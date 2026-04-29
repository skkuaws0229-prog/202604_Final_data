# BRCA Step6 METABRIC Validation

- Date: 2026-04-28
- Input Top30: `brca_directive_top30_unique_candidates.csv`
- Validation scope: `METABRIC Method A/B/C`
- Expression input: `/Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_protocol_choi/data/metabric/metabric_expression_basic_clean_20260406.parquet`
- Clinical input: `/Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_protocol_choi/data/metabric/metabric_clinical_patient_basic_clean_20260406.parquet`

## Summary

- Top30 drugs evaluated: **30**
- Method A target-expressed drugs: **11/30**
- Method A BRCA-pathway drugs: **12/30**
- Method B survival-significant drugs: **2/30**

## Method C

| Metric | Precision | Hits | Total |
| --- | ---: | ---: | ---: |
| P@5 | 0.000 | 0 | 5 |
| P@10 | 0.200 | 2 | 10 |
| P@15 | 0.200 | 3 | 15 |
| P@20 | 0.150 | 3 | 20 |
| P@25 | 0.160 | 4 | 25 |
| P@30 | 0.133 | 4 | 30 |

## Known BRCA Matches In Top30

| Rank | Drug |
| --- | --- |
| 9 | Oxaliplatin |
| 10 | Fludarabine |
| 11 | 5-Fluorouracil |
| 22 | Cyclophosphamide |

## Top15 After METABRIC A/B/C

| Final Rank | Original Rank | Drug | Validation Score | Expr | Pathway | Survival | Known BRCA | Tier |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 24 | PCI-34051 | 7.26 | 1 | 1 | 1 | 0 | 화합물 또는 미지 약물 |
| 2 | 17 | SB216763 | 6.04 | 1 | 0 | 1 | 0 | 화합물 또는 미지 약물 |
| 3 | 9 | Oxaliplatin | 5.40 | 0 | 1 | 0 | 1 | 유방암 적응증 확장 연구 치료제 |
| 4 | 22 | Cyclophosphamide | 4.84 | 0 | 1 | 0 | 1 | 유방암 치료제 |
| 5 | 12 | CCT007093 | 4.73 | 1 | 1 | 0 | 0 | 화합물 또는 미지 약물 |
| 6 | 28 | ML323 | 4.62 | 1 | 1 | 0 | 0 | 화합물 또는 미지 약물 |
| 7 | 10 | Fludarabine | 4.31 | 0 | 1 | 0 | 1 | 유방암 비사용 치료제 |
| 8 | 26 | Lenalidomide | 4.19 | 1 | 1 | 0 | 0 | 유방암 비사용 치료제 |
| 9 | 19 | Veliparib | 3.95 | 1 | 1 | 0 | 0 | 유방암 적응증 확장 연구 치료제 |
| 10 | 13 | A-366 | 3.69 | 1 | 0 | 0 | 0 | 화합물 또는 미지 약물 |
| 11 | 16 | Ruxolitinib | 3.59 | 1 | 0 | 0 | 0 | 유방암 적응증 확장 연구 치료제 |
| 12 | 5 | Temozolomide | 3.25 | 0 | 1 | 0 | 0 | 유방암 적응증 확장 연구 치료제 |
| 13 | 18 | Nelarabine | 2.99 | 0 | 1 | 0 | 0 | 유방암 비사용 치료제 |
| 14 | 20 | MIRA-1 | 2.91 | 1 | 0 | 0 | 0 | 화합물 또는 미지 약물 |
| 15 | 11 | 5-Fluorouracil | 2.77 | 0 | 0 | 0 | 1 | 유방암 치료제 |

## Next

- Supplemental interpretation can be done with `ClinicalTrials.gov + manual review`.
- Step7 ADMET remains a separate stage and is not included in this Step6 output.
