# Raw Source Snapshot

이 디렉토리에는 실제 raw 바이너리를 넣지 않았습니다.

실제 Step0 원천 데이터는 아래 S3 경로에 미러링되어 있습니다.

`s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/raw_source_snapshot/Lung_raw/`

확인된 주요 상위 폴더:

- `CPTAC/`
- `GDSC/`
- `LInc1000(세포주)/`
- `LInc1000/`
- `TCGA/`
- `additional_sources/`
- `admet/`
- `chembl/`
- `cptac/`
- `depmap/`
- `drugbank/`
- `feature_tables/`
- `gdsc/`
- `geo/`
- `gtex/`
- `lincs/`

GitHub에는 설명만 남기고, 실제 복원은 `workspace_git_snapshot/scripts/bootstrap_lung_step0_raw_from_s3.sh`를 사용합니다.
