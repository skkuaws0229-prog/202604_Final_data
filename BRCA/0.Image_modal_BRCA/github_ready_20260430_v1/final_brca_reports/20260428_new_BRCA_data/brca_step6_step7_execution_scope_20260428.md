# BRCA Step6-Step7 Execution Scope

- Date: 2026-04-28
- Basis: user-approved execution scope for current BRCA rerun

## Step 6

- Primary external validation: `METABRIC`
- Validation methods:
  - Method A: target gene expression validation
  - Method B: survival stratification
  - Method C: known BRCA drug precision
- Reference implementation:
  - `20260415_preproject_protocol_choi/run_metabric_validation_final.py`
- Current decision:
  - Re-run Step 6 for the **current BRCA ensemble Top30**
  - Treat METABRIC A/B/C as the official external-validation gate

## Supplemental interpretation

- Optional layer after Step 6:
  - `ClinicalTrials.gov`
  - manual review
- Reference report:
  - `20260415_preproject_protocol_choi/CLINICAL_VALIDATION_COMPREHENSIVE_REPORT.md`
- Current decision:
  - This layer is secondary to METABRIC
  - Use it to interpret novelty / repurposing value, not as the primary Step 6 gate

## Step 7

- Scope: `ADMET 22 assay`
- Reference basis:
  - `drug_repurposing_pipeline_protocol.md`
  - `20260415_preproject_protocol_choi/run_admet_analysis_final.py`
- Method:
  - `TDC ADMET benchmark (22 assays)`
  - `Tanimoto similarity v1`
- Current decision:
  - Step 7 is separate from Step 6
  - Do not mix ADMET completeness checks into the current Step 6 discussion

## Implementation note

- Existing legacy BRCA scripts are based on earlier consensus outputs such as:
  - `metabric_validation_final/top15_validated_consensus.csv`
  - `admet_analysis_final/admet_detailed_24drugs.csv`
- For the current rerun, Step 6 and Step 7 should be adapted to:
  - the current directive-based BRCA ensemble
  - the current deduplicated Top30
  - the current tiered candidate table when needed for reporting
