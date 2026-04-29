#!/usr/bin/env python3
"""
Step 6-5: CPTAC-CRC 외부 검증

CPTAC coad_cptac_2019 환자 mRNA 발현 데이터에서
우리 Top 30 약물의 타겟 유전자 발현 수준 확인.

검증 논리:
  - Top 30 약물의 타겟 유전자 추출
  - CPTAC CRC 환자 mRNA 에서 해당 유전자 발현 확인
  - 발현 있음 = 약물 타겟이 환자에서 활성 → 약물 효과 기대

입력:
  - results/colon_top30_drugs_ensemble.csv
  - curated_data/cbioportal/coad_cptac_2019/data_mrna_seq_v2_rsem.txt

출력:
  - results/colon_cptac_validation_results.json
  - results/colon_cptac_matched_drugs.csv
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd


def normalize_name(name):
    """이름 정규화"""
    if pd.isna(name) or not isinstance(name, str):
        return ""
    return name.strip().lower().replace("-", "").replace(" ", "").replace("_", "")


def load_top_drugs(results_dir):
    """Top 30 약물 로드"""
    path = results_dir / "colon_top30_drugs_ensemble.csv"
    df = pd.read_csv(path)
    print(f"  Top drugs: {len(df)}")
    return df


def extract_target_genes(top_drugs):
    """Top drugs 에서 타겟 유전자 추출"""
    targets = {}  # gene -> [drug_names]

    target_col = "TARGET" if "TARGET" in top_drugs.columns else None
    if target_col is None:
        print("  WARNING: TARGET column not found")
        return targets

    for _, row in top_drugs.iterrows():
        drug_name = row.get("DRUG_NAME", row.get("drug_name_norm", ""))
        target_str = row.get(target_col, "")

        if pd.isna(target_str) or not isinstance(target_str, str):
            continue

        for gene in target_str.replace(";", ",").split(","):
            gene = gene.strip().upper()
            if gene and len(gene) >= 2:
                if gene not in targets:
                    targets[gene] = []
                targets[gene].append(drug_name)

    print(f"  Extracted {len(targets)} unique target genes from {len(top_drugs)} drugs")
    return targets


def load_cptac_mrna(cptac_dir):
    """CPTAC mRNA 발현 데이터 로드"""
    # 파일 찾기
    mrna_files = list(cptac_dir.glob("data_mrna*.txt"))
    if not mrna_files:
        print("  ERROR: No mRNA file found")
        return None

    # rsem 우선
    for f in mrna_files:
        if "rsem" in f.name and "zscores" not in f.name:
            path = f
            break
    else:
        path = mrna_files[0]

    print(f"  Loading: {path.name}")
    df = pd.read_csv(path, sep="\t")
    print(f"  mRNA matrix: {df.shape[0]} genes × {df.shape[1] - 2} patients")
    print(f"  Columns (first 5): {list(df.columns[:5])}")

    return df


def load_cptac_clinical(cptac_dir):
    """CPTAC clinical 데이터 로드 (COAD/READ 구분용)"""
    clinical_files = list(cptac_dir.glob("data_clinical_patient*"))
    if not clinical_files:
        # sample 파일 시도
        clinical_files = list(cptac_dir.glob("data_clinical_sample*"))
    if not clinical_files:
        print("  No clinical file found")
        return None

    path = clinical_files[0]
    print(f"  Loading clinical: {path.name}")

    # cBioPortal clinical 파일은 상단에 # 주석이 있음
    df = pd.read_csv(path, sep="\t", comment="#")
    print(f"  Clinical: {len(df)} patients, columns: {list(df.columns[:10])}")
    return df


def analyze_target_expression(mrna_df, target_genes):
    """타겟 유전자의 발현 수준 분석"""
    results = []

    gene_col = "Hugo_Symbol" if "Hugo_Symbol" in mrna_df.columns else mrna_df.columns[0]
    patient_cols = [c for c in mrna_df.columns if c not in [gene_col, "Entrez_Gene_Id"]]

    available_genes = set(mrna_df[gene_col].dropna().str.upper())
    print(f"  Available genes in CPTAC: {len(available_genes)}")

    matched_count = 0
    expressed_count = 0

    for gene, drugs in target_genes.items():
        if gene in available_genes:
            matched_count += 1

            # 해당 유전자의 발현값 추출
            gene_row = mrna_df[mrna_df[gene_col].str.upper() == gene]
            if len(gene_row) == 0:
                continue

            values = gene_row[patient_cols].values.flatten()
            values = values[~np.isnan(values)]

            if len(values) == 0:
                continue

            mean_expr = float(np.mean(values))
            median_expr = float(np.median(values))
            std_expr = float(np.std(values))
            pct_expressed = float(np.sum(values > 0) / len(values) * 100)

            # 발현 여부 판단 (median > 0 이면 발현)
            is_expressed = median_expr > 0

            if is_expressed:
                expressed_count += 1

            results.append(
                {
                    "gene": gene,
                    "drugs": drugs,
                    "mean_expression": round(mean_expr, 4),
                    "median_expression": round(median_expr, 4),
                    "std_expression": round(std_expr, 4),
                    "pct_patients_expressed": round(pct_expressed, 1),
                    "n_patients": len(values),
                    "is_expressed": is_expressed,
                }
            )

    print(f"  Target genes in CPTAC: {matched_count}/{len(target_genes)}")
    print(f"  Expressed (median > 0): {expressed_count}/{matched_count}")

    return results


def main():
    base_dir = Path(__file__).parent.parent
    results_dir = base_dir / "results"
    cptac_dir = base_dir / "curated_data" / "cbioportal" / "coad_cptac_2019"

    print("=" * 80)
    print("Step 6-5: CPTAC-CRC External Validation")
    print("=" * 80)

    # 1. Top drugs
    print("\n[1] Top drugs 로드")
    top_drugs = load_top_drugs(results_dir)

    # 2. 타겟 유전자 추출
    print("\n[2] 타겟 유전자 추출")
    target_genes = extract_target_genes(top_drugs)

    if not target_genes:
        print("  ERROR: No target genes extracted. TARGET column missing?")
        # TARGET 없이도 진행 — drug name 으로 검증
        print("  Falling back to drug name only mode")

    # 3. CPTAC mRNA 로드
    print("\n[3] CPTAC mRNA 발현 데이터 로드")
    mrna_df = load_cptac_mrna(cptac_dir)
    if mrna_df is None:
        print("  FATAL: Cannot proceed without mRNA data")
        return

    # 4. CPTAC clinical 로드
    print("\n[4] CPTAC clinical 데이터 로드")
    clinical_df = load_cptac_clinical(cptac_dir)

    # COAD/READ 분포 확인
    coad_read_dist = {}
    if clinical_df is not None:
        for col in ["CANCER_TYPE_ACRONYM", "SUBTYPE", "CANCER_TYPE", "ONCOTREE_CODE"]:
            if col in clinical_df.columns:
                dist = clinical_df[col].value_counts().to_dict()
                coad_read_dist = dist
                print(f"  {col} 분포: {dist}")
                break

    # 5. 타겟 유전자 발현 분석
    print("\n[5] 타겟 유전자 발현 분석")
    if target_genes:
        expression_results = analyze_target_expression(mrna_df, target_genes)
    else:
        expression_results = []

    # 6. Drug-level 결과
    print("\n[6] Drug-level 결과")
    name_col = "DRUG_NAME" if "DRUG_NAME" in top_drugs.columns else "drug_name_norm"

    drugs_with_expressed_target = set()
    drugs_with_cptac_target = set()

    for er in expression_results:
        for d in er["drugs"]:
            drugs_with_cptac_target.add(d)
            if er["is_expressed"]:
                drugs_with_expressed_target.add(d)

    all_drug_names = set(top_drugs[name_col].dropna())
    hit_total = len(drugs_with_cptac_target & all_drug_names)
    hit_expressed = len(drugs_with_expressed_target & all_drug_names)

    print(f"  Drugs with target in CPTAC: {hit_total}/{len(top_drugs)}")
    print(f"  Drugs with EXPRESSED target: {hit_expressed}/{len(top_drugs)}")

    # 7. 저장
    print("\n[7] 저장")

    results = {
        "validation_source": "CPTAC",
        "disease": "colorectal cancer (COAD)",
        "dataset": "coad_cptac_2019",
        "top_n_drugs": len(top_drugs),
        "target_genes_extracted": len(target_genes),
        "mrna_genes": mrna_df.shape[0] if mrna_df is not None else 0,
        "mrna_patients": mrna_df.shape[1] - 2 if mrna_df is not None else 0,
        "coad_read_distribution": coad_read_dist,
        "targets_in_cptac": sum(1 for er in expression_results),
        "targets_expressed": sum(1 for er in expression_results if er["is_expressed"]),
        "drugs_with_target": hit_total,
        "drugs_with_expressed_target": hit_expressed,
        "hit_rate_target": round(hit_total / len(top_drugs), 4),
        "hit_rate_expressed": round(hit_expressed / len(top_drugs), 4),
        "hit_rate_target_pct": round(hit_total / len(top_drugs) * 100, 1),
        "hit_rate_expressed_pct": round(hit_expressed / len(top_drugs) * 100, 1),
        "expression_details": expression_results,
        "drugs_matched": sorted(list(drugs_with_expressed_target & all_drug_names)),
        "drugs_unmatched": sorted(list(all_drug_names - drugs_with_expressed_target)),
    }

    results_path = results_dir / "colon_cptac_validation_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  ✅ {results_path}")

    if expression_results:
        expr_df = pd.DataFrame(expression_results)
        expr_df["drugs"] = expr_df["drugs"].apply(lambda x: ", ".join(x))
        expr_csv = results_dir / "colon_cptac_matched_drugs.csv"
        expr_df.to_csv(expr_csv, index=False)
        print(f"  ✅ {expr_csv}")

    # 8. 요약
    print("\n" + "=" * 80)
    print("CPTAC Validation Summary")
    print("=" * 80)
    print(f"  Dataset: coad_cptac_2019")
    print(f"  Patients: {results['mrna_patients']}")
    print(f"  Target genes: {len(target_genes)} extracted → {results['targets_in_cptac']} in CPTAC")
    print(f"  Expressed targets: {results['targets_expressed']}")
    print(f"  Drugs with expressed target: {hit_expressed}/{len(top_drugs)} ({results['hit_rate_expressed_pct']}%)")
    if coad_read_dist:
        print(f"  COAD/READ distribution: {coad_read_dist}")

    print()
    print("  Expression details:")
    for er in sorted(expression_results, key=lambda x: x["median_expression"], reverse=True)[:10]:
        status = "✅" if er["is_expressed"] else "❌"
        print(
            f"    {status} {er['gene']:15s} median={er['median_expression']:10.2f} "
            f"pct_expr={er['pct_patients_expressed']:5.1f}% "
            f"drugs={', '.join(er['drugs'][:3])}"
        )

    print("\n✅ Step 6-5 완료!")


if __name__ == "__main__":
    main()
