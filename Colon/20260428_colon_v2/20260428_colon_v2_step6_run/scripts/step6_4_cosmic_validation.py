#!/usr/bin/env python3
"""
Step 6-4: COSMIC 외부 검증

COSMIC Cancer Gene Census + Actionability 데이터에서
우리 Top 30 약물의 타겟 유전자가 CRC 드라이버/actionable 인지 검증.

입력:
  - results/colon_top30_drugs_ensemble.csv
  - curated_data/validation/cosmic/*.tar (해제 후 사용)

출력:
  - results/colon_cosmic_validation_results.json
  - results/colon_cosmic_matched_drugs.csv
"""

import io
import json
import gzip
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd

from colon_validation_matching_utils import (
    load_aliases,
    match_drugs_in_cosmic_actionability_combos,
)

ALIASES_PATH = Path(__file__).resolve().parent / "colon_validation_drug_aliases.json"


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


def extract_tar_files(cosmic_dir):
    """COSMIC tar 파일 해제"""
    extract_dir = cosmic_dir / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)

    extracted_files = []
    for tar_path in sorted(cosmic_dir.glob("*.tar")):
        print(f"  Extracting: {tar_path.name}")
        try:
            with tarfile.open(tar_path) as tar:
                tar.extractall(path=extract_dir)
                extracted_files.extend(tar.getnames())
        except Exception as e:
            print(f"    ERROR: {e}")

    print(f"  Extracted {len(extracted_files)} files to {extract_dir}")
    return extract_dir


def load_cancer_gene_census(extract_dir):
    """Cancer Gene Census 로드"""
    # tsv.gz 파일 찾기
    cgc_files = list(extract_dir.rglob("*CancerGeneCensus*.tsv.gz"))
    if not cgc_files:
        cgc_files = list(extract_dir.rglob("*CancerGeneCensus*.tsv"))
    if not cgc_files:
        print("  WARNING: Cancer Gene Census file not found")
        return None

    path = cgc_files[0]
    print(f"  Loading CGC: {path.name}")

    if str(path).endswith(".gz"):
        df = pd.read_csv(path, sep="\t", compression="gzip")
    else:
        df = pd.read_csv(path, sep="\t")

    print(f"  CGC rows: {len(df)}, columns: {list(df.columns[:10])}")
    return df


def load_actionability(extract_dir):
    """Actionability 데이터 로드"""
    act_files = list(extract_dir.rglob("*Actionability*.tsv"))
    if not act_files:
        act_files = list(extract_dir.rglob("*Actionability*.tsv.gz"))
    if not act_files:
        print("  WARNING: Actionability file not found")
        return None

    path = act_files[0]
    print(f"  Loading Actionability: {path.name}")

    if str(path).endswith(".gz"):
        df = pd.read_csv(path, sep="\t", compression="gzip")
    else:
        df = pd.read_csv(path, sep="\t")

    print(f"  Actionability rows: {len(df)}, columns: {list(df.columns[:10])}")
    return df


def filter_colorectal(df, tissue_col=None):
    """CRC 관련 행 필터"""
    if df is None or len(df) == 0:
        return df

    # tissue/cancer type 관련 컬럼 찾기
    crc_keywords = ["colorectal", "colon", "rectal", "large_intestine", "large intestine", "coad", "read"]

    candidate_cols = []
    for col in df.columns:
        if any(k in col.lower() for k in ["tissue", "cancer", "tumour", "tumor", "site", "disease", "type"]):
            candidate_cols.append(col)

    if tissue_col and tissue_col in df.columns:
        candidate_cols = [tissue_col] + [c for c in candidate_cols if c != tissue_col]

    if not candidate_cols:
        # 전체 데이터에서 CRC 키워드 검색
        print("  No tissue column found, searching all text columns...")
        for col in df.select_dtypes(include="object").columns:
            sample = df[col].dropna().astype(str).str.lower()
            if sample.str.contains("|".join(crc_keywords)).any():
                candidate_cols.append(col)

    crc_mask = pd.Series(False, index=df.index)
    used_cols = []

    for col in candidate_cols:
        col_mask = df[col].astype(str).str.lower().str.contains("|".join(crc_keywords), na=False)
        if col_mask.any():
            crc_mask = crc_mask | col_mask
            used_cols.append(col)

    crc_df = df[crc_mask]
    print(f"  CRC filter: {len(crc_df)}/{len(df)} rows (columns: {used_cols})")
    return crc_df


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

        # 타겟은 보통 쉼표 또는 세미콜론으로 구분
        for gene in target_str.replace(";", ",").split(","):
            gene = gene.strip().upper()
            if gene and len(gene) >= 2:
                if gene not in targets:
                    targets[gene] = []
                targets[gene].append(drug_name)

    print(f"  Extracted {len(targets)} unique target genes from {len(top_drugs)} drugs")
    return targets


