# HNSC 재현 프로토콜 (프로젝트 시작용)

본 문서는 `STAD_reproduction_protocol.md` 구조를 기반으로, 암종을 **두경부암(HNSC)** 으로 전환해 프로젝트를 시작하기 위한 실행 순서를 정리합니다.

원칙:
- 코드: Colon/Lung/STAD 선행 구현 재사용
- 데이터: HNSC 실제 데이터만 사용
- `curated_data/`는 읽기 전용으로 취급
- 작업 S3 루트: `s3://say2-4team/20260408_new_pre_project_biso/20260427_new_pre_project_biso_HNSC/`

---

## 0. 사전 준비

- 작업 경로: `20260427_HNSC`
- Python: 3.10 (`conda` env `drug4` 권장)
- AWS CLI 인증 확인
- 공통 참고: 팀 상위 프로토콜 문서 + STAD 실행 경험

초기 디렉터리:

```bash
mkdir -p scripts configs data results reports logs nextflow
```

## 1. Raw 수집/동기화

HNSC raw mirror를 팀 S3에서 동기화합니다.

```bash
cd 20260427_HNSC
./scripts/parallel_download_hnsc.sh
```

기본 버킷 규칙:
- prefix: `s3://say2-4team/Hnsc_raw/`
- 하위 소스: `gdsc`, `depmap`, `cbioportal`, `geo`, `additional_sources`, `cptac` (존재하는 소스만 사용)

> 주의: 실제 HNSC raw prefix/하위 경로가 팀 표준과 다르면, 동기화 전에 반드시 경로를 확정하세요.
> 팀원 산출물 채택 기본 경로: `s3://say2-4team/20260409_eseo/20260421_hnsc/`

## 2. 전처리 (Step 2)

```bash
./scripts/run_step2_hnsc.sh
```

예상 산출물(목표):
- `data/labels.parquet`
- `data/drug_features.parquet`
- `data/drug_target_mapping.parquet`
- `data/lincs_hnsc.parquet`
- `reports/step2_integrated_qc_report.json`

HNSC 특이 매핑 이슈(DepMap cell line 이름 표기 불일치 등)가 있으면 STAD의 재필터링 전략을 동일하게 적용합니다.

## 3. FE 실행 (Step 3)

AWS Batch + Nextflow 기준:

```bash
cd nextflow
nextflow run main.nf -profile awsbatch \
  -work-dir s3://say2-4team/20260408_new_pre_project_biso/20260427_new_pre_project_biso_HNSC/work \
  -resume
```

필수:
- `-work-dir` 누락 금지
- Batch queue/container 권한 사전 확인

### 3-1. 이번 라운드 운영 방식 (중요)

이번 HNSC 라운드는 **Step 0~3을 팀원 산출물 채택 방식으로 진행**했습니다.

- 채택 소스(S3): `s3://say2-4team/20260409_eseo/20260421_hnsc/`
- 작업 S3: `s3://say2-4team/20260408_new_pre_project_biso/20260427_new_pre_project_biso_HNSC/`
- 원칙: 타 워크스페이스/원본 수정·삭제 금지, 필요한 자료는 복사만 수행

FE 기반 프로토콜 게이트 QC:
- Step2 채택 QC: `reports/qc_adoption_recheck.json`
- Step4 진입 전 QC: `reports/qc_step4_entry_gate.json`

해석 규칙:
- Step 0~3: 외부(팀원) 데이터 채택 + QC 완료 상태로 기록
- 실험 실행/평가: Step 3.5 이후부터 본 워크스페이스 기준으로 진행

## 4. 모델링/앙상블 (Step 4/5)

