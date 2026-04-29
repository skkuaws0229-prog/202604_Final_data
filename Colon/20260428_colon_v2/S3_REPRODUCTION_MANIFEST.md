# Colon 재현 데이터 — S3 배치 (say2-4team)

**버킷 프리픽스**: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/`

다른 팀원은 아래를 로컬로 받아 `20260428_colon_v2_reproduction_protocol.md` 절차대로 재현하면 된다.

## 디렉터리 구조 (업로드 후)

| S3 키 프리픽스 | 내용 |
|----------------|------|
| `Colon/20260428_colon_v2/` | 대장암 v2 패키지 전체(Step4 산출, Step6 실행·로우 입력·결과, Step7 스크립트·ADMET 산출·재현 프로토콜·보고서) |
| `Colon/shared_inputs/curated_data/admet/` | TDC ADMET 22 assay 라이브러리 (`tdc_admet_group/admet_group/`) |
| `Colon/shared_inputs/20260421_new_pre_project_biso_STAD/data/step4_lihc_v2_manual/` | GDSC `drug_features.parquet` 등(Step7 SMILES 조인용) |
| `Colon/shared_inputs/20260420_new_pre_project_biso_Colon/scripts/` | 초이 `step7_1_admet_filtering.py`(Colon v2 Step7-1 래퍼가 로드) |

## 로컬로 받기 (저장소 루트 = `.../20260415_preproject_choi_protocol_v1_bisotest-1` 가정)

`Step7-1` 래퍼는 루트 아래 `20260415_preproject_choi_protocol_v1_bisotest/20260420_new_pre_project_biso_Colon/scripts/step7_1_admet_filtering.py` 를 찾는다.  
그래서 **`shared_inputs/` 내용을 중첩 패키지 폴더로 그대로 합쳐 받는다.**

```bash
export COLON_S3="s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon"
# 워크스페이스 루트에서 실행
aws s3 sync "${COLON_S3}/20260428_colon_v2/" ./20260428_colon_v2/
aws s3 sync "${COLON_S3}/shared_inputs/" ./20260415_preproject_choi_protocol_v1_bisotest/
```

## Step7 환경변수 (`20260428_colon_v2/scripts/20260428_colon_v2_step7_run.sh` 와 동일 구조)

```bash
export COLON_DRUG_FEATURES="$(pwd)/20260415_preproject_choi_protocol_v1_bisotest/20260421_new_pre_project_biso_STAD/data/step4_lihc_v2_manual/drug_features.parquet"
export COLON_TDC_ADMET="$(pwd)/20260415_preproject_choi_protocol_v1_bisotest/curated_data/admet"
bash 20260428_colon_v2/scripts/20260428_colon_v2_step7_run.sh
```

---

업로드는 원본 로컬 디렉터리를 **수정·삭제하지 않고** `aws s3 sync`/`cp` 로 복사한 것이다 (로컬→S3).
