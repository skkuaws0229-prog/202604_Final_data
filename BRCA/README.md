# BRCA — reproducibility bundle

이 디렉터리는 **유방암(BRCA) 프로토콜 재현 실험(`20260428_new_BRCA_data`)** 결과를 레포에 올린 문서·요약 산출물·예측·검증 표이다.  
동일 파이프라인의 **전체 로우 입력·대용량 의존 디렉터리·전체 multicancer 결과 트리**는 용량 및 경로 중복 때문에 **`say2-4team` S3**에도 함께 적재되어 있다.

## GitHub에 포함된 것 (`20260428_new_BRCA_data/`)

- directive 기반 앙상블(A/B) 검증 요약·예측 CSV/Parquet, Top30 dedup·티어 분류 (`brca_directive_*`, `brca_current_status_20260428.md` 등)
- Step 6 METABRIC 외부 검증 산출물 (`step6_metabric_validation/`)
- Step 7 ADMET 22 assay(Tanimoto) 산출물 및 최종 15 후보 (`step7_admet_22assay/`, `brca_final15_after_admet.csv`)
- 재현 범위 문서 (`brca_step6_step7_execution_scope_20260428.md` 등)
- 대시보드 스크립트 (`brca_repro_dashboard.py`)

## S3에 적재된 것 (전체 재현 번들)

아래 프리픽스 아래에 **BRCA 재현에 사용된 산출물과 의존 데이터 루트**가 워크스페이스 상대 경로 구조를 유지한 채 업로드되어 있다.

**S3 프리픽스:** `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/`

포함 루트·파일 수·바이트·하위 경로는 다음 매니페스트를 따른다.

- `20260428_new_BRCA_data/BRCA_s3_upload_manifest_20260428.md`
- `20260428_new_BRCA_data/BRCA_s3_upload_manifest_20260428.json`

매니페스트 요약: `20260428_new_BRCA_data` 산출물, 재현용 `scripts`, 모델 입력(`20260415_preproject_protocol_choi/data`), multicancer Step4–5 참조용 `results/20260424_multicancer_stad_protocol_rerun`, Step7용 ADMET TDC 레퍼런스(`curated_data/admet/tdc_admet_group/admet_group`) 등이 S3에 포함된다.

GitHub에는 **요약·표·중소형 파일 중심**만 두었고, **전체 동기화·대용량 재현**은 S3 매니페스트를 참고해 받는 것을 권장한다.

## 보안

커밋에 **자격 증명·API 키·개인 식별 정보**를 넣지 않았다. 로컬 `.env` 등은 레포에 포함하지 말 것.
