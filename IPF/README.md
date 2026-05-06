# IPF Drug Repurposing - Final Data for DB/Frontend

## Overview

- Disease: Idiopathic Pulmonary Fibrosis (IPF)
- Purpose: final result data for Neo4j, Vector DB, FastAPI, and frontend integration
- Pipeline: v1.0 ln(IC50), 2A Boosting 3-Ensemble, clean external validation, ADMET filtering, and CT-CLIP image modal
- Date: 2026-05-04 to 2026-05-05

## Directory Guide

### 0.Image_modal_IPF/

CT-CLIP image-modal outputs using OSIC pulmonary fibrosis CT data.

Key contents:
- `step_im2/ct_clip_embeddings_176.parquet`: CT-CLIP embeddings for 176 OSIC patients
- `step_im3/patient_clusters.csv`: K=2 patient cluster labels
- `step_im4a/`: clinical association results
- `step_im4b/`: FVC progression prediction validation
- `step_im4c/`: cluster-drug MoA stratification hypothesis
- `step_im5/`: integrated image-modal report and result archive

### 1.Drug_results/

Core IPF drug recommendation tables for application/database use.

Key contents:
- `ipf_final_15_tiered.csv`: final 15 candidate drugs with tier classification
- `ipf_top30_clinical_reranked.csv`: clinical-augmented Top30 list
- `ipf_admet_22assay_results.csv`: full ADMET 22-assay prediction table
- `ipf_admet_hard_fail_summary.csv`: ADMET hard-fail summary
- `ipf_reference_drugs.csv`: IPF-related reference drugs not present in the modeling pipeline
- `ipf_clinical_drug_rank_lookup.csv`: clinical/reference drug rank lookup

### 2.External_validation/

Held-out external validation outputs using GSE110147 and GSE150910.

Key contents:
- `ev_performance_summary.csv`
- `ev_drug_ranking_GSE110147.csv`
- `ev_drug_ranking_GSE150910.csv`
- `ev_top30_overlap.json`
- `ev_report.md`

### 3.Model_metadata/

Model and drug-target metadata.

Key contents:
- `ensemble_weights.json`
- `ipf_pipeline_protocol_20260504.md`
- `drug_target_summary.csv`
- `drug_target_pairs.csv`

### 4.Cluster_drug_mapping/

Image cluster to drug MoA hypothesis mapping.

Key contents:
- `im4c_cluster_drug_mapping.csv`
- `im4c_stratification_hypothesis.md`

## Key Results

- External validation Spearman: approximately 0.94
- Final candidates: 15 drugs
- Tier composition: Tier1 1, Tier2 7, Tier4 7
- Image clusters: K=2, preserved-FVC vs fibrotic pattern
- ADMET: 22-assay QSAR filtering with clinical-context handling for approved drugs

## Caveats

- ADMET values are QSAR predictions, not experimental measurements.
- GEO expression cohorts and OSIC CT patients are not the same individuals.
- Image-modal cluster-drug mapping is a MoA-based hypothesis, not direct drug-response validation.
- Model Top20 showed JAK1-heavy enrichment, so clinical maturity and ADMET filters were used for final prioritization.
