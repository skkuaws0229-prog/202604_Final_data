# BRCA 재현 프로토콜

- 날짜: 2026-04-28
- 버전: v1
- 범위: 현재 BRCA 재실행을 Step4 요약부터 Step7 ADMET까지 재현

## 표준 범위

- Step5 앙상블: 지시문 기반 A/B 비교, 승자 = `A`
- Step6 외부 검증: `METABRIC Method A/B/C`
- Step6 보조 해석: `ClinicalTrials.gov + 수동 검토`
- Step7 안전성 게이트: `ADMET 22 assay`, `TDC 벤치마크`, `Tanimoto 유사도 v1`

## 핵심 입력

- Step4 요약: `brca_model_performance_summary.csv`
- Step5 Top30: `brca_directive_top30_unique_candidates.csv`
- Step5 Tier 맵: `brca_directive_top30_tiered_candidates.csv`
- Step6 METABRIC 발현 데이터:
  `20260415_preproject_protocol_choi/data/metabric/metabric_expression_basic_clean_20260406.parquet`
- Step6 METABRIC 임상 데이터:
  `20260415_preproject_protocol_choi/data/metabric/metabric_clinical_patient_basic_clean_20260406.parquet`
- Step7 ADMET assay 디렉터리:
  `20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/curated_data/admet/tdc_admet_group/admet_group`

## 고정 의사결정

- 앙상블 승자: `A`
- GroupCV Spearman: `0.4834`
- ScaffoldCV Spearman: `0.3644`
- Step6 입력: 과거 consensus top24가 아닌, 현재 BRCA Top30
- Step7 입력: 현재 Top30의 약물 30개 전부
- 최종 후보 컷: Step7 랭킹 이후 Top 15

## 재현 순서

1. Step4 요약 갱신
   - 명령어: `python3 scripts/extract_brca_step4_summary.py`
   - 산출물: `brca_model_performance_summary.csv`, `brca_model_performance_detailed.csv`

2. Step5 앙상블 재실행
   - 명령어: `python3 scripts/run_brca_directive_ensemble.py`
   - 산출물: `brca_directive_ensemble_validation_summary.csv`, `brca_directive_top30_unique_candidates.csv`

3. Tier 분류
   - 명령어: `python3 scripts/classify_brca_top30_tiers.py`
   - 산출물: `brca_directive_top30_tiered_candidates.csv`

4. Step6 METABRIC 재실행
   - 명령어: `python3 scripts/run_brca_step6_metabric_adapter.py`
   - 산출 디렉터리: `step6_metabric_validation/`

5. Step7 ADMET 재실행
   - 명령어: `python3 scripts/run_brca_step7_admet_adapter.py`
   - 산출 디렉터리: `step7_admet_22assay/`

6. 자료 갱신
   - 명령어: `python3 scripts/build_brca_repro_materials.py`

7. 대시보드
   - 명령어: `streamlit run 20260428_new_BRCA_data/brca_repro_dashboard.py`

## Tier 정의

- Tier 1: 유방암 치료제
- Tier 2: 유방암 적응증 확장 연구 치료제
- Tier 3: 유방암 비사용 치료제
- Tier 4: 화합물 또는 미지 약물

## Step6 수용 기준 뷰

- 현재 타깃 발현 약물: `11/30`
- 현재 BRCA 경로 연관 약물: `12/30`
- 현재 생존 유의 약물: `2/30`

## Step7 수용 기준 뷰

- PASS: `6`
- WARNING: `21`
- FAIL: `3`
- Hard fail: `2`

## 해석 가이드

- Step6 METABRIC은 기전적 타당성을 해석하는 생물학적 검증 레이어입니다.
- Step7 ADMET 22 assay는 현재 Final15를 산출하는 실무적 랭킹 레이어입니다.
- 현재 Final15는 유방암 치료제, 적응증 확장 치료제, 비유방암 치료제, Tier4 화합물이 혼합된 숏리스트로 해석해야 합니다.
- Positive control, 재창출 후보, 탐색 전용 화합물은 하나의 동질적 목록이 아니라 서로 다른 후속 액션 클래스로 구분해 해석해야 합니다.
- Tier4 신호도 가치가 있을 수 있으나, 승인 치료제보다 보수적으로 논의해야 합니다.

## 대시보드 뷰

- Overview 탭: 최종 상태, Step7 카운트, Final15 스냅샷
- Step5 탭: A/B 검증 결과, Top30 Tier 분류 후보 테이블
- Step6 탭: METABRIC A/B/C 지표 및 검증 점수 뷰
- Step7 탭: ADMET 판정 분포, Final15 Tier 분포, 전체 assay 테이블

## 참고사항

- 이번 재실행은 Step6와 Step7을 의도적으로 분리합니다.
- Step6는 Step7 입력 Top30을 게이팅하지 않으며, 현재 약물 30개 전부가 ADMET으로 들어갑니다.
- 현재 Step7 판정 요약: PASS `6`, WARNING `21`, FAIL `3`
