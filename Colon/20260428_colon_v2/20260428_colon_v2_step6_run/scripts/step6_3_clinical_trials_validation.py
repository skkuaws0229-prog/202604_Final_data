#!/usr/bin/env python3
"""
Step 6-3: ClinicalTrials 외부 검증

ClinicalTrials.gov 에서 수집한 colorectal cancer 임상시험과
우리 Top 30 약물 매칭.

입력:
  - results/colon_top30_drugs_ensemble.csv
  - curated_data/validation/clinicaltrials/clinicaltrials_colorectal_cancer_all_studies.json

출력:
  - results/colon_clinical_trials_validation_results.json
  - results/colon_clinical_trials_matched_drugs.csv
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


def load_top_drugs(results_dir):
    """Top 30 약물 로드"""
    path = results_dir / "colon_top30_drugs_ensemble.csv"
    df = pd.read_csv(path)
    print(f"  Top drugs: {len(df)}")
    return df


def load_clinical_trials(ct_dir):
    """ClinicalTrials.gov JSON 로드"""
    path = ct_dir / "clinicaltrials_colorectal_cancer_all_studies.json"
    if not path.exists():
        print(f"  ERROR: {path} not found")
        return None

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    studies = data.get("studies", [])
    print(f"  Total studies: {len(studies)}")
    return studies


def extract_drug_interventions(studies):
    """임상시험에서 약물 intervention 추출"""
    drugs = {}  # normalized_name -> {name, phases, nct_ids, count}

    for s in studies:
        ps = s.get("protocolSection", {})
        dm = ps.get("designModule", {})
        im = ps.get("identificationModule", {})
        sm = ps.get("statusModule", {})

        phases = dm.get("phases", ["N/A"])
        study_type = dm.get("studyType", "")
        nct_id = im.get("nctId", "")

        # INTERVENTIONAL 만
        if study_type != "INTERVENTIONAL":
            continue

        _ = sm  # statusModule reserved for future filtering
        aim = ps.get("armsInterventionsModule", {})
        for iv in aim.get("interventions", []):
            if iv.get("type") != "DRUG":
                continue

            name = iv.get("name", "").strip()
            if not name:
                continue

            norm = normalize_drug_name(name)
            if not norm:
                continue
            if norm not in drugs:
                drugs[norm] = {
                    "name": name,
                    "phases": set(),
                    "nct_ids": [],
                    "count": 0,
                }
            entry = drugs[norm]
            for p in phases:
                entry["phases"].add(p)
            entry["nct_ids"].append(nct_id)
            entry["count"] += 1
            for v in strip_salt_variants(norm):
                if v and v != norm:
                    drugs[v] = entry

    # set -> list (JSON 직렬화)
    for d in drugs.values():
        d["phases"] = sorted(list(d["phases"]))

    print(f"  Unique drug interventions: {len(drugs)}")
    return drugs


def match_drugs(top_drugs, ct_drugs, aliases_data: dict):
    """Top drugs 와 ClinicalTrials drugs 매칭 (별칭·염 변형·부분 문자열)."""
    name_col = "DRUG_NAME" if "DRUG_NAME" in top_drugs.columns else "drug_name_norm"

    matched = []
    unmatched = []

    for _, row in top_drugs.iterrows():
        drug_name = row[name_col]
        norm = normalize_drug_name(drug_name)

        def add_match(ct_info, mtype: str):
            matched.append(
                {
                    "rank": int(row["rank"]),
                    "drug_name": drug_name,
                    "ct_name": ct_info["name"],
                    "match_type": mtype,
                    "phases": ct_info["phases"],
                    "max_phase": max(ct_info["phases"]) if ct_info["phases"] else "N/A",
                    "n_trials": ct_info["count"],
                    "sample_nct_ids": ct_info["nct_ids"][:5],
                }
            )

        found = False
        for cand in [norm, *sorted(expanded_norm_set(str(drug_name), aliases_data))]:
            if cand and cand in ct_drugs:
                add_match(ct_drugs[cand], "exact_or_alias")
                found = True
                break
        if found:
            continue

        # synonym 매칭 시도 (부분 매칭)
        candidates = {norm, *expanded_norm_set(str(drug_name), aliases_data)}
        for cn in candidates:
            if not cn:
                continue
            for ct_norm, ct_info in ct_drugs.items():
                if cn in ct_norm or ct_norm in cn:
                    if len(cn) >= 4 and len(ct_norm) >= 4:
                        add_match(ct_info, "partial")
                        found = True
                        break
            if found:
                break

        if not found:
            unmatched.append(
                {
                    "rank": int(row["rank"]),
                    "drug_name": drug_name,
                }
            )

    return matched, unmatched


def main():
    base_dir = Path(__file__).parent.parent
    results_dir = base_dir / "results"
    ct_dir = base_dir / "curated_data" / "validation" / "clinicaltrials"

    print("=" * 80)
    print("Step 6-3: ClinicalTrials External Validation")
    print("=" * 80)

    # 1. Top drugs
    print("\n[1] Top drugs 로드")
    top_drugs = load_top_drugs(results_dir)

    # 2. ClinicalTrials 로드
    print("\n[2] ClinicalTrials 데이터 로드")
    studies = load_clinical_trials(ct_dir)
    if studies is None:
        return

    # 3. Drug interventions 추출
    print("\n[3] Drug interventions 추출 (INTERVENTIONAL only)")
    ct_drugs = extract_drug_interventions(studies)

    # 4. 매칭
    print("\n[4] Drug matching (aliases + salt + partial)")
    aliases_data = load_aliases(ALIASES_PATH)
    matched, unmatched = match_drugs(top_drugs, ct_drugs, aliases_data)
    print(f"  Matched: {len(matched)}/{len(top_drugs)} ({len(matched)/len(top_drugs)*100:.1f}%)")
    print(f"  Unmatched: {len(unmatched)}")

    # 5. Phase 분석
    print("\n[5] Phase 분석")
    phase_counts = {}
    phase2_plus = 0
    for m in matched:
        for p in m["phases"]:
            phase_counts[p] = phase_counts.get(p, 0) + 1
        max_p = m.get("max_phase", "N/A")
        if max_p in ["PHASE2", "PHASE3", "PHASE4"]:
            phase2_plus += 1

    print(f"  Phase 분포: {phase_counts}")
    print(
        f"  Phase II 이상: {phase2_plus}/{len(matched)} ({phase2_plus/len(matched)*100:.1f}%)"
        if matched
        else "  N/A"
    )

    # 6. 결과 저장
    print("\n[6] 저장")

    results = {
        "validation_source": "ClinicalTrials.gov",
        "disease": "colorectal cancer",
        "query": "colorectal cancer OR colon cancer OR rectal cancer",
        "total_studies": len(studies),
        "interventional_drugs": len(ct_drugs),
        "top_n_drugs": len(top_drugs),
        "matched_drugs": len(matched),
        "hit_rate": round(len(matched) / len(top_drugs), 4) if top_drugs is not None else 0,
        "hit_rate_pct": round(len(matched) / len(top_drugs) * 100, 1) if top_drugs is not None else 0,
        "phase2_plus_count": phase2_plus,
        "phase2_plus_pct": round(phase2_plus / len(matched) * 100, 1) if matched else 0,
        "phase_distribution": phase_counts,
        "matched_details": matched,
        "unmatched_drugs": unmatched,
    }

    results_path = results_dir / "colon_clinical_trials_validation_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  ✅ {results_path}")

    if matched:
        matched_df = pd.DataFrame(matched)
        matched_csv = results_dir / "colon_clinical_trials_matched_drugs.csv"
        matched_df.to_csv(matched_csv, index=False)
        print(f"  ✅ {matched_csv}")

    # 7. 요약
    print("\n" + "=" * 80)
    print("ClinicalTrials Validation Summary")
    print("=" * 80)
    print(f"  Total CRC studies: {len(studies)}")
    print(f"  Unique drug interventions: {len(ct_drugs)}")
    print(f"  Top 30 matched: {len(matched)} ({results['hit_rate_pct']}%)")
    print(f"  Phase II+: {phase2_plus}")
    print()
    print("  Matched drugs:")
    for m in matched:
        phase_str = ",".join(m["phases"])
        match_type = m.get("match_type", "exact")
        print(
            f"    #{m['rank']:2d} {m['drug_name']:25s} → "
            f"{phase_str:30s} ({m['n_trials']} trials) [{match_type}]"
        )
    print()
    if unmatched:
        print("  Unmatched drugs:")
        for u in unmatched:
            print(f"    #{u['rank']:2d} {u['drug_name']}")

    print("\n✅ Step 6-3 완료!")


if __name__ == "__main__":
    main()
