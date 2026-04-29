#!/usr/bin/env bash
# Upload repro bundle built by package_lihc_v2_repro_bundle.sh to S3 (copy semantics: sync uploads copies from disk).
#
# Usage:
#   STAMP=20260429 bash scripts/upload_lihc_v2_repro_to_s3.sh
#
# Env:
#   S3_LIVER_GENERATED_ROOT  default: s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated
#   RESULT_TAG               default: 20260428_liver_step4_v2
#
set -euo pipefail

STAMP="${STAMP:-$(date +%Y%m%d)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIVER_PKG="$(cd "${SCRIPT_DIR}/.." && pwd)"
RESULT_TAG="${RESULT_TAG:-20260428_liver_step4_v2}"

S3_LIVER_GENERATED_ROOT="${S3_LIVER_GENERATED_ROOT:-s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated}"
DEST="${S3_LIVER_GENERATED_ROOT}/repro_${RESULT_TAG}_${STAMP}/"

SRC="${LIVER_PKG}/s3_staging_upload/repro_${RESULT_TAG}_${STAMP}"

if [[ ! -d "$SRC" ]]; then
  echo "Missing bundle: $SRC — run: STAMP=${STAMP} bash scripts/package_lihc_v2_repro_bundle.sh" >&2
  exit 1
fi

echo "[upload] SRC=${SRC}"
echo "[upload] DEST=${DEST}"

aws s3 sync "${SRC}" "${DEST}" --only-show-errors

echo "[upload] OK"

# Optional: pull canonical protocol doc from existing S3 location into same bucket subtree (duplicate for completeness).
S3_DOCS="${S3_LIVER_GENERATED_ROOT%/generated}/protocol_used_files/docs"
if aws s3 ls "${S3_DOCS}/LIHC_ensemble_directive.md" >/dev/null 2>&1; then
  echo "[upload] Also copying protocol_used_files docs sibling into generated bundle mirror (optional)"
  mkdir -p "${LIVER_PKG}/s3_staging_upload/_s3_mirror_docs"
  aws s3 cp "${S3_DOCS}/LIHC_ensemble_directive.md" "${LIVER_PKG}/s3_staging_upload/_s3_mirror_docs/LIHC_ensemble_directive.md" || true
  aws s3 cp "${LIVER_PKG}/s3_staging_upload/_s3_mirror_docs/LIHC_ensemble_directive.md" "${DEST}protocol_mirror/LIHC_ensemble_directive_v1_from_s3_docs.md" || true
fi
