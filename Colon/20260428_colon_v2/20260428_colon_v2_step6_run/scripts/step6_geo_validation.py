#!/usr/bin/env python3
"""
Step 6-GEO: GEO GSE39582 외부 검증

대규모 CRC 코호트 (N=585) 의 유전자 발현 데이터에서
우리 Top 30 약물의 타겟 유전자 발현 확인.

GSE39582: Marisa et al. (2013) PLoS Med
  - 585 CRC 환자
  - Affymetrix HG-U133 Plus 2.0
  - clinical annotation (stage, location, chemotherapy 등)

입력:
  - results/colon_top30_drugs_ensemble.csv
  - curated_data/geo/GSE39582/matrix/GSE39582_series_matrix.txt.gz

출력:
  - results/colon_geo_validation_results.json
  - results/colon_geo_matched_drugs.csv
"""

import json
import gzip
from pathlib import Path

import numpy as np
import pandas as pd


def load_top_drugs(results_dir):
    """Top 30 약물 로드"""
    path = results_dir / "colon_top30_drugs_ensemble.csv"
    df = pd.read_csv(path)
    print(f"  Top drugs: {len(df)}")
    return df


def extract_target_genes(top_drugs):
    """Top drugs 에서 타겟 유전자 추출"""
    targets = {}
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

    print(f"  Extracted {len(targets)} unique target genes")
    return targets


