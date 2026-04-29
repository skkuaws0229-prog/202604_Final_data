# Colon depmap workflow analysis (read-only)

## 1) depmap 관련 스크립트 추적 (Colon)

`depmap|CRISPR|crispr_long` 키워드로 확인된 Colon 스크립트:
- `20260420_new_pre_project_biso_Colon/nextflow/scripts/convert_depmap_wide_to_long.py`
- `20260420_new_pre_project_biso_Colon/scripts/filter_colon_cell_lines.py`
- `20260420_new_pre_project_biso_Colon/nextflow/scripts/prepare_fe_inputs.py`
- `20260420_new_pre_project_biso_Colon/scripts/step2_qc.py`
- `20260420_new_pre_project_biso_Colon/scripts/convert_raw_to_parquet.py`
- `20260420_new_pre_project_biso_Colon/scripts/parallel_download_colon.sh`
- `20260420_new_pre_project_biso_Colon/scripts/upload_to_s3.sh`

`depmap_crispr_long_colon.parquet` 생성/사용 핵심:
- 생성 스크립트: `nextflow/scripts/convert_depmap_wide_to_long.py`
  - `ModelID -> CellLineName` 매핑 후 long 변환
  - 출력: `long[["cell_line_name", "gene_name", "dependency"]]`
  - 코드상 별도 Colon 35-cell 필터 없음
- 라벨 스크립트: `scripts/filter_colon_cell_lines.py`
  - 입력으로 `--depmap-long depmap_crispr_long_colon.parquet` 사용
  - `has_crispr` 체크/매칭에 사용되지만 depmap_long 파일 자체를 35로 재저장하지는 않음
- FE 브리지: `nextflow/scripts/prepare_fe_inputs.py`
  - `sample_features`는 `sample_src`의 `cell_line_name` 전체를 pivot하여 사용
  - 즉 depmap_long이 1150이면 FE sample_features도 1150, depmap_long이 35면 35

## 2) Colon depmap_long이 35로 맞춰진 시점/방식

확인 결과:
- `convert_depmap_wide_to_long.py` 자체는 full depmap long(1150 cells) 생성 로직.
- 문서 근거:
  - `20260420_new_pre_project_biso_Colon/differences.md`
    - 초기 Step 2-3 결과: `depmap_crispr_long_colon.parquet`가 20.4M rows (full)
    - 이슈 기록: FE v1에서 전 암종 혼입, 원인이 depmap_long full(1150)
    - 해결 기록: `labels.parquet`, `GDSC2-dataset.parquet`, `depmap`를 Colon 35 cells로 재필터링
  - `20260420_new_pre_project_biso_Colon/20260420_colon_protocol.md`
    - 동일하게 “labels 35 cells 기준 재필터링 후 재업로드” 명시

정리:
- Colon 35-cell depmap_long은 **convert 스크립트 기본 출력이 아니라, 이후 재필터링된 데이터 산출물**로 확인됨.
- 리포지토리 내에서 그 재필터링을 수행한 별도 자동화 스크립트는 현재 확인되지 않음.
- 따라서 분류하면:
  - Option A (convert 단계 pre-filter): 아님
  - Option B (별도 filter 스크립트 상시화): 코드로는 미확인
  - Option C (후속 수동/일회성 재정리): 문서 근거상 해당

STAD 대비:
- STAD `run_step2_stad.sh`는 `convert_depmap_wide_to_long.py` 출력을 그대로 `data/depmap/depmap_crispr_long_stad.parquet`로 복사
- 후속 depmap 24/35-cell 제한 단계 없음

## 3) Colon labels cell ↔ depmap cell 매칭 관리 방식

확인된 관리 포인트:
- `filter_colon_cell_lines.py`
  - GDSC COREAD 46 cells를 DepMap Model(`StrippedCellLineName`) 기준 2-stage normalize(strict/fallback)로 매칭
  - `reports/step2_4_matching_report.json`에서 `total_matched=46`, `unmatched=0`
  - 매칭 상세는 `reports/matched_colon_cell_lines.csv`에 저장
- FE 단계(`prepare_fe_inputs.py`)
  - join은 exact string key (`labels.sample_id` vs `sample_features.sample_id`)
  - local 산출물 기준 실제 결과:
    - Colon: depmap unique 35 / labels unique 35 / intersection 35
    - STAD: depmap unique 1150 / labels unique 24 / intersection 5

해석 가능한 사실만 요약:
- Colon의 FE 100% sample join은 `data/depmap/depmap_crispr_long_colon.parquet`가 이미 labels 키와 동일 35-cell 집합으로 맞춰져 있기 때문에 가능.
- STAD는 같은 FE 로직이라도 depmap_long이 full(1150) 상태이고 label key 포맷/집합과 불일치가 남아 join rate가 낮아짐.