권장 순서:
1. Step3 산출 feature slim 생성
2. ML/DL/Graph 실행 (Step 4)
3. **Step 5 게이트 표 (고정):** `report_step5_gate_eval_spearman_table_stad.py` 로 **모델별** `cv5` / `groupcv` / `scaffoldcv` **val Spearman** + 각 eval의 **train−val gap**(`gap_spearman_mean`) + 세 eval 간 **span** → `results/<RESULT_TAG>/step5_gate_eval_spearman_table.csv` 검토 (Step4 종료 시 `run_step4_hnsc.sh` 가 자동 생성).
4. `_stad_ref/run_ensemble_catboost_dl_graph_stad.py` 로 **OOF 후보 표**만 생성 (`--candidates-only`) → 검토 → **확정 선택 JSON** (템플릿 복사·수정).
5. **확정 JSON**으로 OOF 앙상블 (`--selection-json ...`). 상세는 `STAD_reproduction_protocol.md` §3-3-4.
6. `results/<RESULT_TAG>/` 아래 성능 리포트 수집
7. **(권장) 지시서 기반 가중 앙상블:** `scripts/ensemble_directive_hnsc.py` → `stad_top30_drugs_ensemble_hnsc_directive_with_names.csv` 등 생성
8. **검증 근거 4분류 (VT1–VT4):** `docs/HNSC_validation_evidence_tiers_v1.md` · `configs/hnsc_validation_evidence_tiers.json` 기준으로 Top30에 `validation_evidence_tier` 부여  
   - 실행: `scripts/apply_validation_evidence_tiers_hnsc.py`  
   - 산출 예: `stad_top30_drugs_ensemble_hnsc_directive_validation_tiers.csv`  
   - 요약 리포트: `reports/hnsc_ensemble_top30_validation_tiers_report.md`

초기에는 STAD 스크립트를 복제한 `*_hnsc.py` 파일명을 사용하고, 내부 cohort 필터/암종명만 HNSC로 치환합니다.

Step 4 평가모드 운영 규칙(고정):
- `holdout`은 **제외**
- `cv5`, `groupcv`, `scaffoldcv`만 실행
- 실행 스크립트 기본값: `EVAL_MODES=cv5,groupcv,scaffoldcv`

Step 5 게이트(선택): `ENSEMBLE_REQUIRE_SELECTION=1` 이면 `run_step4_hnsc.sh` 가 후보 표만 남기고 중단하며, 이후 `ENSEMBLE_SELECTION_JSON` 경로를 지정해 앙상블만 재실행한다.

## 5. 외부검증 (Step 6)

Step6 준비(`_stad_ref/step6_prepare_top30_stad.py`) 시 **약물 추천 리스트에 동일 약물명 중복을 두지 않는다**(GDSC명 기준 dedupe, 더 높은 추천 순위·더 유리한 `pred_ic50_mean` 한 줄만 유지 후 30개 채움). STAD §3-3-6과 동일 정책.

Top 후보 CSV 준비 후 실행:

```bash
./scripts/run_step6_hnsc.sh
```

검증 축(권장):
- PRISM
- ClinicalTrials
- CPTAC
- GEO
- COSMIC

Step6 사전 점검(2026-04-28):
- preflight 리포트: `reports/HNSC_step6_external_validation_preflight_20260428.md`
- Top30 입력: `results/20260427_hnsc_step4_v1/stad_top30_drugs_ensemble_hnsc_directive_validation_tiers.csv`
- 실제 validation 입력 기준 경로: `base_data/20260421_hnsc/data/processed/validation_inputs/`
- 워크스페이스 S3 스테이징 완료:
  - `s3://say2-4team/20260408_new_pre_project_biso/20260427_new_pre_project_biso_HNSC/external_validation/validation_inputs/`
  - `s3://say2-4team/20260408_new_pre_project_biso/20260427_new_pre_project_biso_HNSC/external_validation/step6_hnsc_reference/`
- Step6 최종 요약(2026-04-28):
  - Top30 매칭: 28/30 (미매칭: `Pyridostatin`, `Schweinfurthin A`)
  - 보완 반영: COSMIC bundle + OpenTargets + PRISM/ClinicalTrials raw fallback
  - 최종 리포트: `reports/HNSC_step6_final_and_step7_progress_20260428.md`

## 6. 후보 정교화 (Step 7)

```bash
./scripts/run_step7_hnsc.sh
```

구성:
- ADMET 필터링
- Top15 선정
- (선택) AlphaFold
- HNSC cohort/subtype 문맥 분석

Step7 진행(2026-04-28):
- 1차 Top15: `results/20260427_hnsc_step4_v1/step7_top15_hnsc_provisional.csv`
- 운영 메모:
  - `Camptothecin`(VT4), `Pyridostatin`(미매칭·VT4), `Schweinfurthin A`(미매칭·VT4) 는 `REVIEW`로 분리
  - Step8/9 이전에 최종 포함 여부 확정 필요

