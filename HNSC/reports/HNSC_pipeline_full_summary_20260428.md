# HNSC 파이프라인 종합 결과 보고서 (2026-04-28)

기준 태그: `20260427_hnsc_step4_v1`

## 1) FE 기반 모델학습 및 대표 앙상블

학습 기반: Step0~3 채택 + FE 이후 Step4 실행 체인

모델학습 결과표(전체):


| 구분         | 기준/파일                                                               | 결과                      |
| ---------- | ------------------------------------------------------------------- | ----------------------- |
| 실행 체인      | Step4 (ML/DL/Graph)                                                 | 완료(대표 앙상블 Top30 산출로 확인) |
| 결과 태그      | `results/20260427_hnsc_step4_v1/`                                   | 사용                      |
| 모델 게이트 상세표 | `results/20260427_hnsc_step4_v1/step5_gate_eval_spearman_table.csv` | 현 브랜치 미보유 (N/A)         |
| 대표 앙상블 입력군 | ML + DL + Graph                                                     | 사용                      |


대표 앙상블 결과표:


| 항목       | 값                               |
| -------- | ------------------------------- |
| 대표 산출물   | `top30_tier1234_fixed_hnsc.csv` |
| Top30 행수 | 30                              |
| Tier1    | 3                               |
| Tier2    | 12                              |
| Tier3    | 10                              |
| Tier4    | 5                               |


## 2) 대표 앙상블 기반 Top30 리스트

파일: `results/20260427_hnsc_step4_v1/top30_tier1234_fixed_hnsc.csv`


| rank | drug_name        | tier  | definition_basis  |
| ---- | ---------------- | ----- | ----------------- |
| 1    | Dactinomycin     | Tier2 | 타암종 승인/적응증확장 연구축  |
| 2    | Docetaxel        | Tier1 | 두경부암 승인/표준치료 축    |
| 3    | Vinorelbine      | Tier2 | 타암종 승인/적응증확장 연구축  |
| 4    | Paclitaxel       | Tier1 | 두경부암 승인/표준치료 축    |
| 5    | Temsirolimus     | Tier2 | 타암종 승인/적응증확장 연구축  |
| 6    | Topotecan        | Tier2 | 타암종 승인/적응증확장 연구축  |
| 7    | Vinblastine      | Tier2 | 타암종 승인/적응증확장 연구축  |
| 8    | SN-38            | Tier2 | 타암종 승인/적응증확장 연구축  |
| 9    | Lestaurtinib     | Tier3 | 두경부암 미사용 치료제/신규탐색 |
| 10   | SL0101           | Tier3 | 두경부암 미사용 치료제/신규탐색 |
| 11   | Teniposide       | Tier2 | 타암종 승인/적응증확장 연구축  |
| 12   | Irinotecan       | Tier2 | 타암종 승인/적응증확장 연구축  |
| 13   | Camptothecin     | Tier4 | 화합물/검증추가필요        |
| 14   | Pyridostatin     | Tier4 | 화합물/검증추가필요        |
| 15   | Schweinfurthin A | Tier4 | 화합물/검증추가필요        |
| 16   | GSK1904529A      | Tier3 | 두경부암 미사용 치료제/신규탐색 |
| 17   | Staurosporine    | Tier4 | 화합물/검증추가필요        |
| 18   | Epirubicin       | Tier2 | 타암종 승인/적응증확장 연구축  |
| 19   | Tozasertib       | Tier3 | 두경부암 미사용 치료제/신규탐색 |
| 20   | Mitoxantrone     | Tier2 | 타암종 승인/적응증확장 연구축  |
| 21   | MG-132           | Tier4 | 화합물/검증추가필요        |
| 22   | Sabutoclax       | Tier3 | 두경부암 미사용 치료제/신규탐색 |
| 23   | AZD5582          | Tier3 | 두경부암 미사용 치료제/신규탐색 |
| 24   | Rapamycin        | Tier2 | 타암종 승인/적응증확장 연구축  |
| 25   | AZD2014          | Tier3 | 두경부암 미사용 치료제/신규탐색 |
| 26   | Refametinib      | Tier3 | 두경부암 미사용 치료제/신규탐색 |
| 27   | LMP744           | Tier3 | 두경부암 미사용 치료제/신규탐색 |
| 28   | ZM447439         | Tier3 | 두경부암 미사용 치료제/신규탐색 |
| 29   | Tanespimycin     | Tier2 | 타암종 승인/적응증확장 연구축  |
| 30   | Bleomycin        | Tier1 | 두경부암 승인/표준치료 축    |


