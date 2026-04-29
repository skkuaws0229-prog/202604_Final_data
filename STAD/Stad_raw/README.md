# STAD raw 데이터 (Stad_raw)

GitHub 용량·파일 크기 제한 때문에 **바이너리 원본은 이 저장소에 포함하지 않습니다.**  
전체 미러(~28.5 GB, 820개 객체)는 팀 S3에 있습니다.

## 동기화 (복사만, 원본 수정/삭제 없음)

로컬에 전체 `Stad_raw`를 받으려면:

```bash
aws s3 sync "s3://say2-4team/Stad_raw/" "./Stad_raw/"
```

Final_data 번들에 넣은 복사본(동일 내용)은 다음에서도 받을 수 있습니다:

```bash
aws s3 sync "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/Stad_raw/" "./Stad_raw/"
```

## 이 폴더에 있는 메타데이터

- `top_level_directories.txt` — 미러 기준 최상위 디렉터리 목록
- `file_count.txt` — 파일 개수
- `total_size_local_mirror.txt` — 로컬 미러 기준 총 용량

재현 절차·데이터 정의는 `../workspace_git_snapshot/STAD_reproduction_protocol.md` 및 `../workspace_git_snapshot/configs/CONTEXT.md`를 참고하세요.
