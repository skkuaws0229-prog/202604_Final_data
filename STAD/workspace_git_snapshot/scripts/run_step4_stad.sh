#!/usr/bin/env bash
set -euo pipefail

# STAD Step 4 runner (safe mode)
# - creates isolated run-id outputs under data/<run_id>/
# - does NOT overwrite prior run unless --force passed to sub-steps
# - prefers MPS, falls back to CPU automatically in model scripts

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

RUN_ID="${RUN_ID:-step4_stad_inputs_$(date +%Y%m%d_%H%M%S)}"
LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "$LOG_DIR"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[STAD Step4] PROJECT_ROOT=$PROJECT_ROOT"
echo "[STAD Step4] RUN_ID=$RUN_ID"
RESULT_TAG="${RESULT_TAG:-20260421_stad_step4_v1}"
echo "[STAD Step4] RESULT_TAG=$RESULT_TAG"
echo "[STAD Step4] FORCE_CPU=${FORCE_CPU:-0}"
echo "[STAD Step4] PYTHON_BIN=$PYTHON_BIN"

echo "[STAD Step4] Prepare Phase 2A inputs..."
"$PYTHON_BIN" scripts/prepare_phase2a_data_stad.py --run-id "$RUN_ID" \
  2>&1 | tee "${LOG_DIR}/stad_step4_prepare_phase2a_${RUN_ID}.log"

echo "[STAD Step4] Prepare Phase 2B/2C inputs..."
"$PYTHON_BIN" scripts/prepare_phase2bc_data_stad.py --run-id "$RUN_ID" \
  2>&1 | tee "${LOG_DIR}/stad_step4_prepare_phase2bc_${RUN_ID}.log"

echo "[STAD Step4] Input preparation complete."

echo "[STAD Step4] Run ML experiments (6 models, 4 eval modes)..."
"$PYTHON_BIN" scripts/run_ml_all_stad.py \
  --run-id "$RUN_ID" \
  --result-tag "$RESULT_TAG" \
  2>&1 | tee "${LOG_DIR}/stad_step4_ml_${RUN_ID}.log"

echo "[STAD Step4] ML complete. Run DL experiments (7 models, 4 eval modes)..."
"$PYTHON_BIN" scripts/run_dl_all_stad.py \
  --run-id "$RUN_ID" \
  --result-tag "$RESULT_TAG" \
  2>&1 | tee "${LOG_DIR}/stad_step4_dl_${RUN_ID}.log"

echo "[STAD Step4] DL complete. Run Graph experiments (2 models, 4 eval modes)..."
"$PYTHON_BIN" scripts/run_graph_all_stad.py \
  --run-id "$RUN_ID" \
  --result-tag "$RESULT_TAG" \
  2>&1 | tee "${LOG_DIR}/stad_step4_graph_${RUN_ID}.log"

echo "[STAD Step4] Graph complete. Step4 all phases done."

if [[ "${SKIP_ENSEMBLE:-0}" != "1" ]]; then
  echo "[STAD Step4] CatBoost + DL + Graph OOF ensemble (Lung-style)..."
  "$PYTHON_BIN" scripts/run_ensemble_catboost_dl_graph_stad.py \
    --run-id "$RUN_ID" \
    --result-tag "$RESULT_TAG" \
    --eval-mode groupcv \
    2>&1 | tee "${LOG_DIR}/stad_step4_ensemble_cat_dl_gr_${RUN_ID}.log"
  echo "[STAD Step4] Ensemble summary written under results/${RESULT_TAG}/"
else
  echo "[STAD Step4] SKIP_ENSEMBLE=1 — skipping run_ensemble_catboost_dl_graph_stad.py"
fi