def match_targets_to_cosmic(target_genes, cgc_df, act_df):
    """타겟 유전자를 COSMIC CGC/Actionability 와 매칭"""
    results = []

    # CGC 유전자 목록
    cgc_genes = set()
    cgc_gene_col = None
    if cgc_df is not None:
        for col in ["Gene Symbol", "GENE_SYMBOL", "gene_symbol", "Gene"]:
            if col in cgc_df.columns:
                cgc_gene_col = col
                cgc_genes = set(cgc_df[col].dropna().str.upper())
                break
        print(f"  CGC genes: {len(cgc_genes)}")

    # Actionability 유전자/약물
    act_genes = set()
    act_drugs = set()
    if act_df is not None:
        for col in ["Gene", "GENE", "gene", "Gene Symbol"]:
            if col in act_df.columns:
                act_genes = set(act_df[col].dropna().str.upper())
                break
        for col in ["Drug", "DRUG", "drug", "Drug Name"]:
            if col in act_df.columns:
                act_drugs = set(act_df[col].dropna().str.lower())
                break
        print(f"  Actionability genes: {len(act_genes)}, drugs: {len(act_drugs)}")

    # 매칭
    for gene, drugs in target_genes.items():
        in_cgc = gene in cgc_genes
        in_act = gene in act_genes

        if in_cgc or in_act:
            results.append(
                {
                    "gene": gene,
                    "drugs": drugs,
                    "in_cgc": in_cgc,
                    "in_actionability": in_act,
                }
            )

    print(f"  Matched target genes: {len(results)}/{len(target_genes)}")
    return results


