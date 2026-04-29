# Colon (CRC) — reproducibility bundle

이 디렉터리는 **대장암(`20260428_colon_v2`) 재현**을 위해 레포에 올린 문서·요약 산출물·스크립트이다.  
동일 내용의 **전체 로우 데이터 및 대용량 입력·중복 스테이징 폴더**는 Git 용량·GitHub 파일 크기 제한 때문에 **`say2-4team` S3**에 두었다.

## GitHub에 포함된 것

- 재현 프로토콜·S3 매니페스트·README (`20260428_colon_v2_reproduction_protocol.md`, `S3_REPRODUCTION_MANIFEST.md` 등)
- Step4–Step7 **요약 표·JSON·CSV**(모델 메트릭, 앙상블·티어, 게이트, Top30/Top15, ADMET 22 assay 요약 등)
- Step6 실행 스크립트 및 **소형 검증 결과 JSON**(`20260428_colon_v2_step6_run/scripts`, `.../results`)
- Step7 ADMET 산출(요약 JSON 및 Top30 스코어 CSV)
- 파이프라인 보고서(`reports/`)

## GitHub에서 제외한 것 (S3에서 받기)

다음은 용량·재현 경로 중복·민감 스냅샷 이유로 **이 레포에는 넣지 않았다.** 재현 시 S3 동기화 절차를 따른다.

| 제외 항목 | 비고 |
|-----------|------|
| `20260428_colon_v2_step6_synced_inputs/` | 입력 미러(용량 중복) |
| `20260428_colon_v2_step6_run/curated_data/` | GEO/CPTAC/PRISM/COSMIC/cBioPortal 등 **대용량 로우·중간 입력** |
| `20260428_colon_v2_step6_external_validation_raw_inputs/` | 외부 검증용 원시 입력 |
| `20260428_colon_v2_step6_external_validation_clinicaltrials_api_snapshot.json` | 대용량 API 스냅샷(레포 정책상 제외) |

**S3 프리픽스:** `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/`  

받는 방법은 패키지 안 `20260428_colon_v2/S3_REPRODUCTION_MANIFEST.md` 를 참고한다.

## 보안

커밋에 **자격 증명·API 키·개인 식별 정보**를 넣지 않았다. 로컬 `.env` 등은 레포에 포함하지 말 것.
