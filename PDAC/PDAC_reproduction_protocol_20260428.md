# PDAC 재현 프로토콜 (2026-04-28)

## 범위
- Step4 대표 앙상블 기반 Top30
- Step6 외부검증 (독립 어댑터)
- Step7 ADMET 22 assay 완전 계산형 + Top15 선별

## Step4
- RESULT_TAG: `20260427_pdac_step4_v1_no_holdout`
- Top30 산출물: `results/20260427_pdac_step4_v1_no_holdout/top30_pdac_with_vt.csv`
- VT 분포(Top30): VT1=4, VT2=9, VT3=16, VT4=1

## Step6 외부검증
- 요약 파일: `external_validation/20260427_pdac_step4_v1_no_holdout/external_validation_independent_summary.json`
- Top30 처리: 30
- PRISM evidence: 24
- ClinicalTrials support: 19
- OpenTargets support: 13
- COSMIC support: 2
- GEO/CPTAC: PENDING_DATA

## Step7 ADMET
- 요약 파일: `admet/20260427_pdac_step4_v1_no_holdout/admet_summary_independent.json`
- 후보 30개 전행 평가
- assay: 22
- resolved_smiles_count: 30
- 분류: Candidate=8, Caution=22

### Top15 선별 규칙
1. `admet_category` 우선 (Approved > Candidate > Caution > NO_SMILES)
2. `toxicity_flags` 개수 오름차순
3. `low_confidence_toxic_signals` 오름차순
4. `admet_coverage` 내림차순
5. 원래 rank 오름차순

### Top15 결과
- 파일: `results/20260427_pdac_step4_v1_no_holdout/step7_top15_pdac_admet_with_vt.csv`
- 분포: Candidate=8, Caution=7
- VT 분포: VT1=4, VT2=6, VT3=5