def main():
    base_dir = Path(__file__).parent.parent
    results_dir = base_dir / "results"
    cosmic_dir = base_dir / "curated_data" / "validation" / "cosmic"

    print("=" * 80)
    print("Step 6-4: COSMIC External Validation")
    print("=" * 80)

    # 1. Top drugs
    print("\n[1] Top drugs 로드")
    top_drugs = load_top_drugs(results_dir)

    # 2. COSMIC tar 해제
    print("\n[2] COSMIC tar 해제")
    extract_dir = extract_tar_files(cosmic_dir)

    # 3. CGC 로드
    print("\n[3] Cancer Gene Census 로드")
    cgc_df = load_cancer_gene_census(extract_dir)

    # 4. Actionability 로드
    print("\n[4] Actionability 로드")
    act_df = load_actionability(extract_dir)

    # 5. CRC 필터
    print("\n[5] CRC 필터링")
    cgc_crc = filter_colorectal(cgc_df) if cgc_df is not None else None
    act_crc = filter_colorectal(act_df) if act_df is not None else None

    # 6. 타겟 유전자 추출
    print("\n[6] 타겟 유전자 추출")
    target_genes = extract_target_genes(top_drugs)

    # 7. 매칭 (전체 COSMIC)
    print("\n[7] COSMIC 매칭 (전체)")
    matched_all = match_targets_to_cosmic(target_genes, cgc_df, act_df)

    # 8. 매칭 (CRC 전용)
    print("\n[8] COSMIC 매칭 (CRC 전용)")
    matched_crc = match_targets_to_cosmic(target_genes, cgc_crc, act_crc)

    # 9. Drug-level 매칭 결과
    print("\n[9] Drug-level 결과")
    name_col = "DRUG_NAME" if "DRUG_NAME" in top_drugs.columns else "drug_name_norm"

    # 어떤 약물의 타겟이 COSMIC 에 있는지
    drugs_with_cosmic_target_all = set()
    drugs_with_cosmic_target_crc = set()

    for m in matched_all:
        for d in m["drugs"]:
            drugs_with_cosmic_target_all.add(d)

    for m in matched_crc:
        for d in m["drugs"]:
            drugs_with_cosmic_target_crc.add(d)

    # Actionability DRUG_COMBINATION 문자열에서 약물명 직접 매칭 (CGC 타겟 미포함 약물 보완)
    print("\n[9b] Actionability 약물명 매칭 (DRUG_COMBINATION)")
    aliases_data = load_aliases(ALIASES_PATH)
    hits_combo_all, rows_any = match_drugs_in_cosmic_actionability_combos(
        act_df, top_drugs, name_col, aliases_data, crc_rows_only=False
    )
    hits_combo_crc, rows_crc = match_drugs_in_cosmic_actionability_combos(
        act_df, top_drugs, name_col, aliases_data, crc_rows_only=True
    )
    print(f"  Actionability rows scanned (any): {rows_any}, CRC-filtered: {rows_crc}")
    print(f"  Combo hits (any disease): {len(hits_combo_all)}, combo hits (CRC disease text): {len(hits_combo_crc)}")

    drugs_with_cosmic_target_all |= hits_combo_all
    drugs_with_cosmic_target_crc |= hits_combo_crc

    all_drug_names = set(top_drugs[name_col].dropna())
    hit_all = len(drugs_with_cosmic_target_all & all_drug_names)
    hit_crc = len(drugs_with_cosmic_target_crc & all_drug_names)

    print(f"  Drugs with COSMIC target (all): {hit_all}/{len(top_drugs)}")
    print(f"  Drugs with COSMIC target (CRC): {hit_crc}/{len(top_drugs)}")

    # 10. 저장
    print("\n[10] 저장")

    results = {
        "validation_source": "COSMIC",
        "disease": "colorectal cancer",
        "top_n_drugs": len(top_drugs),
        "target_genes_extracted": len(target_genes),
        "cgc_total_genes": len(cgc_df) if cgc_df is not None else 0,
        "cgc_crc_genes": len(cgc_crc) if cgc_crc is not None else 0,
        "actionability_total": len(act_df) if act_df is not None else 0,
        "actionability_crc": len(act_crc) if act_crc is not None else 0,
        "matched_genes_all": len(matched_all),
        "matched_genes_crc": len(matched_crc),
        "drugs_with_cosmic_target_all": hit_all,
        "drugs_with_cosmic_target_crc": hit_crc,
        "hit_rate_all": round(hit_all / len(top_drugs), 4),
        "hit_rate_crc": round(hit_crc / len(top_drugs), 4),
        "hit_rate_all_pct": round(hit_all / len(top_drugs) * 100, 1),
        "hit_rate_crc_pct": round(hit_crc / len(top_drugs) * 100, 1),
        "matched_genes_detail_all": matched_all,
        "matched_genes_detail_crc": matched_crc,
        "actionability_combo_rows_scanned_any": rows_any,
        "actionability_combo_rows_scanned_crc": rows_crc,
        "drugs_matched_via_actionability_combo_any": sorted(hits_combo_all),
        "drugs_matched_via_actionability_combo_crc": sorted(hits_combo_crc),
        "drugs_matched_all": sorted(list(drugs_with_cosmic_target_all & all_drug_names)),
        "drugs_matched_crc": sorted(list(drugs_with_cosmic_target_crc & all_drug_names)),
        "drugs_unmatched": sorted(list(all_drug_names - drugs_with_cosmic_target_all)),
    }

    results_path = results_dir / "colon_cosmic_validation_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  ✅ {results_path}")

    # 매칭 약물 CSV
    if matched_all:
        rows = []
        for m in matched_all:
            for d in m["drugs"]:
                rows.append(
                    {
                        "drug_name": d,
                        "target_gene": m["gene"],
                        "in_cgc": m["in_cgc"],
                        "in_actionability": m["in_actionability"],
                    }
                )
        matched_df = pd.DataFrame(rows)
        matched_csv = results_dir / "colon_cosmic_matched_drugs.csv"
        matched_df.to_csv(matched_csv, index=False)
        print(f"  ✅ {matched_csv}")

    # 11. 요약
    print("\n" + "=" * 80)
    print("COSMIC Validation Summary")
    print("=" * 80)
    print(f"  Target genes from Top 30: {len(target_genes)}")
    print(f"  COSMIC matched (all cancer): {hit_all}/{len(top_drugs)} ({results['hit_rate_all_pct']}%)")
    print(f"  COSMIC matched (CRC only): {hit_crc}/{len(top_drugs)} ({results['hit_rate_crc_pct']}%)")
    print(f"  Matched drugs (all): {sorted(list(drugs_with_cosmic_target_all & all_drug_names))}")

    print("\n✅ Step 6-4 완료!")


if __name__ == "__main__":
    main()
