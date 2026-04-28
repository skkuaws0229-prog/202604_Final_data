# README_PRODUCTION — HNSC Final Data Bundle

이 폴더는 팀원이 **S3만으로 HNSC 재현실험**을 시작할 수 있도록 구성된 production bundle입니다.

## S3 루트
- `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/`

## 폴더 구조
- `HNSC_reproduction_protocol.md` : 단계별 실행 프로토콜
- `README_REPRODUCE.md` : 재현 개요
- `raw/HNSC_raw/` : 팀 raw 원천(복사본)
- `base_data/20260421_hnsc/` : FE 시작 포함 베이스 데이터/산출물
- `workspace_seed/` : 작업 S3 seed/validation 스냅샷
- `external_validation/` : Step6 입력·참조·결과
- `results/20260427_hnsc_step4_v1/` : Top30/Top15 결과
- `reports/` : 종합 보고서
- `scripts/` : Step7 등 실행 스크립트
- `hnsc_dashboard/` : Streamlit 대시보드

## 원클릭 실행 (권장)
```bash
# 0) 환경 준비
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install pandas pyarrow streamlit

# 1) 번들 동기화
aws s3 sync \
  s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/ \
  ./HNSC

# 2) 작업 폴더 이동
cd HNSC

# 3) (선택) 실행 권한
chmod +x scripts/*.sh

# 4) Step7 재현 실행 (원클릭)
./scripts/run_step7_hnsc.sh

# 5) 결과 확인
ls -lh results/20260427_hnsc_step4_v1/
head -n 20 results/20260427_hnsc_step4_v1/step7_top15_hnsc_provisional_with_fixed_tier.csv

# 6) 대시보드 실행
streamlit run hnsc_dashboard/app.py
```

## Step6 포함 재현 (순차 실행)
```bash
cd HNSC

# Step6 외부검증
./scripts/run_step6_hnsc.sh

# Step7 최종화
./scripts/run_step7_hnsc.sh
```

## S3에서 직접 원격 실행(EC2/서버)
```bash
WORK=/data/hnsc_final
mkdir -p "${WORK}" && cd "${WORK}"

aws s3 sync \
  s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/ \
  ./HNSC

cd HNSC
./scripts/run_step7_hnsc.sh
```

## 핵심 체크포인트
- Step6 외부근거 any-match: `28/30`
- Step7 Top15: `15` (REVIEW `3`)
- Top30 Tier 분포: Tier1=3, Tier2=12, Tier3=10, Tier4=5

## 데이터 출처(복사 기준)
- Raw: `s3://say2-4team/HNSC_raw/`
- Baseline: `s3://say2-4team/20260409_eseo/20260421_hnsc/`
- Workspace seed: `s3://say2-4team/20260408_new_pre_project_biso/20260427_new_pre_project_biso_HNSC/`
