#!/usr/bin/env python3
"""
Step 6-6: 종합 스코어링 (5대 검증)

PRISM + ClinicalTrials + COSMIC + CPTAC + GEO 통합.
각 약물별 검증 통과 수 → 신뢰도 등급 부여.

입력:
  - results/colon_top30_drugs_ensemble.csv
  - results/colon_prism_validation_results.json
  - results/colon_clinical_trials_validation_results.json
  - results/colon_cosmic_validation_results.json
  - results/colon_cptac_validation_results.json
  - results/colon_geo_validation_results.json

출력:
  - results/colon_comprehensive_validation_results.json
  - results/colon_comprehensive_drug_scores.csv
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd


def load_json(path):
    if not path.exists():
        print(f"  WARNING: {path} not found")
        return None
    with open(path) as f:
        return json.load(f)


def main():
    base_dir = Path(__file__).parent.parent
    results_dir = base_dir / "results"

    print("=" * 80)
    print("Step 6-6: Comprehensive Validation Scoring (5 Sources)")
    print("=" * 80)

    # 1. Top drugs
    print("\n[1] Top drugs 로드")
    top_drugs = pd.read_csv(results_dir / "colon_top30_drugs_ensemble.csv")
    name_col = "DRUG_NAME" if "DRUG_NAME" in top_drugs.columns else "drug_name_norm"
    print(f"  Top drugs: {len(top_drugs)}")

    # 2. 검증 결과 로드
    print("\n[2] 검증 결과 로드")
    prism = load_json(results_dir / "colon_prism_validation_results.json")
    ct = load_json(results_dir / "colon_clinical_trials_validation_results.json")
    cosmic = load_json(results_dir / "colon_cosmic_validation_results.json")
    cptac = load_json(results_dir / "colon_cptac_validation_results.json")
    geo = load_json(results_dir / "colon_geo_validation_results.json")

    # 3. 각 소스 매칭 약물 set
    print("\n[3] 소스별 매칭 약물")

    prism_matched = set()
    if prism and "matched_drug_names" in prism:
        prism_matched = set(prism["matched_drug_names"])
    print(f"  PRISM: {len(prism_matched)}")

    ct_matched = set()
    if ct and "matched_details" in ct:
        ct_matched = set(m["drug_name"] for m in ct["matched_details"])
    print(f"  ClinicalTrials: {len(ct_matched)}")

    cosmic_matched = set()
    if cosmic and "drugs_matched_all" in cosmic:
        cosmic_matched = set(cosmic["drugs_matched_all"])
    print(f"  COSMIC: {len(cosmic_matched)}")

    cptac_matched = set()
    if cptac and "drugs_matched" in cptac:
        cptac_matched = set(cptac["drugs_matched"])
    print(f"  CPTAC: {len(cptac_matched)}")

    geo_matched = set()
    if geo and "drugs_matched" in geo:
        geo_matched = set(geo["drugs_matched"])
    print(f"  GEO: {len(geo_matched)}")

    # 4. 약물별 스코어
    print("\n[4] 약물별 스코어 계산")

    drug_scores = []
    for _, row in top_drugs.iterrows():
        drug_name = row[name_col]
        rank = int(row["rank"])
        pred = row["pred_ic50_mean"]

        in_prism = 1 if drug_name in prism_matched else 0
        in_ct = 1 if drug_name in ct_matched else 0
        in_cosmic = 1 if drug_name in cosmic_matched else 0
        in_cptac = 1 if drug_name in cptac_matched else 0
        in_geo = 1 if drug_name in geo_matched else 0

        total_pass = in_prism + in_ct + in_cosmic + in_cptac + in_geo

        if total_pass == 5:
            confidence = "Very High"
        elif total_pass == 4:
            confidence = "High"
        elif total_pass == 3:
            confidence = "Medium"
        elif total_pass == 2:
            confidence = "Low"
        elif total_pass == 1:
            confidence = "Very Low"
        else:
            confidence = "Unvalidated"

        ct_phase = ""
        if ct and "matched_details" in ct:
            for m in ct["matched_details"]:
                if m["drug_name"] == drug_name:
                    ct_phase = m.get("max_phase", "")
                    break

        drug_scores.append(
            {
                "rank": rank,
                "drug_name": drug_name,
                "pred_ic50_mean": round(pred, 4),
                "target": row.get("TARGET", ""),
                "target_pathway": row.get("TARGET_PATHWAY", ""),
                "prism": in_prism,
                "clinical_trials": in_ct,
                "ct_max_phase": ct_phase,
                "cosmic": in_cosmic,
                "cptac": in_cptac,
                "geo": in_geo,
                "validation_count": total_pass,
                "confidence": confidence,
            }
        )

    df_scores = pd.DataFrame(drug_scores)

    # 5. 통계
    print("\n[5] 통계")

    confidence_dist = df_scores["confidence"].value_counts().to_dict()
    print(f"  Confidence 분포: {confidence_dist}")

    avg_pass = df_scores["validation_count"].mean()
    print(f"  평균 통과 수: {avg_pass:.2f}/5")

    source_rates = {
        "PRISM": round(df_scores["prism"].mean() * 100, 1),
        "ClinicalTrials": round(df_scores["clinical_trials"].mean() * 100, 1),
        "COSMIC": round(df_scores["cosmic"].mean() * 100, 1),
        "CPTAC": round(df_scores["cptac"].mean() * 100, 1),
        "GEO": round(df_scores["geo"].mean() * 100, 1),
    }
    print(f"  소스별 통과율: {source_rates}")

    full_5 = df_scores[df_scores["validation_count"] == 5]
    full_4 = df_scores[df_scores["validation_count"] >= 4]
    print(f"  5/5 통과 (Very High): {len(full_5)}")
    print(f"  4/5+ 통과 (High+): {len(full_4)}")

    for _, row in full_4.iterrows():
        print(f"    #{row['rank']} {row['drug_name']} ({row['validation_count']}/5)")

    # 6. 저장
    print("\n[6] 저장")

    csv_path = results_dir / "colon_comprehensive_drug_scores.csv"
    df_scores.to_csv(csv_path, index=False)
    print(f"  ✅ {csv_path}")

    comprehensive = {
        "step": "Step 6-6 Comprehensive Scoring",
        "disease": "colorectal cancer (COAD+READ)",
        "top_n_drugs": len(top_drugs),
        "validation_sources": ["PRISM", "ClinicalTrials", "COSMIC", "CPTAC", "GEO"],
        "source_hit_rates": source_rates,
        "confidence_distribution": confidence_dist,
        "avg_validation_count": round(avg_pass, 2),
        "drugs_5_of_5": full_5["drug_name"].tolist(),
        "drugs_4_of_5": df_scores[df_scores["validation_count"] == 4]["drug_name"].tolist(),
        "drugs_3_of_5": df_scores[df_scores["validation_count"] == 3]["drug_name"].tolist(),
        "drugs_0_of_5": df_scores[df_scores["validation_count"] == 0]["drug_name"].tolist(),
        "lung_comparison": {
            "lung_prism": 67.4,
            "lung_ct": 48.8,
            "lung_cosmic": 51.2,
            "lung_cptac": 51.2,
            "colon_prism": source_rates["PRISM"],
            "colon_ct": source_rates["ClinicalTrials"],
            "colon_cosmic": source_rates["COSMIC"],
            "colon_cptac": source_rates["CPTAC"],
            "colon_geo": source_rates["GEO"],
        },
        "drug_scores": drug_scores,
    }

    json_path = results_dir / "colon_comprehensive_validation_results.json"
    with open(json_path, "w") as f:
        json.dump(comprehensive, f, indent=2, default=str)
    print(f"  ✅ {json_path}")

    # 7. 최종 요약
    print("\n" + "=" * 80)
    print("Comprehensive Validation Summary (5 Sources)")
    print("=" * 80)
    print("  Disease: Colorectal Cancer (COAD+READ)")
    print(f"  Top {len(top_drugs)} drugs evaluated")
    print()
    print("  Source Hit Rates:")
    for src, rate in source_rates.items():
        print(f"    {src:20s}: {rate}%")
    print()
    print("  Confidence Distribution:")
    for conf in ["Very High", "High", "Medium", "Low", "Very Low", "Unvalidated"]:
        cnt = confidence_dist.get(conf, 0)
        if cnt > 0:
            print(f"    {conf:15s}: {cnt} drugs")
    print()
    print(f"  Average validation: {avg_pass:.2f}/5")
    print()

    print(
        f"{'Rank':>4} {'Drug':25s} {'PRISM':>5} {'CT':>5} {'COSMIC':>6} "
        f"{'CPTAC':>5} {'GEO':>5} {'Total':>5} {'Confidence':>12}"
    )
    print("-" * 85)
    for _, row in df_scores.iterrows():
        p = "✅" if row["prism"] else "❌"
        c = "✅" if row["clinical_trials"] else "❌"
        co = "✅" if row["cosmic"] else "❌"
        cp = "✅" if row["cptac"] else "❌"
        g = "✅" if row["geo"] else "❌"
        print(
            f"#{row['rank']:3d} {row['drug_name']:25s} {p:>5} {c:>5} {co:>6} "
            f"{cp:>5} {g:>5} {row['validation_count']:>5}/5 {row['confidence']:>12}"
        )

    print("\n✅ Step 6-6 완료!")


if __name__ == "__main__":
    main()
