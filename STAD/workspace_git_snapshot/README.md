# 20260421_new_pre_project_biso_STAD

위암(TCGA-STAD) drug repurposing 파이프라인 프로젝트입니다.  
코드는 Colon/Lung 파이프라인 구조를 재사용하고, 데이터 경로만 STAD 기준으로 운영합니다.

> 문서 버전: `v2026.04.24-r4`  
> 최종 업데이트: `2026-04-24`  
> 변경 요약: 대시보드 사이드바(Overview·Step 0-1…9), Step 8 다질환 KG, Step 9 안내, 프로토콜 §4.4A 반영

## 현재 상태

| Stage | Status |
| ----- | ------ |
| Step 0-1 | Stad_raw 기반 raw 수집/동기화 스크립트 구성 완료 |
| Step 2 | 전처리 완료 + depmap 재필터링 (`filter_stad_depmap_to_labels.py`) |
| Step 3 | FE 완료 (AWS Batch), features_rows=5118, sample join ~83% |
| Step 3.5 | Feature selection 완료 → `fe_qc/20260421_stad_fe_v1/features_slim.parquet` (Step 4 입력) |
| Step 4 | ML→DL→Graph 단일 모델 학습/평가 스크립트 + `run_step4_stad.sh` (기본 끝에 Step 5용 앙상블 JSON 생성, `SKIP_ENSEMBLE=1`로 생략 가능) |
| Step 5 | `scripts/run_ensemble_catboost_dl_graph_stad.py` — **CatBoost(고정) + phase별 best DL + GraphSAGE(고정)** OOF 블렌드, Lung `phase3_ensemble_analysis` 스타일(Simple / JSON 가중 / 그리드). 산출: `results/<tag>/ensemble_catboost_dl_graph_groupcv.json` |
| Step 6 | 외부검증(`run_step6_stad.sh`) — PRISM/ClinicalTrials/COSMIC/CPTAC/GEO + 종합 |
| Step 7 | ADMET·Top15·AlphaFold·서브타입 — `./scripts/run_step7_stad.sh` |
| Step 8 | KG JSON·HTML·Neo4j(선택) — `./scripts/run_step8_9_stad.sh` ; 대시보드에서 위·대장·폐·유방 네트워크 전환 |
| Step 9 | LLM 근거 — `STAD_LLM_DRY_RUN=1` 로 형식 검증 가능 |
| 대시보드 | `streamlit run stad_dashboard/app.py` — **왼쪽 사이드바**에서 전 단계 + Step 8 질환별 KG |


## 핵심 제약

- `curated_data/`는 raw mirror로 취급하며 **읽기 전용**입니다. 수정/삭제 금지.
- 전처리/가공 산출물은 `curated_data/processed/`, `data/`, `reports/`, `logs/`에만 생성합니다.
- LINCS는 `configs/lincs_source.json` 기준으로 `GSE92742`를 사용합니다.
- 현재 `GSE92742` 기준 usable STAD cell은 `AGS` 1개입니다.  
이후 분석/해석 문서에 **coverage limitation(AGS-only)** 를 명시해야 합니다.

### ⚠️ STAD 고유 주의사항 (Colon/Lung과 다른 점)

STAD는 labels sample_id와 DepMap cell_line_name의 표기가 다릅니다.

- labels: `HGC27`, `KATOIII` (stripped)
- DepMap: `HGC-27`, `KATO III` (원본)

이 때문에 **반드시** `filter_stad_depmap_to_labels.py` 단계가 필요합니다.
이 단계 없이 FE로 가면 sample join이 ~60% 수준으로 떨어지고 37% row loss 발생합니다.

이 단계는 `run_step2_stad.sh`에 이미 통합되어 있습니다. Step 2 QC에서
`labels_cells_in_depmap == 20` 확인만 하시면 됩니다.

### Step 4 + Step 5 앙상블 (요약)

1. **입력:** Step 3.5의 `features_slim.parquet`만 사용 (`prepare_phase2a/bc_data_stad.py` → `data/<run_id>/X_*.npy`, `y_train.npy`).
2. **학습:** `run_ml_all_stad.py` / `run_dl_all_stad.py` / `run_graph_all_stad.py` — 각 `results/<RESULT_TAG>/{ml,dl,graph}/`에 JSON + `*_groupcv_oof/` 등.
3. **Step 5 앙상블:** 전 모델 혼합이 아니라 **phase마다 CatBoost OOF(고정) + OOF Spearman 최고 DL 1개 + GraphSAGE OOF(고정)**만 블렌드.
4. **diversity 필드:** 예측 벡터 쌍의 **평균 Spearman ρ** — 값이 **크면** 세 모델 예측이 **비슷**(보완 다양성은 작음). 직관용으로 JSON에 **`complementarity_1_minus_pairwise_pred_rho`** 포함.

