# BRCA Current Status

- Status date: 2026-04-28
- Ensemble directive applied: `BRCA_ensemble_directive.md`
- Current ensemble winner: **A안**
- Current tier classification status: **redefined by breast-cancer treatment / breast-trial / non-breast-therapy / compound criteria**

## Ensemble Validation

| Config | Eval Mode | Spearman | RMSE | Mean Component Std |
| --- | --- | ---: | ---: | ---: |
| A | groupcv | 0.4834 | 2.2362 | 0.5863 |
| B | groupcv | 0.4826 | 2.2310 | 0.4632 |
| A | holdout | 0.7847 | 1.4343 | 0.5433 |
| B | holdout | 0.7878 | 1.4259 | 0.4433 |
| A | scaffoldcv | 0.3644 | 2.6779 | 0.6769 |
| B | scaffoldcv | 0.3622 | 2.6321 | 0.5988 |

## Tier Count

| Tier | Name | Count |
| --- | --- | ---: |
| 1 | 유방암 치료제 | 2 |
| 2 | 유방암 적응증 확장 연구 치료제 | 5 |
| 3 | 유방암 비사용 치료제 | 4 |
| 4 | 화합물 또는 미지 약물 | 19 |

## Tier 1

- Definition: 유방암 치료제
- Validation goal: 유방암 치료 맥락의 positive control 확인

| Rank | Drug | Score | Confidence | Note |
| --- | --- | ---: | --- | --- |
| 11 | 5-Fluorouracil | 5.1282 | C | NCI breast cancer approved drug list에 포함되는 유방암 치료제 |
| 22 | Cyclophosphamide | 4.8824 | A | NCI breast cancer approved drug list 및 AC/FEC/CMF 조합에 포함되는 유방암 치료제 |

## Tier 2

- Definition: 유방암 적응증 확장 연구 치료제
- Validation goal: 유방암 임상연구/적응증 확장 가능성 확인

| Rank | Drug | Score | Confidence | Note |
| --- | --- | ---: | --- | --- |
| 5 | Temozolomide | 6.2014 | B | 타 적응증 치료제이며 TNBC/전이성 유방암 임상연구 기록이 확인됨 |
| 9 | Oxaliplatin | 5.3569 | A | 타 적응증 승인 치료제이며 재발/전이성 유방암 임상연구 기록이 확인됨 |
| 16 | Ruxolitinib | 5.0745 | A | 타 적응증 승인 치료제이며 유방암/전암성 유방병변 임상연구 기록이 확인됨 |
| 19 | Veliparib | 4.9340 | C | 유방암 특히 BRCA 연관/삼중음성 유방암에서 다수 임상연구가 확인된 치료 후보 |
| 23 | Motesanib | 4.8782 | C | 유방암 병용요법 임상연구가 확인된 개발 치료 후보 |

## Tier 3

- Definition: 유방암 비사용 치료제
- Validation goal: 타 적응증 치료제의 신규 repurposing 탐색

| Rank | Drug | Score | Confidence | Note |
| --- | --- | ---: | --- | --- |
| 6 | Dacarbazine | 5.6518 | C | 승인 치료제이지만 현재 기준 유방암 직접 치료/확장 임상 근거는 뚜렷하지 않음 |
| 10 | Fludarabine | 5.1769 | C | 승인 치료제이지만 유방암 직접 치료제보다 혈액암/전처치 맥락이 중심 |
| 18 | Nelarabine | 4.9393 | A | 승인 치료제이지만 적응증은 T-ALL/T-LBL로 유방암 사용 근거가 뚜렷하지 않음 |
| 26 | Lenalidomide | 4.8358 | B | 승인 치료제이지만 현재 확인된 주 적응증은 혈액암 계열로 유방암 직접 사용 근거가 제한적 |

## Tier 4

- Definition: 화합물 또는 미지 약물
- Validation goal: 비승인 화합물/보충제/실험용 물질 분리

| Rank | Drug | Score | Confidence | Note |
| --- | --- | ---: | --- | --- |
| 1 | ascorbate (vitamin C) | 8.5058 | C | 보충제 성격의 비항암 물질로, 치료제군과 분리 필요 |
| 2 | N-acetyl cysteine | 7.8483 | C | 보충제/항산화 물질로, 치료제보다는 artifact 후보 성격이 큼 |
| 3 | glutathione | 7.4384 | A | 내인성 항산화 물질로 치료제보다는 대사성 보조물질 성격이 강함 |
| 4 | alpha-lipoic acid | 6.3771 | B | 보충제 성격이 강한 물질로 유방암 치료제 tier와 분리 |
| 7 | CZC24832 | 5.5331 | C | 승인 치료제가 아닌 연구용 저분자 화합물 |
| 8 | BEN | 5.4729 | C | 현재 명칭만으로 승인 치료제로 확인되지 않는 실험성/미지 후보 |
| 12 | CCT007093 | 5.1142 | B | 승인 치료제가 아닌 연구용 저분자 화합물 |
| 13 | A-366 | 5.0932 | A | 승인 치료제가 아닌 연구용 저분자 화합물 |
| 14 | THR-101 | 5.0845 | B | 승인 치료제로 정착되지 않은 개발/실험 단계 후보 |
| 15 | GSK2830371 | 5.0761 | B | 승인 치료제가 아닌 연구용 저분자 화합물 |
| 17 | SB216763 | 5.0167 | A | 승인 치료제가 아닌 연구용 저분자 화합물 |
| 20 | MIRA-1 | 4.9204 | B | 승인 치료제가 아닌 연구용 저분자 화합물 |
| 21 | PRIMA-1MET | 4.8964 | A | 개발 코드명 기반 후보로 승인 치료제군과 분리 |
| 24 | PCI-34051 | 4.8604 | A | 승인 치료제가 아닌 연구용 저분자 화합물 |
| 25 | AZD1208 | 4.8469 | B | 개발 코드명 기반 후보로 승인 치료제군과 분리 |
| 27 | JNK Inhibitor VIII | 4.8152 | B | 연구용 inhibitor 명칭으로 임상 치료제군과 분리 |
| 28 | ML323 | 4.8135 | A | 승인 치료제가 아닌 연구용 저분자 화합물 |
| 29 | GSK2801 | 4.7891 | B | 승인 치료제가 아닌 연구용 저분자 화합물 |
| 30 | LY2109761 | 4.7446 | C | 개발 코드명 기반 후보로 승인 치료제군과 분리 |

## Classification Notes

- Tier 1: 실제 유방암 치료제로 사용되거나 NCI breast cancer approved list에 포함된 약물
- Tier 2: 유방암 임상연구 또는 적응증 확장 시도가 확인된 치료제/치료 후보
- Tier 3: 치료제이지만 현재 기준 유방암 직접 사용 근거가 제한적인 약물
- Tier 4: 승인 치료제로 보기 어려운 화합물, 보충제, 실험용 inhibitor, 또는 미지 후보
