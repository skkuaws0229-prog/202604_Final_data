# 20260428_colon_v2 파이프라인 보고서 — Step6 외부검증 · Step7 ADMET 22 assay

**목적**: 대장암 후보 약물에 대해 외부 근거(Step6)를 확보한 뒤, 초이 프로토콜 **22 assay ADMET**으로 안전성·매칭 프로파일을 계산하고, **CRC 임상 Tier 1–4**와 함께 **Top15**를 확정한다.

---

## 1. 요약

| 구간 | 상태 | 비고 |
|------|------|------|
| Step4–5 | 완료 | 앙상블·메트릭 표·스코어링 테이블 보존 |
| Step6 외부검증 | 완료 | PRISM, ClinicalTrials(CRC), COSMIC, CPTAC, GEO 등 |
| Step7 ADMET 22 assay | 완료 | STAD와 동일 `step7_1` + TDC `tdc_admet_group`, GDSC `drug_features.parquet` |
| Top15 + Tier1–4 | 완료 | ADMET 병합본 파일명에 `admet22assay_choi_protocol` 포함 |

---

## 2. Step6 (외부검증)

- **입력 코호트**: Top30 (`20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv`).
- **실행물**: `20260428_colon_v2_step6_run/` (스크립트·`results/`·curated clinicaltrials 등).
- **CRC 앙상블 티어**: 열 `tier_20260428_colon_v2` — 승인·적응증 확장·미사용·화합물 검토 구분.
- **대리 화합물**: 이름 불일치 시 동일 표적/MOA 규칙은  
  `20260428_colon_v2_step6_external_validation_surrogate_compound_matching_protocol.md` 참고.
- **게이트**: GEO·ClinicalTrials 보완 후 **Step7 진행 가능** 판정(`20260428_colon_v2_step6_execution_gate_decision_rerun_after_geo_clinicaltrials_fix.*`).

---

## 3. Step7 — ADMET 22 assay (초이 프로토콜)

- **방법**: Morgan fingerprint + Tanimoto 유사도(≥0.70 구간)·22개 TDC ADMET assay 라이브러리 매칭·Safety score·verdict(PASS/WARNING/FAIL).
- **실행 결과(Top30 기준, 요약 JSON)**  
  - `assays_loaded`: **22**  
  - **verdict**: PASS 5, WARNING 23, FAIL 2 (FAIL은 Top15 풀에서 제외)  
  - 평균 safety score·매칭 수 등: `admet/20260428_colon_v2_step7/20260428_colon_v2_step7_admet_22assay_choi_protocol_summary.json`
- **약물별 상세**: 동일 JSON의 `match_details`(assay별 similarity·값).

### 입력 데이터 출처(재현용)

- SMILES: 공유 `drug_features.parquet`(GDSC ID와 Top30 일치 확인됨).
- TDC: `curated_data/admet/tdc_admet_group/admet_group/`.

---

## 4. Step7 — Top15 선정 및 CRC Tier

- **선정**: ADMET 결과와 Top30 병합 후 **PASS/WARNING**만 사용, 프로토콜 순위로 **15개** 추출.
- **산출**:  
  `20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv`  
  `20260428_colon_v2_step7_summary_admet22assay_choi_protocol.json`
- **Top15 내 CRC Tier 분포(예시, 요약 JSON 기준)**  
  - Tier 1: 1  
  - Tier 2: 5  
  - Tier 3: 1  
  - Tier 4: 8  

(티어 값은 Step6 앙상블 열을 우선 반영하는 정책.)

---

## 5. 산출물 인덱스

| 유형 | 경로 |
|------|------|
| 재현 절차 전체 | `../20260428_colon_v2_reproduction_protocol.md` |
| Step7 ADMET 상세 JSON | `../admet/20260428_colon_v2_step7/20260428_colon_v2_step7_admet_22assay_choi_protocol_summary.json` |
| Step7 최종 Top15 CSV | `../20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv` |
| Step7 요약 JSON | `../20260428_colon_v2_step7_summary_admet22assay_choi_protocol.json` |

---

## 6. 제한·메모

- ADMET **미적용** 비교 실행 시 파일명에 `no_admet_tier_sort_only` 가 붙는 별도 결과가 생길 수 있다. 최종 권고는 **`admet22assay_choi_protocol`** 접미사 파일을 사용한다.
- 절대 경로가 JSON에 기록될 수 있으므로 공유 시 상대 경로로 치환하거나 동일 디렉터리 구조를 유지한다.
