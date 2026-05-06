# BRCA Step7 ADMET 22-Assay

- Date: 2026-04-28
- Input: current BRCA Top30 (all drugs entered Step7)
- Method: TDC ADMET 22 assays + Tanimoto similarity v1
- Assay source: `/Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/curated_data/admet/tdc_admet_group/admet_group`

## Summary

- Total evaluated: **30**
- PASS: **6**
- WARNING: **21**
- FAIL: **3**
- Hard fail: **2**

## Final 15

| Final Rank | Orig Rank | Drug | Tier | Verdict | Safety Score | Hard Fail | Soft Flags |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
| 1 | 18 | Nelarabine | 유방암 비사용 치료제 | PASS | 33.285 | 0 | - |
| 2 | 16 | Ruxolitinib | 유방암 적응증 확장 연구 치료제 | PASS | 30.776 | 0 | - |
| 3 | 10 | Fludarabine | 유방암 비사용 치료제 | PASS | 12.160 | 0 | - |
| 4 | 5 | Temozolomide | 유방암 적응증 확장 연구 치료제 | PASS | 6.576 | 0 | - |
| 5 | 11 | 5-Fluorouracil | 유방암 치료제 | PASS | 6.129 | 0 | - |
| 6 | 4 | alpha-lipoic acid | 화합물 또는 미지 약물 | PASS | 6.073 | 0 | - |
| 7 | 25 | AZD1208 | 화합물 또는 미지 약물 | WARNING | 43.506 | 0 | PPBR_high |
| 8 | 22 | Cyclophosphamide | 유방암 치료제 | WARNING | 12.869 | 0 | Ames |
| 9 | 2 | N-acetyl cysteine | 화합물 또는 미지 약물 | WARNING | 7.259 | 0 | Ames |
| 10 | 8 | BEN | 화합물 또는 미지 약물 | WARNING | 5.000 | 0 | - |
| 11 | 9 | Oxaliplatin | 유방암 적응증 확장 연구 치료제 | WARNING | 5.000 | 0 | - |
| 12 | 13 | A-366 | 화합물 또는 미지 약물 | WARNING | 5.000 | 0 | - |
| 13 | 21 | PRIMA-1MET | 화합물 또는 미지 약물 | WARNING | 5.000 | 0 | - |
| 14 | 24 | PCI-34051 | 화합물 또는 미지 약물 | WARNING | 5.000 | 0 | - |
| 15 | 28 | ML323 | 화합물 또는 미지 약물 | WARNING | 5.000 | 0 | - |

## Note

- This Step7 selection keeps all 30 drugs as input and selects the final 15 after ADMET filtering.
- Tier 1/2/3/4 labels are preserved from the existing BRCA classification table.
