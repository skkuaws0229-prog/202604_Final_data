# README_PRODUCTION — PDAC Final Data Bundle

이 폴더는 팀원이 S3/로컬에서 바로 PDAC 재현 실험을 시작할 수 있도록 구성된 production bundle입니다.

## 권장 루트
- `PDAC/`

## 포함 구성
- `PDAC_reproduction_protocol_20260428.md`
- `pdac_dashboard/app.py`
- `reports/`
- `results/20260427_pdac_step4_v1_no_holdout/`
- `external_validation/20260427_pdac_step4_v1_no_holdout/`
- `admet/20260427_pdac_step4_v1_no_holdout/`
- `scripts/`

## 원클릭 실행(로컬)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install pandas streamlit

cd PDAC
streamlit run pdac_dashboard/app.py
```

## 핵심 체크포인트
- Step6 Top30 외부근거: PRISM 24/30, ClinicalTrials 19/30, OpenTargets 13/30, COSMIC 2/30
- Step7 ADMET (22 assay): Top30 전행 평가 완료
- 최종 Top15 확정: 15개 (VT 포함)