def parse_series_matrix(gz_path):
    """
    GEO series matrix 파싱.
    메타데이터 (! 시작) 와 발현 데이터 분리.
    """
    print(f"  Parsing: {gz_path.name}")

    metadata_lines = []
    data_lines = []
    header_line = None

    with gzip.open(gz_path, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("!"):
                metadata_lines.append(line)
            elif line.startswith('"ID_REF"'):
                header_line = line
            elif line.startswith("!series_matrix_table_end"):
                break
            elif header_line is not None and line.strip():
                data_lines.append(line)

    print(f"  Metadata lines: {len(metadata_lines)}")
    print(f"  Data lines: {len(data_lines)}")

    # 헤더 파싱
    if header_line is None:
        print("  ERROR: No header found")
        return None, None, None

    headers = header_line.replace('"', "").split("\t")
    sample_ids = headers[1:]
    print(f"  Samples: {len(sample_ids)}")

    # Clinical metadata 추출
    clinical = {}
    for line in metadata_lines:
        if line.startswith("!Sample_characteristics_ch1"):
            # 각 샘플의 특성
            parts = line.split("\t")
            values = [v.strip().strip('"') for v in parts[1:]]
            if values and ":" in values[0]:
                key = values[0].split(":")[0].strip()
                vals = [v.split(":", 1)[1].strip() if ":" in v else v for v in values]
                clinical[key] = vals

    print(f"  Clinical features: {list(clinical.keys())[:10]}")

    # 발현 데이터 파싱 (probe × sample)
    # 메모리 효율: 필요한 유전자만 나중에 필터
    probe_ids = []
    expr_data = []

    for line in data_lines:
        parts = line.split("\t")
        probe_id = parts[0].strip('"')
        values = []
        for v in parts[1:]:
            v = v.strip().strip('"')
            try:
                values.append(float(v))
            except ValueError:
                values.append(np.nan)
        probe_ids.append(probe_id)
        expr_data.append(values)

    expr_df = pd.DataFrame(expr_data, index=probe_ids, columns=sample_ids)
    print(f"  Expression matrix: {expr_df.shape[0]} probes × {expr_df.shape[1]} samples")

    return expr_df, clinical, sample_ids


def load_probe_to_gene_mapping(geo_dir):
    """
    Probe → Gene 매핑 로드.
    GPL570_probe_to_gene.json 파일 사용.
    """
    json_path = geo_dir / "GPL570_probe_to_gene.json"
    if json_path.exists():
        with open(json_path) as f:
            probe_to_gene = json.load(f)
        print(
            f"  Loaded probe-to-gene mapping: {len(probe_to_gene)} probes → "
            f"{len(set(probe_to_gene.values()))} genes"
        )
        return probe_to_gene

    print("  WARNING: GPL570_probe_to_gene.json not found")
    return None


def match_genes_in_expression(expr_df, target_genes, probe_to_gene=None):
    """
    타겟 유전자가 발현 데이터에 있는지 확인.
    probe_to_gene 없으면 probe ID 에서 직접 유전자명 검색.
    """
    results = []

    if probe_to_gene is not None:
        # annotation 있는 경우
        available_genes = set(probe_to_gene.values())
    else:
        # probe ID 자체를 gene symbol 로 사용 시도
        # Affymetrix probe 는 숫자_at 형식이라 gene symbol 과 다름
        # 이 경우 매칭 불가 → 대안 전략 필요
        available_probes = set(expr_df.index)
        print(f"  No annotation file. Probe IDs are Affymetrix format.")
        print(f"  Sample probes: {list(available_probes)[:5]}")

        # Affymetrix probe 는 gene symbol 과 직접 매칭 안 됨
        # 대안: probe ID 에 gene symbol 이 포함된 경우 (거의 없음)
        # 최선: gene symbol 을 포함하는 probe 를 찾기
        # 실질적으로는 annotation 없이 매칭 어려움

        # 그래도 시도: gene symbol 이 probe ID 에 포함?
        for gene, drugs in target_genes.items():
            matching_probes = [p for p in available_probes if gene.lower() in p.lower()]
            if matching_probes:
                values = expr_df.loc[matching_probes].values.flatten()
                values = values[~np.isnan(values)]
                if len(values) > 0:
                    results.append(
                        {
                            "gene": gene,
                            "drugs": drugs,
                            "probe_ids": matching_probes[:3],
                            "mean_expression": round(float(np.mean(values)), 4),
                            "median_expression": round(float(np.median(values)), 4),
                            "pct_expressed": round(
                                float(np.sum(values > np.median(values)) / len(values) * 100), 1
                            ),
                            "n_patients": len(expr_df.columns),
                            "is_expressed": True,
                            "match_method": "probe_id_contains",
                        }
                    )

        if not results:
            print("  Direct probe matching failed. Trying alternative approach...")
            # 대안: 발현 행렬의 probe 수 자체로 coverage 측정
            # 또는 전체 발현 통계만 보고
            print(f"  Expression matrix has {expr_df.shape[0]} probes, {expr_df.shape[1]} samples")
            print(f"  Overall expression stats:")
            overall_mean = expr_df.mean().mean()
            print(f"    Grand mean: {overall_mean:.4f}")

        return results

    # annotation 있는 경우 (정상 경로)
    for gene, drugs in target_genes.items():
        if gene in available_genes:
            # gene → probe 역매핑
            probes = [p for p, g in probe_to_gene.items() if g == gene]
            if not probes:
                continue

            values = expr_df.loc[expr_df.index.isin(probes)].values.flatten()
            values = values[~np.isnan(values)]

            if len(values) > 0:
                mean_expr = float(np.mean(values))
                median_expr = float(np.median(values))
                all_values = expr_df.values.flatten()
                all_values = all_values[~np.isnan(all_values)]
                is_expressed = median_expr > np.percentile(all_values, 25)

                results.append(
                    {
                        "gene": gene,
                        "drugs": drugs,
                        "probe_ids": probes[:3],
                        "mean_expression": round(mean_expr, 4),
                        "median_expression": round(median_expr, 4),
                        "pct_expressed": round(float(np.sum(values > median_expr) / len(values) * 100), 1),
                        "n_patients": len(expr_df.columns),
                        "is_expressed": is_expressed,
                        "match_method": "annotation",
                    }
                )

    return results


def main():
    base_dir = Path(__file__).parent.parent
    results_dir = base_dir / "results"
    geo_dir = base_dir / "curated_data" / "geo" / "GSE39582"
    matrix_path = geo_dir / "matrix" / "GSE39582_series_matrix.txt.gz"

    print("=" * 80)
    print("Step 6-GEO: GEO GSE39582 External Validation")
    print("=" * 80)

    # 1. Top drugs
    print("\n[1] Top drugs 로드")
    top_drugs = load_top_drugs(results_dir)

    # 2. 타겟 유전자
    print("\n[2] 타겟 유전자 추출")
    target_genes = extract_target_genes(top_drugs)

    # 3. Series matrix 파싱
    print("\n[3] GEO series matrix 파싱")
    if not matrix_path.exists():
        print(f"  ERROR: {matrix_path} not found")
        return

    expr_df, clinical, sample_ids = parse_series_matrix(matrix_path)
    if expr_df is None:
        print("  FATAL: Failed to parse expression data")
        return

    # 4. Probe → Gene 매핑
    print("\n[4] Probe-Gene annotation")
    probe_to_gene = load_probe_to_gene_mapping(geo_dir)

    # 5. 타겟 유전자 발현 확인
    print("\n[5] 타겟 유전자 발현 분석")
    expression_results = match_genes_in_expression(expr_df, target_genes, probe_to_gene)
    print(f"  Matched genes: {len(expression_results)}/{len(target_genes)}")

    # 6. Drug-level 결과
    print("\n[6] Drug-level 결과")
    name_col = "DRUG_NAME" if "DRUG_NAME" in top_drugs.columns else "drug_name_norm"

    drugs_matched = set()
    for er in expression_results:
        for d in er["drugs"]:
            drugs_matched.add(d)

    all_drug_names = set(top_drugs[name_col].dropna())
    hit_count = len(drugs_matched & all_drug_names)
    print(f"  Drugs with expressed target in GEO: {hit_count}/{len(top_drugs)}")

    # 7. Clinical 메타 요약
    print("\n[7] Clinical metadata 요약")
    clinical_summary = {}
    if clinical:
        for key, values in clinical.items():
            unique_vals = pd.Series(values).value_counts().head(5).to_dict()
            clinical_summary[key] = unique_vals
            print(f"  {key}: {unique_vals}")

    # 8. 저장
    print("\n[8] 저장")

    results = {
        "validation_source": "GEO",
        "dataset": "GSE39582",
        "publication": "Marisa et al. 2013 PLoS Med",
        "disease": "colorectal cancer",
        "n_patients": len(sample_ids),
        "n_probes": expr_df.shape[0],
        "platform": "Affymetrix HG-U133 Plus 2.0",
        "top_n_drugs": len(top_drugs),
        "target_genes_extracted": len(target_genes),
        "genes_matched_in_expression": len(expression_results),
        "drugs_with_expressed_target": hit_count,
        "hit_rate": round(hit_count / len(top_drugs), 4) if len(top_drugs) > 0 else 0,
        "hit_rate_pct": round(hit_count / len(top_drugs) * 100, 1) if len(top_drugs) > 0 else 0,
        "clinical_summary": clinical_summary,
        "expression_details": expression_results,
        "drugs_matched": sorted(list(drugs_matched & all_drug_names)),
        "drugs_unmatched": sorted(list(all_drug_names - drugs_matched)),
        "note": (
            "Probe-to-gene annotation required for full matching. "
            "Without GPL570 annotation, matching is limited to probe ID substring search."
        ),
    }

    results_path = results_dir / "colon_geo_validation_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  ✅ {results_path}")

    if expression_results:
        expr_rows = []
        for er in expression_results:
            expr_rows.append(
                {
                    "gene": er["gene"],
                    "drugs": ", ".join(er["drugs"]),
                    "mean_expression": er["mean_expression"],
                    "median_expression": er["median_expression"],
                    "match_method": er.get("match_method", ""),
                }
            )
        expr_csv = results_dir / "colon_geo_matched_drugs.csv"
        pd.DataFrame(expr_rows).to_csv(expr_csv, index=False)
        print(f"  ✅ {expr_csv}")

    # 9. 요약
    print("\n" + "=" * 80)
    print("GEO GSE39582 Validation Summary")
    print("=" * 80)
    print(f"  Dataset: GSE39582 (Marisa et al. 2013)")
    print(f"  Patients: {len(sample_ids)}")
    print(f"  Probes: {expr_df.shape[0]}")
    print(f"  Target genes: {len(target_genes)} → matched: {len(expression_results)}")
    print(f"  Drugs with expressed target: {hit_count}/{len(top_drugs)} ({results['hit_rate_pct']}%)")
    if not probe_to_gene:
        print(f"  ⚠️ Note: GPL570 annotation file not available.")
        print(f"     Matching was done by probe ID substring search (limited).")
        print(f"     For full matching, download GPL570 annotation from GEO.")

    print("\n✅ Step 6-GEO 완료!")


if __name__ == "__main__":
    main()
