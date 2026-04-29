#!/usr/bin/env bash
# 20260428_colon_v2 Step7 전체: (1) 초이 22 assay ADMET (STAD/step7_1과 동일 로직)
#                        (2) Top30 → Top15 + CRC Tier1–4
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "${ROOT}/.." && pwd)"
cd "${ROOT}"

TOP30="${TOP30_CSV:-${ROOT}/20260428_colon_v2_step6_top30_drug_recommendations_tier1_tier2_tier3_tier4.csv}"

# 동일 워크스페이스 내 공유 자료 (GDSC drug SMILES + TDC ADMET 라이브러리)
_DEFAULT_FEAT="${REPO}/20260415_preproject_choi_protocol_v1_bisotest/20260421_new_pre_project_biso_STAD/data/step4_lihc_v2_manual/drug_features.parquet"
_DEFAULT_ADMET="${REPO}/20260415_preproject_choi_protocol_v1_bisotest/curated_data/admet"

COLON_DRUG_FEATURES="${COLON_DRUG_FEATURES:-${_DEFAULT_FEAT}}"
COLON_TDC_ADMET="${COLON_TDC_ADMET:-${_DEFAULT_ADMET}}"

if [[ -f "${COLON_DRUG_FEATURES}" && -d "${COLON_TDC_ADMET}/tdc_admet_group/admet_group" ]]; then
  echo "[INFO] Step7-1 ADMET 22 assay (Choi / Tanimoto, STAD와 동일 스택)"
  echo "       drug_features: ${COLON_DRUG_FEATURES}"
  echo "       tdc_admet:     ${COLON_TDC_ADMET}"
  python3 "${ROOT}/scripts/20260428_colon_v2_step7_1_admet_22assay_gate.py" \
    --package-root "${ROOT}" \
    --top30-csv "${TOP30}" \
    --drug-features-parquet "${COLON_DRUG_FEATURES}" \
    --tdc-admet-root "${COLON_TDC_ADMET}"
else
  echo "[WARN] 기본 경로에 drug_features 또는 tdc_admet_group 없음 → Step7-1 생략."
  echo "       COLON_DRUG_FEATURES / COLON_TDC_ADMET 를 수동 지정하세요."
fi

echo "[INFO] Step7 Top15 + CRC tier (ADMET CSV 있으면 자동 병합)"
python3 "${ROOT}/scripts/20260428_colon_v2_step7_select_top15_crc_clinical_tiers.py" \
  --package-root "${ROOT}" \
  --top30-csv "${TOP30}"

echo "[OK] 산출:"
echo "    ..._admet_22assay_choi_protocol_tanimoto_top30_scored.csv / _summary.json"
echo "    ..._top15_crc_tier1234_admet22assay_choi_protocol.csv (또는 no_admet_...)"
