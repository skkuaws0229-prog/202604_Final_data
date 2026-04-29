#!/usr/bin/env bash
# Build a reproducibility bundle by COPYING local artifacts (never modify/delete sources).
# Output: Liver cancer/s3_staging_upload/repro_lihc_step4_v2_<STAMP>/
#
# Usage:
#   STAMP=20260429 bash scripts/package_lihc_v2_repro_bundle.sh
#
set -euo pipefail

STAMP="${STAMP:-$(date +%Y%m%d)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIVER_PKG="$(cd "${SCRIPT_DIR}/.." && pwd)"
NESTED_REPO="$(cd "${LIVER_PKG}/../20260415_preproject_choi_protocol_v1_bisotest" && pwd)"
STAD="${NESTED_REPO}/20260421_new_pre_project_biso_STAD"
LIVER_BASE="$(cd "${LIVER_PKG}/../20260427_Liver/base_data/20260421_liver" && pwd)"
RESULT_TAG="${RESULT_TAG:-20260428_liver_step4_v2}"
RUN_ID="${RUN_ID:-step4_lihc_v2_manual}"

OUT="${LIVER_PKG}/s3_staging_upload/repro_${RESULT_TAG}_${STAMP}"

log() { echo "[package_lihc_v2_repro] $*"; }

require_dir() {
  if [[ ! -d "$1" ]]; then
    echo "Missing directory: $1" >&2
    exit 1
  fi
}

require_dir "$STAD"
require_dir "$LIVER_BASE"

log "OUT=${OUT}"
rm -rf "${OUT}"
mkdir -p "${OUT}"

copy_tree() {
  local src="$1"
  local dst="$2"
  mkdir -p "${dst}"
  cp -R "${src}/." "${dst}/"
}

log "Copy STAD results/${RESULT_TAG}"
copy_tree "${STAD}/results/${RESULT_TAG}" "${OUT}/stad_results_${RESULT_TAG}"

log "Copy STAD data/${RUN_ID}"
copy_tree "${STAD}/data/${RUN_ID}" "${OUT}/stad_data_${RUN_ID}"

log "Copy STAD reports (step4 metrics review)"
mkdir -p "${OUT}/stad_reports"
for f in "${STAD}/reports/step4_metrics_review_${RESULT_TAG}"*.csv "${STAD}/reports/step4_metrics_review_${RESULT_TAG}"*.md; do
  [[ -f "$f" ]] && cp -f "$f" "${OUT}/stad_reports/" || true
done

log "Copy STAD configs (lihc v2)"
mkdir -p "${OUT}/stad_configs"
cp -f "${STAD}/configs/lihc_v2_clinical_tier_overrides.tsv" "${OUT}/stad_configs/" 2>/dev/null || true
cp -f "${STAD}/configs/lihc_v2_hcc_approved_anchors.tsv" "${OUT}/stad_configs/" 2>/dev/null || true

log "Copy key STAD scripts (snapshots)"
mkdir -p "${OUT}/stad_scripts_snapshot"
for f in ensemble_lihc_v2_directive_weighted.py prepare_lihc_v2_top30_dedup_tiered.py summarize_step4_metrics_stad.py; do
  [[ -f "${STAD}/scripts/$f" ]] && cp -f "${STAD}/scripts/$f" "${OUT}/stad_scripts_snapshot/"
done

log "Copy Liver processed inputs used by STAD (train_table, drug_features)"
mkdir -p "${OUT}/liver_processed_snapshot/model_inputs" "${OUT}/liver_processed_snapshot/slim_inputs"
copy_tree "${LIVER_BASE}/data/processed/model_inputs" "${OUT}/liver_processed_snapshot/model_inputs"
copy_tree "${LIVER_BASE}/data/processed/slim_inputs" "${OUT}/liver_processed_snapshot/slim_inputs"

log "Copy Liver cancer handoff results + external_validation"
if [[ -d "${LIVER_PKG}/results/${RESULT_TAG}" ]]; then
  copy_tree "${LIVER_PKG}/results/${RESULT_TAG}" "${OUT}/liver_cancer_results_${RESULT_TAG}"
fi
if [[ -d "${LIVER_PKG}/external_validation/${RESULT_TAG}" ]]; then
  copy_tree "${LIVER_PKG}/external_validation/${RESULT_TAG}" "${OUT}/liver_cancer_external_validation_${RESULT_TAG}"
fi

log "Copy v2 protocol/report snapshots from Liver cancer/reports"
mkdir -p "${OUT}/liver_cancer_reports_snapshot"
for f in LIHC_STAD_operational_protocol_20260428_v2.md LIHC_STAD_execution_report_20260428_v2.md LIVER_ONECLICK_RUNBOOK_v2.md LIHC_V2_READINESS_CHECKLIST.md LIHC_V2_S3_REPRO_HANDOFF.md; do
  [[ -f "${LIVER_PKG}/reports/$f" ]] && cp -f "${LIVER_PKG}/reports/$f" "${OUT}/liver_cancer_reports_snapshot/"
done

log "Optional: copy Downloads directive (LIHC_v2_ensemble_directive.md)"
mkdir -p "${OUT}/protocol_used_files/docs"
if [[ -f "${HOME}/Downloads/LIHC_v2_ensemble_directive.md" ]]; then
  cp -f "${HOME}/Downloads/LIHC_v2_ensemble_directive.md" "${OUT}/protocol_used_files/docs/"
else
  log "SKIP: ~/Downloads/LIHC_v2_ensemble_directive.md not found"
fi

python3 <<PY
import json, os, subprocess, hashlib
from pathlib import Path
out = Path("${OUT}")
manifest = {
    "bundle_stamp": "${STAMP}",
    "result_tag": "${RESULT_TAG}",
    "run_id": "${RUN_ID}",
    "stad_root": "${STAD}",
    "liver_package": "${LIVER_PKG}",
    "notes": "Copied artifacts only; sources were not modified.",
}
# lightweight file list (top-level sizes)
rows = []
for p in sorted(out.rglob("*")):
    if p.is_file():
        try:
            rows.append({"path": str(p.relative_to(out)), "bytes": p.stat().st_size})
        except OSError:
            pass
manifest["files"] = rows[:5000]
manifest["file_count"] = len(rows)
(out / "REPRO_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "out": str(out), "file_count": len(rows)}, indent=2))
PY

log "Done. Upload with: bash scripts/upload_lihc_v2_repro_to_s3.sh"
