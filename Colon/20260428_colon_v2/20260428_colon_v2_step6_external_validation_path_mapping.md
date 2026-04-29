# 20260428_colon_v2 Step6 External Validation Path Mapping

## Base Prefix (S3)
- `s3://say2-4team/20260408_new_pre_project_biso/20260428_colon_v2_external_validation_inputs/`

## Local Base (recommended)
- `20260420_new_pre_project_biso_Colon/curated_data/`

---

## 1) Script-to-Data Mapping

### `scripts/step6_2_prism_validation.py`
- **Use from S3**
  - `.../prism/prism-repurposing-20q2-primary-screen-cell-line-info.csv`
  - `.../prism/prism-repurposing-20q2-primary-screen-replicate-collapsed-treatment-info.csv`
  - (optional for deeper checks) `.../prism/*secondary*`
- **Sync to local**
  - `curated_data/validation/prism/`

### `scripts/step6_3_clinical_trials_validation.py`
- **Use from S3**
  - `.../clinicaltrials/clinicaltrials_liver_cancer_page_001.json` ... `006.json`
  - `.../clinicaltrials/clinicaltrials_liver_cancer_summary.json`
- **Sync to local**
  - `curated_data/validation/clinicaltrials/`
- **Note**
  - 파일명은 liver지만 JSON 구조는 재사용 가능. 실행 시 disease/query 파라미터는 CRC로 맞추는 것을 권장.

### `scripts/step6_4_cosmic_validation.py`
- **Use from S3**
  - `.../cosmic/Cosmic_CancerGeneCensus_Tsv_v103_GRCh38.tar`
  - `.../cosmic/Cosmic_MutantCensus_Tsv_v103_GRCh38.tar`
  - `.../cosmic/Cosmic_Classification_Tsv_v103_GRCh38.tar`
  - `.../cosmic/Actionability_AllData_Tsv_v19_GRCh37.tar`
- **Sync to local**
  - `curated_data/validation/cosmic/`

### `scripts/step6_5_cptac_validation.py`
- **Use from S3**
  - `.../cptac/coad_cptac_2019/data_clinical_patient.txt`
  - `.../cptac/coad_cptac_2019/data_mrna_seq_v2_rsem.txt`
  - (optional) `data_mrna_seq_v2_rsem_zscores_ref_all_samples.txt`
- **Sync to local**
  - `curated_data/cbioportal/coad_cptac_2019/` (or script expected path에 맞춰 `curated_data/cptac/coad_cptac_2019/`)

### `scripts/step6_geo_validation.py`
- **Use from S3**
  - `.../geo/GSE39582/matrix/GSE39582_series_matrix.txt.gz`
  - `.../geo/GSE39582/metadata/GSE39582_family.soft.gz`
- **Sync to local**
  - `curated_data/geo/GSE39582/matrix/`
  - `curated_data/geo/GSE39582/metadata/`

---

## 2) One-time Sync Commands (S3 -> Local)

```bash
cd /Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest-1/20260420_new_pre_project_biso_Colon

mkdir -p curated_data/validation/prism
mkdir -p curated_data/validation/clinicaltrials
mkdir -p curated_data/validation/cosmic
mkdir -p curated_data/cbioportal/coad_cptac_2019
mkdir -p curated_data/geo/GSE39582/matrix
mkdir -p curated_data/geo/GSE39582/metadata

aws s3 cp --recursive "s3://say2-4team/20260408_new_pre_project_biso/20260428_colon_v2_external_validation_inputs/prism/" "curated_data/validation/prism/"
aws s3 cp --recursive "s3://say2-4team/20260408_new_pre_project_biso/20260428_colon_v2_external_validation_inputs/clinicaltrials/" "curated_data/validation/clinicaltrials/"
aws s3 cp --recursive "s3://say2-4team/20260408_new_pre_project_biso/20260428_colon_v2_external_validation_inputs/cosmic/" "curated_data/validation/cosmic/"
aws s3 cp --recursive "s3://say2-4team/20260408_new_pre_project_biso/20260428_colon_v2_external_validation_inputs/cptac/coad_cptac_2019/" "curated_data/cbioportal/coad_cptac_2019/"
aws s3 cp --recursive "s3://say2-4team/20260408_new_pre_project_biso/20260428_colon_v2_external_validation_inputs/geo/GSE39582/" "curated_data/geo/GSE39582/"
```

---

## 3) Quick Integrity Checks

```bash
ls -lh curated_data/validation/prism | wc -l
ls -lh curated_data/validation/clinicaltrials | wc -l
ls -lh curated_data/validation/cosmic | wc -l
ls -lh curated_data/cbioportal/coad_cptac_2019 | wc -l
ls -lh curated_data/geo/GSE39582/matrix
ls -lh curated_data/geo/GSE39582/metadata
```

---

## 4) Expected Step6 Output Targets (for this run)

- `20260428_colon_v2_step6_prism_validation_results.json`
- `20260428_colon_v2_step6_clinical_trials_validation_results.json`
- `20260428_colon_v2_step6_cosmic_validation_results.json`
- `20260428_colon_v2_step6_cptac_validation_results.json`
- `20260428_colon_v2_step6_geo_validation_results.json`
- `20260428_colon_v2_step6_comprehensive_validation_results.json`

