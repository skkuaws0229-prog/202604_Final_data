# 20260428_colon_v2 재현 프로토콜

대장암(CRC) 파이프라인: Step4·5 앙상블·티어 → Step6 외부검증 → **Step7 초이 22 assay ADMET + CRC 임상 Tier1–4 + Top15**.

문서 갱신 기준: Step7 ADMET 22 assay 완료·Top15·요약 JSON 생성 시점.

---

## 0. 루트·태그

- **패키지 루트(이 문서 기준)**: 저장소의 `20260428_colon_v2/`
- **결과 태그**: 파일명에 `20260428_colon_v2` 접두(또는 동일 문자열 포함) 사용

### S3 재현 번들 (팀 공유)

동일 데이터가 업로드되어 있다:

`s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/`

디렉터리 설명·`aws s3 sync` 예시: **`S3_REPRODUCTION_MANIFEST.md`** 참고.

---

## 1. Step4–5 (모델·앙상블)

| 항목 | 경로(상대) |
|------|------------|
| 15모델·CV·스캐폴드 메트릭 | `20260428_colon_v2_step4_2abc_15models_5cv_groupcv_scaffoldcv_overfit_table.csv`, `20260428_colon_v2_step4_model_metrics_full_table.csv` |
| 메트릭 프리뷰 | `20260428_colon_v2_step4_2abc_15models_metrics_preview.md` |
| 앙상블 후보 점수 | `20260428_colon_v2_step5_ensemble_candidate_scoring_table.csv` |
| Step5–6 앙상블·티어링 요약 | `20260428_colon_v2_step5_step6_ensemble_execution_and_tiering_summary.json` |

---

## 2. Step6 (외부검증)

| 항목 | 경로(상대) |
|------|------------|
| Top30 + CRC Tier1–4 (앙상블) | `20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv` |
| 가중 앙상블 랭킹(전체) | `20260428_colon_v2_step6_all_drugs_weighted_ensemble_ranking.csv` |
| Step6 실행 스크립트·로그 | `20260428_colon_v2_step6_run/` |
| 대리 화합물 규칙 | `20260428_colon_v2_step6_external_validation_surrogate_compound_matching_protocol.md` |
| Readiness / 게이트 | `20260428_colon_v2_step6_readiness_gate_report.md`, `20260428_colon_v2_step6_execution_gate_decision_rerun_after_geo_clinicaltrials_fix.md` |

**Tier 정의(요약)**: `tier_20260428_colon_v2` — 1=대장암 승인, 2=타암종 승인·CRC 확장 연구, 3=대장암 미사용, 4=화합물·추가 확인.

---

## 3. Step7 — 초이 프로토콜 ADMET 22 assay (STAD/`step7_1`과 동일 스택)

### 3.1 공통 입력(워크스페이스 내 공유)

재현 시 아래가 존재해야 한다.

| 입력 | 상대 경로(저장소 루트 기준) |
|------|---------------------------|
| GDSC SMILES (`canonical_drug_id`) | `20260415_preproject_choi_protocol_v1_bisotest/20260421_new_pre_project_biso_STAD/data/step4_lihc_v2_manual/drug_features.parquet` |
| TDC ADMET 22 assay 라이브러리 | `20260415_preproject_choi_protocol_v1_bisotest/curated_data/admet/` (`tdc_admet_group/admet_group/` 하위) |

환경변수로 덮어쓸 수 있다: `COLON_DRUG_FEATURES`, `COLON_TDC_ADMET` (`20260428_colon_v2/scripts/20260428_colon_v2_step7_run.sh`).

### 3.2 Step7-1 스크립트

- `scripts/20260428_colon_v2_step7_1_admet_22assay_gate.py`  
- 내부적으로 `20260415_preproject_choi_protocol_v1_bisotest/20260420_new_pre_project_biso_Colon/scripts/step7_1_admet_filtering.py`(22 assay·Tanimoto·Safety score) 로직 로드.

### 3.3 Step7-1 산출물

| 파일 | 설명 |
|------|------|
| `admet/20260428_colon_v2_step7/20260428_colon_v2_step7_admet_22assay_choi_protocol_tanimoto_top30_scored.csv` | Top30 약물별 verdict, safety_score, `n_total_matches`, `admet_coverage` 등 |
| `admet/20260428_colon_v2_step7/20260428_colon_v2_step7_admet_22assay_choi_protocol_summary.json` | `assays_loaded: 22`, `match_details`(약물별 assay 매칭), 요약 통계 |

### 3.4 Step7-2 Top15 + CRC Tier

- 스크립트: `scripts/20260428_colon_v2_step7_select_top15_crc_clinical_tiers.py`
- ADMET CSV가 있으면 **PASS/WARNING** 후보만 두고, verdict → safety_score → admet_coverage → rank 순으로 정렬 후 15개 (컬럼 존재 시 toxicity 관련 정렬도 가능).
- CRC 임상 티어: Step6의 `tier_20260428_colon_v2`를 우선(`crc_clinical_tier`, 한글 라벨 부여). 시드: `config/20260428_colon_v2_step7_crc_clinical_tier_seed.json`.

### 3.5 Step7 최종 산출물(22 assay 적용본)

| 파일 | 설명 |
|------|------|
| `20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv` | **최종 추천 15종** + ADMET 열 + CRC Tier |
| `20260428_colon_v2_step7_summary_admet22assay_choi_protocol.json` | 실험 ID·입력·티어 개수 요약 |

(ADMET 없이 티어·랭크만 쓴 비교용: `..._no_admet_tier_sort_only.csv` / `..._summary_no_admet_tier_sort_only.json`)

---

## 4. 원클릭 재실행

패키지 루트에서:

```bash
bash scripts/20260428_colon_v2_step7_run.sh
```

Step7-1은 기본 공유 경로가 유효할 때 자동 실행된다.

---

## 5. 관련 보고서

- 통합 파이프라인 보고서: `reports/20260428_colon_v2_pipeline_report_step6_step7.md`
