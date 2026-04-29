#!/usr/bin/env python3
"""
Step 6-0: Drug-level Ranking 생성

앙상블 OOF (GraphSAGE FSimp 2B × 0.8 + CatBoost FSimp 2B × 0.2) 에서
drug 별 평균 predicted IC50 계산 → Top N 약물 추출.

입력:
  - results/graph_fsimp_top1000_20260422/colon_numeric_smiles_graph_v1_fsimp_top1000_oof/GraphSAGE.npy
  - results/fsimp_top1000_20260422/colon_numeric_smiles_ml_v1_fsimp_top1000_oof/CatBoost.npy
  - fe_qc/20260420_colon_fe_v2/features_slim.parquet (canonical_drug_id)
  - data/y_train.npy

출력:
  - results/colon_top30_drugs_ensemble.csv
  - results/colon_top50_drugs_ensemble.csv
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd


def load_oof(path: Path) -> np.ndarray:
    """OOF predictions 로드."""
    oof = np.load(path, allow_pickle=True)
    print(f"  Loaded: {path} shape={oof.shape}")
    return oof


def main() -> None:
    base_dir = Path(__file__).parent.parent
    results_dir = base_dir / "results"

    # ─── 1. OOF 로드 ───
    print("=" * 80)
    print("Step 6-0: Drug-level Ranking (Ensemble OOF)")
    print("=" * 80)

    graph_oof_path = (
        results_dir
        / "graph_fsimp_top1000_20260422"
        / "colon_numeric_smiles_graph_v1_fsimp_top1000_oof"
        / "GraphSAGE.npy"
    )
    ml_oof_path = (
        results_dir
        / "fsimp_top1000_20260422"
        / "colon_numeric_smiles_ml_v1_fsimp_top1000_oof"
        / "CatBoost.npy"
    )

    if not graph_oof_path.exists():
        print(f"ERROR: {graph_oof_path} not found!")
        return
    if not ml_oof_path.exists():
        print(f"ERROR: {ml_oof_path} not found!")
        return

    print("\n[1] OOF 로드")
    graph_oof = load_oof(graph_oof_path)
    ml_oof = load_oof(ml_oof_path)

    # ─── 2. 앙상블 OOF ───
    print("\n[2] 앙상블 OOF 계산 (GraphSAGE × 0.8 + CatBoost × 0.2)")
    ensemble_oof = 0.8 * graph_oof + 0.2 * ml_oof
    print(f"  Ensemble OOF shape: {ensemble_oof.shape}")

    # ─── 3. Drug ID 매핑 ───
    print("\n[3] Drug ID 로드")
    features_path = base_dir / "fe_qc" / "20260420_colon_fe_v2" / "features_slim.parquet"
    if not features_path.exists():
        print(f"ERROR: {features_path} not found!")
        return

    df_feat = pd.read_parquet(features_path, columns=["canonical_drug_id"])
    print(f"  Features: {len(df_feat)} rows")

    if len(df_feat) != len(ensemble_oof):
        print(f"  WARNING: Feature rows ({len(df_feat)}) != OOF length ({len(ensemble_oof)})")
        print("  Trying labels.parquet...")
        labels_path = base_dir / "data" / "labels.parquet"
        if labels_path.exists():
            df_feat = pd.read_parquet(labels_path)
            print(f"  Labels: {len(df_feat)} rows, columns: {list(df_feat.columns[:5])}")

    # y_train 로드
    y = np.load(base_dir / "data" / "y_train.npy")
    print(f"  y_train: {y.shape}")

    # ─── 4. Drug-level 통계 ───
    print("\n[4] Drug-level 통계 계산")

    df = pd.DataFrame(
        {
            "canonical_drug_id": df_feat["canonical_drug_id"].values,
            "y_true": y,
            "pred_ic50": ensemble_oof,
        }
    )

    drug_stats = (
        df.groupby("canonical_drug_id")
        .agg(
            pred_ic50_mean=("pred_ic50", "mean"),
            pred_ic50_std=("pred_ic50", "std"),
            pred_ic50_min=("pred_ic50", "min"),
            pred_ic50_max=("pred_ic50", "max"),
            y_true_mean=("y_true", "mean"),
            n_cell_lines=("pred_ic50", "count"),
        )
        .reset_index()
    )

    # IC50 낮을수록 감수성 높음 → 오름차순 정렬
    drug_stats = drug_stats.sort_values("pred_ic50_mean").reset_index(drop=True)

    # ─── 4b. Drug name 매핑 (중복 제거 위해 먼저 수행) ───
    print("\n[4b] Drug name 매핑 + 중복 제거")

    drug_meta_path = base_dir / "data" / "drug_features.parquet"
    if drug_meta_path.exists():
        drug_meta = pd.read_parquet(drug_meta_path, columns=["canonical_drug_id", "drug_name_norm"])
        drug_meta = drug_meta.drop_duplicates("canonical_drug_id")
        drug_stats = drug_stats.merge(drug_meta, on="canonical_drug_id", how="left")

    gdsc_meta_path = base_dir / "curated_data" / "gdsc" / "Compounds-annotation.csv"
    if gdsc_meta_path.exists():
        gdsc = pd.read_csv(gdsc_meta_path)
        if "DRUG_ID" in gdsc.columns:
            gdsc_map = gdsc[["DRUG_ID", "DRUG_NAME", "TARGET", "TARGET_PATHWAY"]].copy()
            gdsc_map = gdsc_map.rename(columns={"DRUG_ID": "canonical_drug_id"})
            gdsc_map["canonical_drug_id"] = gdsc_map["canonical_drug_id"].astype(str)
            drug_stats["canonical_drug_id"] = drug_stats["canonical_drug_id"].astype(str)
            drug_stats = drug_stats.merge(
                gdsc_map, on="canonical_drug_id", how="left", suffixes=("", "_gdsc")
            )

    # 중복 제거: 같은 DRUG_NAME 이 여러 ID 로 존재 → 가장 낮은 pred_ic50_mean 만 유지
    name_col = "DRUG_NAME" if "DRUG_NAME" in drug_stats.columns else "drug_name_norm"
    before_dedup = len(drug_stats)

    # NaN 이름은 유지 (제거 대상 아님)
    has_name = drug_stats[drug_stats[name_col].notna()]
    no_name = drug_stats[drug_stats[name_col].isna()]

    # 이미 pred_ic50_mean 오름차순 정렬이므로 first = 최저값
    has_name_dedup = has_name.drop_duplicates(subset=name_col, keep="first")

    drug_stats = pd.concat([has_name_dedup, no_name], ignore_index=True)
    drug_stats = drug_stats.sort_values("pred_ic50_mean").reset_index(drop=True)

    after_dedup = len(drug_stats)
    print(f"  중복 제거: {before_dedup} → {after_dedup} ({before_dedup - after_dedup} 제거)")

    # Rank 재할당
    drug_stats["rank"] = np.arange(1, len(drug_stats) + 1)

    print(f"  최종 약물 수: {len(drug_stats)}")
    print("  Top 5:")
    for _, row in drug_stats.head(5).iterrows():
        print(
            f"    #{int(row['rank'])} drug_id={row['canonical_drug_id']}"
            f" {row.get(name_col, '?')}"
            f" pred_mean={row['pred_ic50_mean']:.4f}"
            f" n_cells={int(row['n_cell_lines'])}"
        )

    # ─── 6. 저장 ───
    print("\n[6] 저장")

    # Top 30
    top30 = drug_stats.head(30)
    top30_path = results_dir / "colon_top30_drugs_ensemble.csv"
    top30.to_csv(top30_path, index=False)
    print(f"  ✅ Top 30: {top30_path}")

    # Top 50
    top50 = drug_stats.head(50)
    top50_path = results_dir / "colon_top50_drugs_ensemble.csv"
    top50.to_csv(top50_path, index=False)
    print(f"  ✅ Top 50: {top50_path}")

    # 전체 ranking
    all_path = results_dir / "colon_all_drugs_ranking_ensemble.csv"
    drug_stats.to_csv(all_path, index=False)
    print(f"  ✅ 전체: {all_path}")

    # ─── 7. 요약 출력 ───
    print("\n" + "=" * 80)
    print("Top 10 약물")
    print("=" * 80)

    name_col = "DRUG_NAME" if "DRUG_NAME" in drug_stats.columns else "drug_name_norm"
    target_col = "TARGET" if "TARGET" in drug_stats.columns else None

    for _, row in drug_stats.head(10).iterrows():
        name = row.get(name_col, "?")
        target = row.get(target_col, "") if target_col else ""
        print(
            f"  #{int(row['rank']):2d} {str(name):25s} "
            f"pred_IC50={row['pred_ic50_mean']:.4f} ± {row['pred_ic50_std']:.4f} "
            f"(n={int(row['n_cell_lines'])}) "
            f"target={target}"
        )

    print("\n✅ Step 6-0 완료!")


if __name__ == "__main__":
    main()
