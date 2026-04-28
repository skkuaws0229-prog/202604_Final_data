# PDAC Reproduce Quick Guide

## 1) 대시보드 확인
```bash
cd PDAC
streamlit run pdac_dashboard/app.py
```

## 2) 결과 파일 핵심 경로
- Top30: `results/20260427_pdac_step4_v1_no_holdout/top30_pdac_with_vt.csv`
- Step6 요약: `external_validation/20260427_pdac_step4_v1_no_holdout/external_validation_independent_summary.json`
- Step7 요약: `admet/20260427_pdac_step4_v1_no_holdout/admet_summary_independent.json`
- Step7 Top15: `results/20260427_pdac_step4_v1_no_holdout/step7_top15_pdac_admet_with_vt.csv`

## 3) 보고서
- `reports/PDAC_pipeline_full_summary_20260428.md`