## 주요 참고 문서

- 운영 컨텍스트: [configs/CONTEXT.md](configs/CONTEXT.md)
- STAD 재현 절차: [STAD_reproduction_protocol.md](STAD_reproduction_protocol.md) (§3-3 Step 4·앙상블·대시보드)
- 상위(계속 업데이트) 프로토콜: 팀 배포본 `drug_repurposing_pipeline_protocol`(로컬 절대 경로는 README에 적지 않음)
- 코드 템플릿: [20260420_new_pre_project_biso_Colon](../20260420_new_pre_project_biso_Colon), [20260416_new_pre_project_biso_Lung](../20260416_new_pre_project_biso_Lung)

## 빠른 실행 순서

### 1) Raw 동기화

```bash
cd 20260421_new_pre_project_biso_STAD
./scripts/parallel_download_stad.sh
```

### 2) LINCS GSE92742 정렬 (필요 시)

`Stad_raw/LInc1000`에 `GSE92742`가 없고, 같은 머신의 Colon 프로젝트에 이미 있으면:

```bash
./scripts/link_lincs_gse92742_from_colon.sh
```

### 3) 전처리 (Step 2)

```bash
./scripts/run_step2_stad.sh
```

### 3-1) Feature selection (Step 3.5)

Step 3 `fe_qc/` 산출물이 있을 때:

```bash
python3 scripts/feature_selection.py \
  --features fe_qc/20260421_stad_fe_v1/features/features.parquet \
  --pair-features fe_qc/20260421_stad_fe_v1/pair_features/pair_features_newfe_v2.parquet \
  --output-dir fe_qc/20260421_stad_fe_v1 \
  --low-var-threshold 0.01 \
  --high-corr-threshold 0.95
```

### 3-2) Step 4 + Step 5 앙상블 (로컬)

```bash
export RUN_ID=step4_stad_inputs_20260422_002
export RESULT_TAG=20260422_stad_step4_v2
./scripts/run_step4_stad.sh
```

앙상블만 다시 돌리기:

```bash
python3 scripts/run_ensemble_catboost_dl_graph_stad.py \
  --run-id "$RUN_ID" --result-tag "$RESULT_TAG" --eval-mode groupcv
```

대시보드:

```bash
streamlit run stad_dashboard/app.py
```

(`stad_dashboard/app.py` 상단 `STEP4_RUN_ID` / `STEP4_RESULT_TAG`를 위와 맞출 것.)

### 4) LINCS cell_id 재검증/재생성 (GSE92742 기준)

```bash
python3 scripts/rebuild_stad_lincs_cell_ids_gse92742.py --project-root .
```

산출물:

- `configs/stad_lincs_cell_ids.json`
- `reports/lincs/stad_lincs_cell_id_review.csv`
- `reports/lincs/stad_lincs_cell_id_qc.json`

## Step 6 외부검증 (STAD)

```bash
SYNC_S3=1 ./scripts/run_step6_stad.sh
```

주의:

- `results/stad_top30_phase2b_catboost_with_names.csv`
- `results/stad_top30_phase2c_catboost_with_names.csv`
- `results/stad_top30_unified_2b_and_2c_with_names.csv`

위 3개가 있어야 Step 6이 끝까지 실행됩니다.

## 현재 확인된 사실 (LINCS coverage)

LINCS evidence in STAD is AGS-only under GSE92742 (362 trt_cp signatures).  
This limitation has been triple-verified (2026-04-21):  
(a) GSE92742 primary_site/subtype strict: AGS only  
(b) GSE70138 phase II plate: AGS present but 0 trt_cp; merge/replace yields no gain  
(c) Deep alias/normalize/substring check: no missed stomach cells  
Downstream interpretation relies more heavily on DepMap/GDSC/PRISM axes  
for drug repurposing evidence, with LINCS used as supporting signal for AGS only.

근거 문서:

- `reports/lincs/stad_lincs_cell_id_qc.json` (1차 검증)
- `reports/lincs/stad_lincs_gse70138_verification.json` (2차 검증)
- `reports/lincs/stad_lincs_alias_deep_check.json` (3차 검증)

