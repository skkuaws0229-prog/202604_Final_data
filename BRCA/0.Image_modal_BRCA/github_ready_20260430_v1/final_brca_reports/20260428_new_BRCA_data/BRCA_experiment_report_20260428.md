# BRCA Experiment Report

- Date: 2026-04-28
- Experiment line: Step4 screening -> Step5 directive ensemble -> Step6 METABRIC -> Step7 ADMET 22 assay

## Executive Summary

- Ensemble winner: `A`
- GroupCV Spearman: `0.4834`
- ScaffoldCV Spearman: `0.3644`
- Holdout Spearman: `0.7847`
- Top30 generated: `30`
- Step6 Top15 generated: `15`
- Step7 Final15 generated: `15`

## Step4 Shortlist Context

| Phase | Family | Model | GroupCV | ScaffoldCV | Overfit Gap |
| --- | --- | --- | ---: | ---: | ---: |
| 2C | ML | CatBoost | 0.4695 | 0.4157 | 0.2865 |
| 2C | ML | LightGBM | 0.4604 | 0.3925 | 0.3556 |
| 2C | ML | XGBoost | 0.4601 | 0.3189 | 0.3592 |
| 2C | ML | RandomForest | 0.4450 | 0.3617 | 0.4865 |
| 2C | DL | ResidualMLP | 0.4390 | 0.3876 | 0.3421 |

## Step5 Top30 Tier Mix

| Tier | Count |
| --- | ---: |
| 화합물 또는 미지 약물 | 19 |
| 유방암 적응증 확장 연구 치료제 | 5 |
| 유방암 비사용 치료제 | 4 |
| 유방암 치료제 | 2 |

## Step6 Highlights

- Target-expressed drugs: `9` within Step6 Top15
- Survival-significant drugs in Step6 Top15: `2`

| Step6 Rank | Drug | Tier | Validation Score |
| --- | --- | --- | ---: |
| 1 | PCI-34051 | 화합물 또는 미지 약물 | 7.264 |
| 2 | SB216763 | 화합물 또는 미지 약물 | 6.039 |
| 3 | Oxaliplatin | 유방암 적응증 확장 연구 치료제 | 5.396 |
| 4 | Cyclophosphamide | 유방암 치료제 | 4.837 |
| 5 | CCT007093 | 화합물 또는 미지 약물 | 4.732 |
| 6 | ML323 | 화합물 또는 미지 약물 | 4.618 |
| 7 | Fludarabine | 유방암 비사용 치료제 | 4.315 |
| 8 | Lenalidomide | 유방암 비사용 치료제 | 4.191 |
| 9 | Veliparib | 유방암 적응증 확장 연구 치료제 | 3.950 |
| 10 | A-366 | 화합물 또는 미지 약물 | 3.693 |

## Step7 Highlights

- PASS: `6`
- WARNING: `21`
- FAIL: `3`
- Hard fail: `2`

| Final ADMET Rank | Drug | Tier | Verdict | Safety Score | Assay Matches |
| --- | --- | --- | --- | ---: | ---: |
| 1 | Nelarabine | 유방암 비사용 치료제 | PASS | 33.285 | 7 |
| 2 | Ruxolitinib | 유방암 적응증 확장 연구 치료제 | PASS | 30.776 | 2 |
| 3 | Fludarabine | 유방암 비사용 치료제 | PASS | 12.160 | 6 |
| 4 | Temozolomide | 유방암 적응증 확장 연구 치료제 | PASS | 6.576 | 5 |
| 5 | 5-Fluorouracil | 유방암 치료제 | PASS | 6.129 | 7 |
| 6 | alpha-lipoic acid | 화합물 또는 미지 약물 | PASS | 6.073 | 5 |
| 7 | AZD1208 | 화합물 또는 미지 약물 | WARNING | 43.506 | 4 |
| 8 | Cyclophosphamide | 유방암 치료제 | WARNING | 12.869 | 8 |
| 9 | N-acetyl cysteine | 화합물 또는 미지 약물 | WARNING | 7.259 | 4 |
| 10 | BEN | 화합물 또는 미지 약물 | WARNING | 5.000 | 3 |
| 11 | Oxaliplatin | 유방암 적응증 확장 연구 치료제 | WARNING | 5.000 | 0 |
| 12 | A-366 | 화합물 또는 미지 약물 | WARNING | 5.000 | 0 |
| 13 | PRIMA-1MET | 화합물 또는 미지 약물 | WARNING | 5.000 | 0 |
| 14 | PCI-34051 | 화합물 또는 미지 약물 | WARNING | 5.000 | 0 |
| 15 | ML323 | 화합물 또는 미지 약물 | WARNING | 5.000 | 0 |

## Final15 Tier Distribution

| Tier | Count |
| --- | ---: |
| 화합물 또는 미지 약물 | 8 |
| 유방암 적응증 확장 연구 치료제 | 3 |
| 유방암 비사용 치료제 | 2 |
| 유방암 치료제 | 2 |

## Interpretation

- This rerun keeps the full Step5 Top30 through Step7, matching the current agreed scope.
- Step6 METABRIC acts as a biological validation layer, while Step7 ADMET 22 assay is the practical selection layer for the current Final15.
- The current Final15 contains a mix of breast-cancer drugs, indication-expansion therapies, non-breast therapies, and Tier4 compounds, so downstream review should interpret efficacy and developability separately.
- Tier4 compounds remain useful as discovery signals, but they should be handled more cautiously than approved therapies in experimental planning and narrative reporting.
