#!/usr/bin/env bash
set -euo pipefail

# v2 one-click: Step6 → Step7 (same scripts as v1, different default paths).
# Does not overwrite v1 artifacts.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULT_TAG="${RESULT_TAG:-20260428_liver_step4_v2}"
TOP30_CSV="${TOP30_CSV:-${ROOT_DIR}/results/${RESULT_TAG}/lihc_top30_directive_ensemble_with_names.csv}"
SKIP_STEP6="${SKIP_STEP6:-0}"

NESTED_PROTOCOL_ROOT="$(cd "${ROOT_DIR}/../20260415_preproject_choi_protocol_v1_bisotest/20260421_new_pre_project_biso_STAD" && pwd)"
RUNTIME_SCRIPTS_DIR="${ROOT_DIR}/scripts"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --result-tag)
      RESULT_TAG="$2"
      shift 2
      ;;
    --top30-csv)
      TOP30_CSV="$2"
      shift 2
      ;;
    --skip-step6)
      SKIP_STEP6="1"
      shift 1
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [v2] $*"
}

require_file() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    echo "ERROR: required file not found: $f" >&2
    exit 1
  fi
}

ensure_runtime_script() {
  local script_name="$1"
  local local_script="${RUNTIME_SCRIPTS_DIR}/${script_name}"
  local source_script="${NESTED_PROTOCOL_ROOT}/scripts/${script_name}"
  if [[ -f "$local_script" ]]; then
    return 0
  fi
  require_file "$source_script"
  cp "$source_script" "$local_script"
}

mkdir -p "${ROOT_DIR}/results/${RESULT_TAG}" "${ROOT_DIR}/external_validation/${RESULT_TAG}" "${ROOT_DIR}/logs"

require_file "$TOP30_CSV"

if [[ "$SKIP_STEP6" != "1" ]]; then
  log "Step6 start (CPTAC excluded): result_tag=${RESULT_TAG}"
  cp "$TOP30_CSV" "${ROOT_DIR}/results/${RESULT_TAG}/lihc_top30_directive_ensemble_with_names.csv"
  python3 "${ROOT_DIR}/scripts/step6_ext_lihc_independent_cptac_excluded.py" \
    --project-root "$ROOT_DIR" \
    --result-tag "$RESULT_TAG"
else
  log "Step6 skipped (--skip-step6)."
fi

log "Ensure Step7 runtime scripts"
ensure_runtime_script "step7_1_admet_filtering_stad.py"
ensure_runtime_script "step7_2_select_top15_lihc.py"

log "Step7-1 start (ADMET 22 assays)"
STAD_TOP30_CSV="$TOP30_CSV" python3 "${ROOT_DIR}/scripts/step7_1_admet_filtering_stad.py"

log "Step7-2 start (Top15)"
python3 "${ROOT_DIR}/scripts/step7_2_select_top15_lihc.py"

log "Done v2 one-click. RESULT_TAG=${RESULT_TAG}"
