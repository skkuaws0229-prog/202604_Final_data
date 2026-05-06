# 20260428_new_BRCA_data

This folder is the canonical bundle for the current BRCA rerun.

## Main deliverables

- `BRCA_reproduction_protocol_20260428_v1.md`: step-by-step rerun protocol
- `BRCA_experiment_report_20260428.md`: experiment report from Step4 through Step7
- `BRCA_reproducibility_manifest_20260428.json`: machine-readable path/command manifest
- `brca_repro_dashboard.py`: Streamlit dashboard for this BRCA rerun

## Core data products

- `brca_model_performance_summary.csv`: Step4 model screening summary
- `brca_directive_ensemble_validation_summary.csv`: Step5 ensemble comparison
- `brca_directive_top30_tiered_candidates.csv`: Step5 tiered Top30
- `step6_metabric_validation/brca_top15_metabric_validated.csv`: Step6 METABRIC Top15
- `step7_admet_22assay/brca_final15_after_admet.csv`: Step7 final15 after ADMET 22-assay

## Reproduction commands

1. `python3 scripts/extract_brca_step4_summary.py`
2. `python3 scripts/run_brca_directive_ensemble.py`
3. `python3 scripts/classify_brca_top30_tiers.py`
4. `python3 scripts/run_brca_step6_metabric_adapter.py`
5. `python3 scripts/run_brca_step7_admet_adapter.py`
6. `python3 scripts/build_brca_repro_materials.py`
7. `streamlit run 20260428_new_BRCA_data/brca_repro_dashboard.py`
