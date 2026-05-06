# BRCA Reproduction Protocol

- Date: 2026-04-28
- Version: v1
- Scope: reproduce the current BRCA rerun from Step4 summary through Step7 ADMET

## Canonical scope

- Step5 ensemble: directive-based A/B comparison, winner = `A`
- Step6 external validation: `METABRIC Method A/B/C`
- Step6 supplemental interpretation: `ClinicalTrials.gov + manual review`
- Step7 safety gate: `ADMET 22 assay`, `TDC benchmark`, `Tanimoto similarity v1`

## Key inputs

- Step4 summary: `brca_model_performance_summary.csv`
- Step5 top30: `brca_directive_top30_unique_candidates.csv`
- Step5 tier map: `brca_directive_top30_tiered_candidates.csv`
- Step6 METABRIC expression:
  `20260415_preproject_protocol_choi/data/metabric/metabric_expression_basic_clean_20260406.parquet`
- Step6 METABRIC clinical:
  `20260415_preproject_protocol_choi/data/metabric/metabric_clinical_patient_basic_clean_20260406.parquet`
- Step7 ADMET assay dir:
  `20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/curated_data/admet/tdc_admet_group/admet_group`

## Fixed decisions

- Ensemble winner: `A`
- GroupCV Spearman: `0.4834`
- ScaffoldCV Spearman: `0.3644`
- Step6 input: current BRCA Top30, not legacy consensus top24
- Step7 input: all 30 drugs from current Top30
- Final candidate cut: top 15 after Step7 ranking

## Reproduction order

1. Step4 summary refresh
   - Command: `python3 scripts/extract_brca_step4_summary.py`
   - Output: `brca_model_performance_summary.csv`, `brca_model_performance_detailed.csv`

2. Step5 ensemble rerun
   - Command: `python3 scripts/run_brca_directive_ensemble.py`
   - Output: `brca_directive_ensemble_validation_summary.csv`, `brca_directive_top30_unique_candidates.csv`

3. Tier classification
   - Command: `python3 scripts/classify_brca_top30_tiers.py`
   - Output: `brca_directive_top30_tiered_candidates.csv`

4. Step6 METABRIC rerun
   - Command: `python3 scripts/run_brca_step6_metabric_adapter.py`
   - Output dir: `step6_metabric_validation/`

5. Step7 ADMET rerun
   - Command: `python3 scripts/run_brca_step7_admet_adapter.py`
   - Output dir: `step7_admet_22assay/`

6. Materials refresh
   - Command: `python3 scripts/build_brca_repro_materials.py`

7. Dashboard
   - Command: `streamlit run 20260428_new_BRCA_data/brca_repro_dashboard.py`

## Tier definition

- Tier 1: 유방암 치료제
- Tier 2: 유방암 적응증 확장 연구 치료제
- Tier 3: 유방암 비사용 치료제
- Tier 4: 화합물 또는 미지 약물

## Step6 acceptance view

- Current target-expressed drugs: `11/30`
- Current BRCA-pathway drugs: `12/30`
- Current survival-significant drugs: `2/30`

## Step7 acceptance view

- PASS: `6`
- WARNING: `21`
- FAIL: `3`
- Hard fail: `2`

## Interpretation guide

- Step6 METABRIC is a biological validation layer that helps interpret mechanistic plausibility.
- Step7 ADMET 22 assay is the practical ranking layer that produces the current Final15.
- The current Final15 should be read as a mixed shortlist of breast-cancer drugs, indication-expansion therapies, non-breast therapies, and Tier4 compounds.
- Positive controls, repurposing candidates, and discovery-only compounds should be interpreted as different downstream action classes rather than one homogeneous list.
- Tier4 signals can still be valuable, but should be discussed more cautiously than approved therapies.

## Dashboard view

- Overview tab: final status, Step7 counts, Final15 snapshot
- Step5 tab: A/B validation results, Top30 tiered candidate table
- Step6 tab: METABRIC A/B/C metrics and validation score view
- Step7 tab: ADMET verdict distribution, Final15 tier distribution, full assay table

## Notes

- This rerun intentionally separates Step6 and Step7.
- Step6 does not gate the Top30 input for Step7; all 30 current drugs enter ADMET.
- Current Step7 verdict summary: PASS `6`, WARNING `21`, FAIL `3`
