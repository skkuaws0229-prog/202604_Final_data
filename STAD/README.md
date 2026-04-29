# STAD (위암 / TCGA-STAD) Final data bundle

이 폴더는 drug repurposing STAD 파이프라인 **재현에 필요한 산출·코드 스냅샷**과, **S3에 보관된 대용량 원본**을 가리키는 메타데이터로 구성됩니다.

| 하위 경로 | 설명 |
|-----------|------|
| `COPY_MANIFEST.txt` | S3 복사 출처·요약 |
| `workspace_git_snapshot/` | `results`, `fe_qc`, `configs`, `reports`, `scripts`, `stad_dashboard`, 프로토콜 문서 등 (레포 스냅샷) |
| `pipeline_s3_work/` | 팀 S3 작업 접두사 `20260421_new_pre_project_biso_STAD`에서 복사한 `data`, `fe_output`, `work` |
| `Stad_raw/` | **원본 바이너리는 미포함.** `README.md` 및 경로/용량 메타데이터만 포함. 전체는 S3에서 `aws s3 sync`로 수신 |

원본 `Stad_raw`는 GitHub 단일 파일·저장소 제한으로 인해 이 저장소에 포함되지 않습니다. 반드시 S3에서 받아 사용하세요.
