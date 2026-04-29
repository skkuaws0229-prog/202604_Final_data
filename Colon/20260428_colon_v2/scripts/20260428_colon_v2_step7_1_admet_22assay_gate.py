#!/usr/bin/env python3
"""
20260428_colon_v2 Step7-1: 초이 프로토콜 22 ADMET assay + Morgan/Tanimoto 매칭 + Safety score.

기존 `20260420_new_pre_project_biso_Colon/scripts/step7_1_admet_filtering.py` 로직을 재사용하고,
입력/출력만 colon_v2 규칙 파일명으로 고정한다.

필수 입력:
  - Top30 CSV (canonical_drug_id, DRUG_NAME, …)
  - drug_features.parquet (canonical_drug_id, canonical_smiles)
  - TDC ADMET 디렉터리: .../tdc_admet_group/admet_group/{ames,dili,...}/train_val.csv

출력 (기본, 실험명 포함):
  - admet/20260428_colon_v2_step7/20260428_colon_v2_step7_admet_22assay_choi_protocol_tanimoto_top30_scored.csv
  - admet/20260428_colon_v2_step7/20260428_colon_v2_step7_admet_22assay_choi_protocol_summary.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def _load_legacy_step7_1():
    here = Path(__file__).resolve()
    repo = here.parents[2]
    legacy = (
        repo
        / "20260415_preproject_choi_protocol_v1_bisotest"
        / "20260420_new_pre_project_biso_Colon"
        / "scripts"
        / "step7_1_admet_filtering.py"
    )
    if not legacy.is_file():
        raise FileNotFoundError(
            f"레거시 ADMET 스크립트가 없습니다: {legacy}\n"
            "저장소에 Colon 원 프로젝트 scripts/step7_1_admet_filtering.py 가 있어야 합니다."
        )
    spec = importlib.util.spec_from_file_location("colon_step7_1_admet", legacy)
    if spec is None or spec.loader is None:
        raise ImportError("importlib spec 실패")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_top30_with_smiles(top30_csv: Path, drug_features_parquet: Path):
    import pandas as pd

    df = pd.read_csv(top30_csv)
    if "canonical_drug_id" not in df.columns or "DRUG_NAME" not in df.columns:
        raise ValueError("Top30 CSV에 canonical_drug_id, DRUG_NAME 이 필요합니다.")
    feat = pd.read_parquet(drug_features_parquet, columns=["canonical_drug_id", "canonical_smiles"])
    feat = feat.drop_duplicates("canonical_drug_id")
    df["canonical_drug_id"] = df["canonical_drug_id"].astype(str)
    feat["canonical_drug_id"] = feat["canonical_drug_id"].astype(str)
    out = df.merge(feat, on="canonical_drug_id", how="left")
    n = int(out["canonical_smiles"].notna().sum())
    print(f"  Top drugs: {len(out)}, SMILES 매칭: {n}/{len(out)}")
    return out, "canonical_smiles"


def main() -> int:
    ap = argparse.ArgumentParser(description="Colon v2 — 22 ADMET assay gate")
    pkg = Path(__file__).resolve().parents[1]
    ap.add_argument("--package-root", type=Path, default=pkg)
    ap.add_argument(
        "--top30-csv",
        type=Path,
        default=pkg / "20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv",
    )
    ap.add_argument(
        "--drug-features-parquet",
        type=Path,
        required=True,
        help="GDSC/파이프라인 drug_features.parquet (canonical_drug_id, canonical_smiles)",
    )
    ap.add_argument(
        "--tdc-admet-root",
        type=Path,
        required=True,
        help="curated_data/admet 등 — 내부에 tdc_admet_group/admet_group 가 있어야 함",
    )
    args = ap.parse_args()

    mod = _load_legacy_step7_1()
    if not getattr(mod, "HAS_RDKIT", False):
        print("❌ RDKit 필요: pip install rdkit")
        return 1

    out_dir = args.package_root / "admet" / "20260428_colon_v2_step7"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_out = out_dir / "20260428_colon_v2_step7_admet_22assay_choi_protocol_tanimoto_top30_scored.csv"
    json_out = out_dir / "20260428_colon_v2_step7_admet_22assay_choi_protocol_summary.json"

    print("=" * 80)
    print("20260428_colon_v2 Step7-1: ADMET Gate (Choi — 22 assays + Tanimoto)")
    print("=" * 80)

    print("\n[1] Top30 + SMILES")
    drugs_df, smiles_col = _load_top30_with_smiles(args.top30_csv, args.drug_features_parquet)

    print("\n[2] 22개 assay 라이브러리")
    assay_libraries = mod.load_assay_libraries(args.tdc_admet_root)
    if len(assay_libraries) < 10:
        print(
            f"⚠️ 로드된 assay가 {len(assay_libraries)}개뿐입니다. "
            f"--tdc-admet-root 경로에 tdc_admet_group/admet_group 가 올바른지 확인하세요."
        )

    print("\n[3] Tanimoto 매칭 (시간 소요 가능)")
    match_results = mod.perform_tanimoto_matching(drugs_df, smiles_col, assay_libraries)

    print("\n[4] Safety score")
    df_scored = mod.calculate_safety_scores(match_results, drugs_df, smiles_col)
    df_scored["admet_coverage"] = df_scored["n_total_matches"].astype(float) / 22.0
    df_scored["admet_category"] = df_scored["verdict"].map(
        lambda v: {"PASS": "Candidate", "WARNING": "Caution", "FAIL": "NO_SMILES"}.get(str(v), "Caution")
    )

    verdict_counts = df_scored["verdict"].value_counts().to_dict()
    pains_count = df_scored["pains_alert"].sum() if "pains_alert" in df_scored.columns else 0

    df_scored.to_csv(csv_out, index=False)
    print(f"  ✅ {csv_out}")

    summary = {
        "step": "20260428_colon_v2 Step7-1 ADMET (22 assays)",
        "method": "22 ADMET assays + Tanimoto (Choi protocol, legacy step7_1)",
        "inputs": {
            "top30_csv": str(args.top30_csv),
            "drug_features_parquet": str(args.drug_features_parquet),
            "tdc_admet_root": str(args.tdc_admet_root),
        },
        "outputs": {"csv": str(csv_out), "json": str(json_out)},
        "thresholds": mod.SIMILARITY_THRESHOLDS,
        "total_drugs": int(len(df_scored)),
        "verdict_counts": verdict_counts,
        "avg_safety_score": round(float(df_scored["safety_score"].mean()), 4),
        "avg_matches": round(float(df_scored["n_total_matches"].mean()), 4),
        "assays_loaded": len(assay_libraries),
        "pains_alerts": int(pains_count) if pains_count else 0,
        "rdkit_available": True,
        "status_detail": [],
    }

    for _, row in df_scored.iterrows():
        summary["status_detail"].append(
            {
                "rank": int(row.get("rank", 0) or 0),
                "drug": row["drug_name"],
                "safety_score": float(row["safety_score"]),
                "verdict": row["verdict"],
                "matches": int(row["n_total_matches"]),
                "admet_coverage": float(row.get("admet_coverage", 0)),
                "mw": row.get("mw"),
                "logp": row.get("logp"),
                "tpsa": row.get("tpsa"),
            }
        )

    results_detail = {}
    for drug_name, result in match_results.items():
        results_detail[drug_name] = {
            "n_total_matches": result["n_total_matches"],
            "n_exact": result["n_exact"],
            "n_close_analog": result["n_close_analog"],
            "n_analog": result["n_analog"],
            "assays": result["assays"],
        }
    summary["match_details"] = results_detail

    with json_out.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  ✅ {json_out}")

    print("\n✅ Step7-1 완료 (22 assay). 다음: step7_select_top15 에 --admet-csv 위 CSV 경로 전달")
    return 0


if __name__ == "__main__":
    sys.exit(main())