## 7. KG/LLM (Step 8/9)

```bash
./scripts/run_step8_9_hnsc.sh
```

출력 목표:
- `results/hnsc_knowledge_graph_data.json`
- `results/hnsc_knowledge_graph_viewer.html`
- `results/hnsc_drug_explanations.json`

## Dashboard (운영 모니터링)

대시보드가 없는 경우, 아래 앱을 생성해 운영 상태를 확인합니다.

```bash
streamlit run hnsc_dashboard/app.py
```

대시보드에는 최소 아래를 표기:
- Step 0~3: 외부 데이터 채택 경로 + QC 리포트 링크
- Step 3.5: 산출물 존재/shape
- Step 4: 모델별 진행 상태(ML/DL/Graph)와 결과 파일 존재 여부
- Step 6: 소스별 매칭 수(PRISM/CT/CPTAC/TCGA/OpenTargets/COSMIC/GEO)
- Step 7: Top15 확정/REVIEW 구간

## 8. 시작 체크리스트

- [ ] `scripts/parallel_download_hnsc.sh`에서 S3 prefix를 팀 표준으로 확정
- [ ] `scripts/run_step2_hnsc.sh`에서 HNSC 전용 전처리 파이프라인 연결
- [ ] `nextflow/main.nf` 또는 참조 nextflow를 HNSC 프로젝트로 연결
- [ ] Step 2 QC 기준(매칭율/누락 셀 허용범위) 정의
- [ ] 결과 태그 규칙(`RUN_ID`, `RESULT_TAG`) 정의

---

## 빠른 시작

```bash
cd 20260427_HNSC
chmod +x scripts/*.sh
./scripts/parallel_download_hnsc.sh
./scripts/run_step2_hnsc.sh
```

이 문서는 **프로젝트 시작점**입니다. Step 2 결과를 확인한 뒤, STAD 구현체를 HNSC로 안전하게 복제/치환하는 방식으로 확장하세요.

---

## 9. 현 라운드 종합 결과 기록 (2026-04-28)

요청 기준(프로토콜/레포트/대시보드 공통 표기):
- FE 데이터 기반 모델학습 결과(전체)
- 대표 앙상블 결과 및 Top30
- 외부검증 방법/리스트
- ADMET/Step7 방법 및 최종 Top15

### 9-1. Step4 모델학습 + 대표 앙상블

- RESULT_TAG: `20260427_hnsc_step4_v1`
- 대표 Top30: `results/20260427_hnsc_step4_v1/top30_tier1234_fixed_hnsc.csv` (30행)
- Tier1/2/3/4 분포(Top30):
  - Tier1: 3
  - Tier2: 12
  - Tier3: 10
  - Tier4: 5

### 9-2. Step6 외부검증 (방법/결과)

- 입력: Top30 (`results/20260427_hnsc_step4_v1/`)
- 실행: `scripts/run_step6_hnsc.sh` + `scripts/step6_ext_comprehensive_hnsc_independent.py`
- 요약 파일: `external_validation/20260427_hnsc_step4_v1/external_validation_independent_summary.json`

최종 수치:
- Top30 처리: 30
- 1개 이상 외부근거 매칭: 28/30
- 미매칭: 2 (`Pyridostatin`, `Schweinfurthin A`)
- 소스별:
  - PRISM(any): 21
  - ClinicalTrials: 17
  - Patient context(TCGA/CPTAC): 14
  - OpenTargets: 14
  - COSMIC: 3
  - GEO(drug-level): 0 (`DATASET_ONLY`)

### 9-3. Step7 ADMET/후보정제 (방법/결과)

- 실행: `scripts/run_step7_hnsc.sh` + `scripts/step7_finalize_hnsc.py`
- 산출: `results/20260427_hnsc_step4_v1/step7_top15_hnsc_provisional_with_fixed_tier.csv`
- 정책: 외부근거 + Tier1/2/3/4 + 독성/검증 필요물질 REVIEW 분리

최종 Top15 분포:
- KEEP_TOP15: 12
- REVIEW: 3 (`Camptothecin`, `Pyridostatin`, `Schweinfurthin A`)
- Tier 분포(Top15): Tier1=2, Tier2=8, Tier3=2, Tier4=3
