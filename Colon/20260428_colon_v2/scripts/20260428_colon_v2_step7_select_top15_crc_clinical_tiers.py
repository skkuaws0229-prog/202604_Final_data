#!/usr/bin/env python3
"""
20260428_colon_v2 Step7: Top30 → Top15 + CRC 임상 티어(1–4).

- ADMET CSV가 있으면 초이 프로토콜식 정렬(verdict, safety_score, pred_ic50)을 우선.
- 없으면 CRC 임상 티어(낮은 숫자 우선) + ensemble rank로 Top15.

입력 기본값: 20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv

출력 파일명 (실험 구분):
  - ADMET 22assay 병합 성공 시:
      20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv
      20260428_colon_v2_step7_summary_admet22assay_choi_protocol.json
  - ADMET 없이 CRC 티어·랭크만:
      20260428_colon_v2_step7_top15_crc_tier1234_no_admet_tier_sort_only.csv
      20260428_colon_v2_step7_summary_no_admet_tier_sort_only.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


def _norm_inn_key(name: object) -> str:
    t = str(name or "").strip().lower()
    t = re.sub(r"\([^)]*\)", "", t)
    return re.sub(r"[^a-z0-9]+", "", t)


def _parse_ensemble_tier(cell: object) -> int | None:
    s = str(cell or "").strip()
    m = re.match(r"Tier\s*(\d+)", s, re.I)
    if m:
        return int(m.group(1))
    return None


def _load_seed(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _assign_crc_tier(
    drug_name: object,
    seed: dict,
    t1: set[str],
    t2: set[str],
    t4: set[str],
    ensemble_tier: int | None,
) -> tuple[int, str, str]:
    """Returns tier int, label, evidence source. Step6 ensemble tier가 있으면 최우선."""
    sem = seed.get("tier_semantics_ko", {})
    key = _norm_inn_key(drug_name)

    def label(n: int) -> str:
        return sem.get(str(n), f"Tier {n}")

    if ensemble_tier is not None:
        return ensemble_tier, label(ensemble_tier), "ensemble:step6_tier_20260428_colon_v2"
    if key in t1:
        return 1, label(1), "seed:tier1_crc_approved_inn"
    if key in t2:
        return 2, label(2), "seed:tier2_other_cancer_crc_expansion_inn"
    if key in t4:
        return 4, label(4), "seed:tier4_research_tool_or_uncertain_inn"
    return 3, label(3), "default:tier3"


def _verdict_rank(v: object) -> int:
    s = str(v or "").upper()
    if s == "PASS":
        return 0
    if s == "WARNING":
        return 1
    if s == "FAIL":
        return 2
    return 3


def _sort_key_admet(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work = work[work["verdict"].isin(["PASS", "WARNING"])].copy()
    work["_vr"] = work["verdict"].map(_verdict_rank)
    sort_cols = ["_vr"]
    asc = [True]
    if "safety_score" in work.columns:
        sort_cols.append("safety_score")
        asc.append(False)
    if "toxicity_flags" in work.columns:
        sort_cols.append("toxicity_flags")
        asc.append(True)
    if "low_confidence_toxic_signals" in work.columns:
        sort_cols.append("low_confidence_toxic_signals")
        asc.append(True)
    if "admet_coverage" in work.columns:
        sort_cols.append("admet_coverage")
        asc.append(False)
    rk = "rank_20260428_colon_v2" if "rank_20260428_colon_v2" in work.columns else "rank"
    if rk in work.columns:
        sort_cols.append(rk)
        asc.append(True)
    elif "pred_ic50_mean" in work.columns:
        sort_cols.append("pred_ic50_mean")
        asc.append(True)
    work = work.sort_values(sort_cols, ascending=asc).drop(columns=["_vr"], errors="ignore")
    return work.head(15).reset_index(drop=True)


def _sort_key_no_admet(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work = work.sort_values(
        ["crc_clinical_tier", "rank_20260428_colon_v2" if "rank_20260428_colon_v2" in work.columns else "rank"],
        ascending=[True, True],
    )
    return work.head(15).reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[1]
    ap.add_argument(
        "--package-root",
        type=Path,
        default=root,
        help="20260428_colon_v2 폴더",
    )
    ap.add_argument(
        "--top30-csv",
        type=Path,
        default=None,
        help="Step6 Top30 CSV (기본: 패키지 루트의 표준 파일명)",
    )
    ap.add_argument(
        "--seed-json",
        type=Path,
        default=None,
        help="CRC 티어 시드 JSON",
    )
    ap.add_argument(
        "--admet-csv",
        type=Path,
        default=None,
        help="Step7-1 산출 CSV (verdict, safety_score, admet_coverage). 미지정 시 표준 경로에 파일 있으면 자동 사용",
    )
    args = ap.parse_args()
    pkg: Path = args.package_root

    top30_path = args.top30_csv or (
        pkg / "20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv"
    )
    seed_path = args.seed_json or (pkg / "config" / "20260428_colon_v2_step7_crc_clinical_tier_seed.json")

    admet_dir = pkg / "admet" / "20260428_colon_v2_step7"
    default_admet_new = admet_dir / "20260428_colon_v2_step7_admet_22assay_choi_protocol_tanimoto_top30_scored.csv"
    default_admet_legacy = admet_dir / "20260428_colon_v2_step7_drugs_with_admet_22assay.csv"
    admet_arg = args.admet_csv
    if admet_arg is None:
        if default_admet_new.is_file():
            admet_arg = default_admet_new
        elif default_admet_legacy.is_file():
            admet_arg = default_admet_legacy

    if not top30_path.is_file():
        raise FileNotFoundError(f"Top30 CSV 없음: {top30_path}")
    if not seed_path.is_file():
        raise FileNotFoundError(f"Seed JSON 없음: {seed_path}")

    seed = _load_seed(seed_path)
    t1 = {_norm_inn_key(x) for x in seed.get("tier1_crc_approved_inn", [])}
    t2 = {_norm_inn_key(x) for x in seed.get("tier2_other_cancer_crc_expansion_inn", [])}
    t4 = {_norm_inn_key(x) for x in seed.get("tier4_research_tool_or_uncertain_inn", [])}

    df = pd.read_csv(top30_path)
    if "DRUG_NAME" not in df.columns:
        raise ValueError("DRUG_NAME 열이 필요합니다.")

    tiers = []
    for _, row in df.iterrows():
        ens = _parse_ensemble_tier(row.get("tier_20260428_colon_v2"))
        t_int, t_label, t_src = _assign_crc_tier(row["DRUG_NAME"], seed, t1, t2, t4, ens)
        tiers.append((t_int, t_label, t_src))

    df["crc_clinical_tier"] = [x[0] for x in tiers]
    df["crc_clinical_tier_label_ko"] = [x[1] for x in tiers]
    df["crc_tier_evidence_source"] = [x[2] for x in tiers]

    admet_path = admet_arg
    merged_note = "no_admet_file"
    if admet_path and Path(admet_path).is_file():
        admet = pd.read_csv(admet_path)
        merge_on = None
        for c in ("canonical_drug_id", "DRUG_NAME", "drug_name"):
            if c in admet.columns and c in df.columns:
                merge_on = c
                break
        if merge_on:
            df = df.merge(admet, on=merge_on, how="left", suffixes=("", "_admet"))
            merged_note = f"merged_on_{merge_on}"
        else:
            merged_note = "admet_csv_present_but_no_merge_key"

    if "verdict" in df.columns and df["verdict"].notna().any():
        top15 = _sort_key_admet(df)
        selection_mode = "admet_protocol_pass_warning"
        experiment_id = "colon_v2_step7_admet22assay_choi_protocol"
        experiment_label_ko = "초이 프로토콜 22 assay ADMET(Tanimoto) 병합 후 PASS/WARNING 기준 Top15"
    else:
        top15 = _sort_key_no_admet(df)
        selection_mode = "crc_tier_then_ensemble_rank"
        experiment_id = "colon_v2_step7_no_admet_crc_tier_sort_only"
        experiment_label_ko = "ADMET 미적용: CRC 임상 Tier1–4 + ensemble rank만으로 Top15"

    top15 = top15.copy()
    top15.insert(0, "step7_final_rank", range(1, len(top15) + 1))
    top15.insert(1, "step7_experiment_id", experiment_id)
    top15.insert(2, "step7_experiment_label_ko", experiment_label_ko)

    if selection_mode == "admet_protocol_pass_warning":
        out_csv = pkg / "20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv"
        out_json = pkg / "20260428_colon_v2_step7_summary_admet22assay_choi_protocol.json"
    else:
        out_csv = pkg / "20260428_colon_v2_step7_top15_crc_tier1234_no_admet_tier_sort_only.csv"
        out_json = pkg / "20260428_colon_v2_step7_summary_no_admet_tier_sort_only.json"

    top15.to_csv(out_csv, index=False)

    summary = {
        "step": "20260428_colon_v2 Step7",
        "experiment_id": experiment_id,
        "experiment_label_ko": experiment_label_ko,
        "inputs": {
            "top30_csv": str(top30_path),
            "seed_json": str(seed_path),
            "admet_csv": str(admet_path) if admet_path and Path(admet_path).is_file() else None,
        },
        "outputs": {"top15_csv": str(out_csv), "summary_json": str(out_json)},
        "selection_mode": selection_mode,
        "admet_merge": merged_note,
        "top15_row_count": int(len(top15)),
        "crc_tier_counts_top15": top15["crc_clinical_tier"].value_counts().sort_index().to_dict(),
        "tier_semantics_ko": seed.get("tier_semantics_ko", {}),
        "tier_policy": "ensemble_tier_20260428_colon_v2 우선, 없을 때만 seed INN 목록",
    }
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
