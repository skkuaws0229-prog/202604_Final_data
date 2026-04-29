# LUNG Final data bundle

이 폴더는 `LUNG/LUAD` drug repurposing 파이프라인의 공개 가능한 재현 패키지입니다.

## 구성

| 하위 경로 | 설명 |
|-----------|------|
| `COPY_MANIFEST.txt` | GitHub 공개 패키지 구성 원칙과 S3 기준 경로 |
| `workspace_git_snapshot/` | 재현 문서, 경량 결과, 실행 스크립트, S3 인벤토리 매니페스트 |
| `raw_source_snapshot/` | Step0 원천 데이터의 GitHub용 안내 문서만 포함 |
| `pipeline_s3_work/` | 현재 팀 S3 작업 경로 안내 문서만 포함 |

## 포함된 것

- Step5~Step7 재현 프로토콜과 실행 보고서
- 최종 `Top30`, `Tier1~4`, 외부검증, ADMET, `Top15` 결과
- Step0 raw bootstrap, Step5~Step7 bootstrap, S3 sync 스크립트
- 현재 S3 경로와 데이터 인벤토리 텍스트 매니페스트

## GitHub에서 제외한 것

- Step0 raw 바이너리 전체
- `project_root/curated_data`, `project_root/data`, `project_root/fe_qc`의 대용량 데이터셋 원본
- 대용량 중간 산출물과 바이너리 배열 (`.npy`, `.parquet`)
- 비밀 저장소 경로가 찍힌 `.nextflow.log`류 로그

위 항목들은 보안과 용량 제한 때문에 GitHub에 직접 넣지 않았고, 현재 기준 S3 canonical 경로에서 복원하도록 구성했습니다.

## Canonical S3

`s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/`

핵심 하위 경로:

- `project_root/`
- `raw_source_snapshot/Lung_raw/`
- `supporting_inputs/`
- `workspace_docs/`
- `workspace_reports/`
- `workspace_scripts/`

## 빠른 재현

1. Step0 raw 복원:
   - `workspace_git_snapshot/scripts/bootstrap_lung_step0_raw_from_s3.sh`
2. Step5~Step7 현재 패키지 복원:
   - `workspace_git_snapshot/scripts/bootstrap_lung_repro_from_s3.sh`
3. 전체 순서:
   - `workspace_git_snapshot/reports/lung_reproducibility/LUNG_reproduction_protocol_20260429_v1.md`
