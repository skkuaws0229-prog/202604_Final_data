# 20260428_colon_v2 external validation raw check and collection report

## PRISM_raw
- local_found: False
- files:
  - 20260428_colon_v2_prism-repurposing-20q2-primary-screen-cell-line-info.csv
  - 20260428_colon_v2_prism-repurposing-20q2-primary-screen-replicate-collapsed-treatment-info.csv

## COSMIC_raw
- local_found: True
- source: copied from local backup snapshot
- files:
  - 20260428_colon_v2_Cosmic_CancerGeneCensus_v103_GRCh38.tsv.gz
  - 20260428_colon_v2_Cosmic_MutantCensus_v103_GRCh38.tsv.gz

## CPTAC_expression_raw
- local_found: False
- files:
  - 20260428_colon_v2_data_clinical_patient.txt
  - 20260428_colon_v2_data_mrna_seq_v2_rsem.txt

## GEO_GSE39582_matrix_probe_raw
- local_found: False
- files:
  - 20260428_colon_v2_GPL570.annot.gz
  - 20260428_colon_v2_GSE39582_series_matrix.txt.gz

## Notes
- PRISM required files were downloaded from Figshare article 20564034.
- COSMIC raw was not available in active colon workspace; copied existing local raw files from backup path without modification.
- CPTAC tarball endpoints returned invalid tiny files; instead downloaded expression and clinical text files directly from cBioPortal datahub media URLs.
- GEO matrix and GPL570 annotation were downloaded; annotation file uses GPL570.annot.gz as probe-map source.