## 3) Step6 외부검증 (방법 + 결과 리스트)

방법:

- 스크립트: `scripts/run_step6_hnsc.sh`
- 어댑터: `scripts/step6_ext_comprehensive_hnsc_independent.py`
- 입력: Top30
- 소스: PRISM / ClinicalTrials / Patient context(TCGA/CPTAC) / OpenTargets / COSMIC / GEO

결과 요약 (파일: `external_validation/20260427_hnsc_step4_v1/external_validation_independent_summary.json`):

- Top30 처리: 30
- 1개 이상 매칭: 28/30
- 미매칭: `Pyridostatin`, `Schweinfurthin A`
- PRISM(any): 21
- ClinicalTrials: 17
- Patient context: 14
- OpenTargets: 14
- COSMIC: 3
- GEO(drug-level): 0 (`DATASET_ONLY`)

## 4) Step7 ADMET/후보정제 (방법 + 최종 15 리스트)

방법:

- 스크립트: `scripts/run_step7_hnsc.sh`, `scripts/step7_finalize_hnsc.py`
- 정책: 외부근거 + Tier1/2/3/4 + REVIEW 분리

최종 파일:

- `results/20260427_hnsc_step4_v1/step7_top15_hnsc_provisional_with_fixed_tier.csv`

요약:

- Top15: 15개
- KEEP_TOP15: 12
- REVIEW: 3
- REVIEW 항목: `Camptothecin`, `Pyridostatin`, `Schweinfurthin A`

Top15 리스트:


| rank | drug_name        | step6_external_match | validation_evidence_tier | step7_decision | fixed_tier |
| ---- | ---------------- | -------------------- | ------------------------ | -------------- | ---------- |
| 1    | Dactinomycin     | matched              | VT2                      | KEEP_TOP15     | Tier2      |
| 2    | Docetaxel        | matched              | VT1                      | KEEP_TOP15     | Tier1      |
| 3    | Vinorelbine      | matched              | VT2                      | KEEP_TOP15     | Tier2      |
| 4    | Paclitaxel       | matched              | VT1                      | KEEP_TOP15     | Tier1      |
| 5    | Temsirolimus     | matched              | VT2                      | KEEP_TOP15     | Tier2      |
| 6    | Topotecan        | matched              | VT2                      | KEEP_TOP15     | Tier2      |
| 7    | Vinblastine      | matched              | VT2                      | KEEP_TOP15     | Tier2      |
| 8    | SN-38            | matched              | VT2                      | KEEP_TOP15     | Tier2      |
| 9    | Lestaurtinib     | matched              | VT3                      | KEEP_TOP15     | Tier3      |
| 10   | SL0101           | matched              | VT3                      | KEEP_TOP15     | Tier3      |
| 11   | Teniposide       | matched              | VT2                      | KEEP_TOP15     | Tier2      |
| 12   | Irinotecan       | matched              | VT2                      | KEEP_TOP15     | Tier2      |
| 13   | Camptothecin     | matched              | VT4                      | REVIEW         | Tier4      |
| 14   | Pyridostatin     | unmatched            | VT4                      | REVIEW         | Tier4      |
| 15   | Schweinfurthin A | unmatched            | VT4                      | REVIEW         | Tier4      |
