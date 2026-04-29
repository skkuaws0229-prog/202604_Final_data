# STAD Step 3 row drop fix plan (analysis only)

## 1) Colon vs STAD filter script diff 결과

비교 대상:
- `20260420_new_pre_project_biso_Colon/scripts/filter_colon_cell_lines.py`
- `20260421_new_pre_project_biso_STAD/scripts/filter_stad_cell_lines.py`

핵심 관찰:
- 두 스크립트 모두 **동일한 2-stage normalize 로직**을 사용함.
  - `normalize_strict`: `- / _ : space` 제거 + lower
  - `normalize_fallback`: strict 이후 추가 특수문자 제거 + regex (`[^a-z0-9]`)
- 두 스크립트 모두 DepMap lookup key를 **`StrippedCellLineName` 기반**으로 구성함.
- 두 스크립트 모두 labels의 `sample_id`를 최종적으로 **DepMap `stripped_name`**으로 기록함.
- 두 스크립트 차이는 대부분 문서화/타이핑/로그/리포트 필드 축약이며, normalize 매칭 알고리즘 자체 차이는 확인되지 않음.

요청하신 관점 답변:
- Colon은 cell line normalize/mapping을 어떻게 하는가?  
  -> `StrippedCellLineName` 기준 2-stage normalize 매칭.
- StrippedCellLineName vs CellLineName 중 무엇 사용?  
  -> 매칭 key와 output `sample_id`는 `StrippedCellLineName` 사용 (`CellLineName`은 info 보조 필드).
- GDSC labels의 cell_line_name을 DepMap 이름으로 변환 단계가 있는가?  
  -> 있음. 매칭된 GDSC `CELL_LINE_NAME`를 DepMap `stripped_name`으로 변환해 labels `sample_id`로 저장.

## 2) STAD에서 누락된 normalize 로직 식별

Colon 대비 STAD `filter_stad_cell_lines.py`에서 **누락된 normalize 단계는 확인되지 않음**.

근거:
- STAD/Colon 모두 동일한 `normalize_strict` + `normalize_fallback` 적용.
- STAD/Colon 모두 labels `sample_id`를 DepMap stripped 기준으로 생성.

실제 row loss와 연결되는 지점(관찰):
- `reports/step3_sample_mismatch_diagnosis.json` 기준 STAD는 labels 24개 중 19개 unmatched, 이 중 다수가 형식 차이 후보(`HGC27 -> HGC-27`, `HS746T -> Hs 746T` 등).
- `reports/step3_row_drop_analysis.json` 기준 unmatched_drugs=0, unmatched_samples=2339/6060.
- 즉 손실은 drug side가 아니라 sample side에서 발생.

## 3) 해결 방안 3가지 장단점

### (alpha) `filter_stad_cell_lines.py`에 Colon과 동일 normalize 추가 후 Step2/Step3 재실행
- 장점
  - 근본 원인(샘플명 포맷 정합) 해결 경로.
  - Step2 산출물(`labels.parquet`) 자체를 개선하므로 downstream 전체 일관성 확보.
  - Colon 기준 운영 방식(전처리에서 sample_id 정합 확보)과 가장 맞음.
- 단점
  - Step2 + Step3 재실행 비용(시간/Batch 자원).
  - 재현 로그/산출물 버전 증가 관리 필요.

### (beta) `prepare_fe_inputs.py`(nextflow/scripts)에서 normalize 패치
- 장점
  - Step2 재실행 없이 Step3에서 즉시 완화 가능.
  - 빠른 임시 복구 경로.
- 단점
  - FE bridge 단계에서만 보정되어 원천 labels 정합 문제를 남김.
  - `prepare_fe_inputs.py`는 Colon/STAD에 사실상 동일 계약 스크립트로 운용 중이라, disease별 분기/패치 시 프로토콜 일관성 저하 위험.
  - 같은 입력이라도 stage별 표준 키 정의가 달라질 수 있어 추적 복잡도 증가.

### (gamma) 현재 3721 rows 그대로 진행
- 장점
  - 즉시 진행 가능, 추가 실행 비용 없음.
- 단점
  - 포맷 차이성 unmatched 샘플이 포함된 상태로 FE 진행되어 정보 손실 고착.
  - Colon(35/35 매칭)과 비교 시 프로토콜 일관성/비교 가능성 저하.
  - 이후 해석 단계에서 sample coverage 편향 리스크 유지.

## 4) 프로토콜 일관성 관점 권장안(판정 아님, 근거 정리)

근거 기반으로 보면, **(alpha) 경로가 프로토콜 일관성에 가장 부합**:
- 문제 위치가 sample join upstream(Step2 산출 sample_id 정합)으로 관찰됨.
- drug side mismatch가 0이므로, FE 단계 임시 보정보다 labels 생성 단계 정합 보장이 구조적으로 일관됨.
- Colon과의 비교 기준(전처리 단계에서 sample key 확정)과 맞춰 재현성 설명이 가장 명확함.

반대로 (beta)는 단기 복구에는 유리하지만, bridge 단계에서만 규칙을 추가해 disease 간 계약 차이를 만들 수 있어 표준 운영 관점에서 관리 부담이 큼.

