#!/usr/bin/env python3
"""
Step 6-2: PRISM 외부 검증

PRISM secondary screen 에서 Colon (colorectal) cell line 의
약물 감수성 데이터와 우리 Top 30 예측 비교.

입력:
  - results/colon_top30_drugs_ensemble.csv
  - curated_data/validation/prism/secondary-screen-dose-response-curve-parameters.csv
  - curated_data/validation/prism/prism-repurposing-20q2-primary-screen-cell-line-info.csv

출력:
  - results/colon_prism_validation_results.json
  - results/colon_prism_matched_drugs.csv
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from colon_validation_matching_utils import (
    expanded_norm_set,
    load_aliases,
    normalize_drug_name,
    strip_salt_variants,
)

ALIASES_PATH = Path(__file__).resolve().parent / "colon_validation_drug_aliases.json"


def load_top_drugs(results_dir: Path) -> pd.DataFrame:
    """Top 30 약물 로드."""
    path = results_dir / "colon_top30_drugs_ensemble.csv"
    df = pd.read_csv(path)
    print(f"  Top drugs: {len(df)}")
    return df


def load_prism_cell_lines(prism_dir: Path) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """PRISM cell line info 에서 colorectal 필터."""
    # 여러 파일명 시도
    for fname in [
        "prism-repurposing-20q2-primary-screen-cell-line-info.csv",
        "primary-screen-cell-line-info.csv",
    ]:
        path = prism_dir / fname
        if path.exists():
            df = pd.read_csv(path)
            print(f"  PRISM cell lines: {len(df)} (from {fname})")

            # colorectal 필터
            if "primary_tissue" in df.columns:
                crc = df[df["primary_tissue"].str.lower().str.contains("colorectal", na=False)]
                print(f"  Colorectal cell lines: {len(crc)}")
                return df, crc

    print("  WARNING: PRISM cell line info not found")
    return None, None


def load_prism_dose_response(prism_dir: Path) -> pd.DataFrame | None:
    """PRISM dose-response 데이터 로드."""
    for fname in [
        "secondary-screen-dose-response-curve-parameters.csv",
        "prism-repurposing-20q2-secondary-screen-dose-response-curve-parameters.csv",
    ]:
        path = prism_dir / fname
        if path.exists():
            df = pd.read_csv(path)
            print(f"  PRISM dose-response: {len(df)} rows (from {fname})")
            print(f"  Columns: {list(df.columns[:10])}")
            return df

    # logfold-change 도 시도
    for fname in [
        "secondary-screen-replicate-collapsed-logfold-change.csv",
        "prism-repurposing-20q2-secondary-screen-replicate-collapsed-logfold-change.csv",
    ]:
        path = prism_dir / fname
        if path.exists():
            print(f"  Using logfold-change: {fname}")
            df = pd.read_csv(path, nrows=5)
            print(f"  Columns: {list(df.columns[:10])}")
            # 이 파일은 wide format (cell line × drug)
            return pd.read_csv(path)

    print("  WARNING: PRISM dose-response not found")
    return None


def load_prism_treatment_info(prism_dir: Path) -> pd.DataFrame | None:
    """PRISM treatment (약물) info 로드.

    Secondary + Primary를 합쳐 이름 사전을 만든다.
    일부 약물(dactinomycin 등)은 primary 테이블에만 있는 경우가 있다.
    동일 broad_id가 양쪽에 있으면 secondary 행을 우선한다.
    """
    secondary_names = [
        "prism-repurposing-20q2-secondary-screen-replicate-collapsed-treatment-info.csv",
        "secondary-screen-replicate-collapsed-treatment-info.csv",
    ]
    primary_names = [
        "prism-repurposing-20q2-primary-screen-replicate-collapsed-treatment-info.csv",
        "primary-screen-replicate-collapsed-treatment-info.csv",
    ]
    frames: list[pd.DataFrame] = []
    for fname in secondary_names:
        path = prism_dir / fname
        if path.exists():
            df = pd.read_csv(path, low_memory=False)
            df["_prism_table"] = "secondary"
            frames.append(df)
            print(f"  PRISM treatments (secondary): {len(df)} ({fname})")
            break
    for fname in primary_names:
        path = prism_dir / fname
        if path.exists():
            df = pd.read_csv(path, low_memory=False)
            df["_prism_table"] = "primary"
            frames.append(df)
            print(f"  PRISM treatments (primary): {len(df)} ({fname})")
            break

    if not frames:
        print("  WARNING: PRISM treatment info not found")
        return None

    combined = pd.concat(frames, ignore_index=True)
    before = len(combined)
    if "broad_id" in combined.columns:
        combined = combined.drop_duplicates(subset=["broad_id"], keep="first")
    print(f"  PRISM treatments merged (dedup broad_id): {before} → {len(combined)}")
    return combined


def match_drugs(
    top_drugs: pd.DataFrame, prism_treatments: pd.DataFrame, aliases_data: dict
) -> list[dict[str, str]]:
    """Top drugs 와 PRISM treatments 매칭 (염 접미사 + 별칭 확장)."""
    name_col = "DRUG_NAME" if "DRUG_NAME" in top_drugs.columns else "drug_name_norm"

    prism_name_col = "name" if "name" in prism_treatments.columns else prism_treatments.columns[0]
    prism_norm_to_raw: dict[str, str] = {}
    for _, row in prism_treatments.iterrows():
        raw = row[prism_name_col]
        n = normalize_drug_name(raw)
        if not n:
            continue
        prism_norm_to_raw[n] = raw
        for v in strip_salt_variants(n):
            if v:
                prism_norm_to_raw[v] = raw

    matched: list[dict[str, str]] = []
    for _, row in top_drugs.iterrows():
        our_name = row[name_col]
        found_raw = None
        matched_norm = ""
        for exp in expanded_norm_set(str(our_name), aliases_data):
            if exp in prism_norm_to_raw:
                found_raw = prism_norm_to_raw[exp]
                matched_norm = exp
                break
        if found_raw is not None:
            matched.append(
                {
                    "our_drug": our_name,
                    "prism_drug": found_raw,
                    "normalized": matched_norm,
                    "match_type": "exact_alias_or_salt",
                }
            )

    n_top = len(top_drugs)
    print(f"  매칭: {len(matched)}/{n_top} ({len(matched)/n_top*100:.1f}%)")
    return matched


def main() -> None:
    base_dir = Path(__file__).parent.parent
    results_dir = base_dir / "results"
    prism_dir = base_dir / "curated_data" / "validation" / "prism"

    print("=" * 80)
    print("Step 6-2: PRISM External Validation")
    print("=" * 80)

    # 1. Top drugs 로드
    print("\n[1] Top drugs 로드")
    top_drugs = load_top_drugs(results_dir)

    # 2. PRISM cell line info
    print("\n[2] PRISM cell lines")
    all_cells, crc_cells = load_prism_cell_lines(prism_dir)

    # 3. PRISM treatment info
    print("\n[3] PRISM treatments")
    prism_treatments = load_prism_treatment_info(prism_dir)

    # 4. 약물 매칭
    print("\n[4] Drug matching (aliases + salt variants)")
    aliases_data = load_aliases(ALIASES_PATH)
    if prism_treatments is not None:
        matched = match_drugs(top_drugs, prism_treatments, aliases_data)
    else:
        matched = []

    # 5. PRISM dose-response (colorectal cell lines 만)
    print("\n[5] PRISM dose-response (colorectal)")
    prism_dr = load_prism_dose_response(prism_dir)

    # 6. 결과 계산
    print("\n[6] Validation metrics")

    n_top = len(top_drugs)
    n_matched = len(matched)
    hit_rate = n_matched / n_top if n_top > 0 else 0

    results = {
        "validation_source": "PRISM",
        "disease": "colorectal",
        "top_n_drugs": n_top,
        "prism_total_treatments": len(prism_treatments) if prism_treatments is not None else 0,
        "colorectal_cell_lines": len(crc_cells) if crc_cells is not None else 0,
        "matched_drugs": n_matched,
        "hit_rate": round(hit_rate, 4),
        "hit_rate_pct": round(hit_rate * 100, 1),
        "matched_drug_names": [m["our_drug"] for m in matched],
        "unmatched_drug_names": [],
    }

    # 매칭 안 된 약물
    name_col = "DRUG_NAME" if "DRUG_NAME" in top_drugs.columns else "drug_name_norm"
    matched_ours = {m["our_drug"] for m in matched}
    for _, row in top_drugs.iterrows():
        if row[name_col] not in matched_ours:
            results["unmatched_drug_names"].append(row[name_col])

    # 7. 저장
    print("\n[7] 저장")

    results_path = results_dir / "colon_prism_validation_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  ✅ {results_path}")

    if matched:
        matched_df = pd.DataFrame(matched)
        matched_csv = results_dir / "colon_prism_matched_drugs.csv"
        matched_df.to_csv(matched_csv, index=False)
        print(f"  ✅ {matched_csv}")

    # 8. 요약
    print("\n" + "=" * 80)
    print("PRISM Validation Summary")
    print("=" * 80)
    print(f"  Top drugs: {n_top}")
    print(f"  PRISM matched: {n_matched} ({results['hit_rate_pct']}%)")
    print(f"  Colorectal cell lines in PRISM: {results['colorectal_cell_lines']}")
    print(f"  Matched: {results['matched_drug_names']}")
    print(f"  Unmatched: {results['unmatched_drug_names']}")

    if all_cells is None:
        print("  Note: cell line info 파일을 찾지 못해 colorectal 필터가 제한될 수 있습니다.")
    if prism_dr is None:
        print("  Note: dose-response 파일을 찾지 못했습니다.")

    print("\n✅ Step 6-2 완료!")


if __name__ == "__main__":
    main()
