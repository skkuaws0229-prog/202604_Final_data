# Pipeline S3 Work

이 디렉토리는 현재 팀 S3 작업 구조를 설명하기 위한 자리표시자입니다.

Canonical S3:

`s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/`

핵심 경로:

- `project_root/`
- `supporting_inputs/`
- `workspace_docs/`
- `workspace_reports/`
- `workspace_scripts/`

팀원은 GitHub 패키지 자체를 실행 입력으로 직접 쓰기보다, 위 S3 경로에서 bootstrap 스크립트로 로컬 작업 구조를 복원한 뒤 프로토콜을 따라 실행해야 합니다.
