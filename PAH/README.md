# PAH Drug Repurposing - Final Data for DB/Frontend

## Overview
- Disease: Pulmonary Arterial Hypertension (PAH)
- Purpose: final result data for Neo4j, Vector DB, and FastAPI/frontend integration
- Pipeline: v1.0 ln(IC50), 2A/2B Boosting 3-Ensemble + reused OSIC CT-CLIP image modal
- Date: 2026-05-05 to 2026-05-06

## Directory Guide

### 0.Image_modal_PAH/
Reused OSIC CT-CLIP image-modal outputs plus PAH-specific cluster-drug MoA hypothesis mapping.

### 1.Drug_results/
Core PAH drug recommendation tables.
- pah_final_11_tiered.csv: final ADMET-filtered PAH candidates
- pah_top30_clinical_reranked.csv: deduplicated clinical-augmented Top30
- pah_admet_22assay_results.csv: 22-assay ADMET prediction table
- pah_clinical_drug_rank_lookup.csv: PAH approved/reference drug rank lookup

### 2.External_validation/
Held-out GSE15197 PAH external validation outputs.

### 3.Model_metadata/
Model performance, ensemble metadata, and PAH drug-target mapping files.

### 4.Cluster_drug_mapping/
PAH CT-CLIP cluster-drug stratification hypothesis.

## Key Results
- External validation 2B ensemble Spearman: 0.939
- Train Top30 vs EV Top30 overlap: Jaccard 1.000
- Final ADMET candidates: 11
- Tier composition: Tier1 9, Tier2 1, Tier4 1
- Image modal: OSIC K=2 clusters reused; PAH mapping is MoA-based hypothesis only

## Caveats
- PAH cohort size is small compared with IPF.
- Riociguat and treprostinil were not present in the small-molecule IC50 pipeline.
- OSIC CT is not PAH-specific; image modal mapping is not direct drug-response validation.
