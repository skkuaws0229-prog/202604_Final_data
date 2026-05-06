# BRCA Step0~7 Dataset Readiness (v1)

- Checked at: 2026-04-29
- Local target folder: `20260430_multimodal_BRCA_v1`
- Policy: source files are not modified/deleted; copied from S3 only.

## Step-wise readiness summary

| Step | Dataset readiness | Evidence |
|---|---|---|
| Step0 (preflight) | PASS | AWS identity ok, BRCA base S3 prefix reachable |
| Step1~3 (upstream multimodal inputs) | PASS | `20260415_preproject_protocol_choi/data/` synced |
| Step4 (model summary/input assets) | PASS | `20260428_new_BRCA_data/` + rerun result bundle synced |
| Step5 (ensemble) | PASS | Step5 source/result files present under BRCA bundle |
| Step6 (METABRIC) | PASS | METABRIC expression/clinical parquet present |
| Step7 (ADMET 22 assay) | PASS | ADMET assay directory synced with full assay set |

## Copied dataset roots (S3 -> Local)

1. `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260428_new_BRCA_data/`  
   -> `20260430_multimodal_BRCA_v1/20260428_new_BRCA_data/`  
   - files: `304`

2. `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/scripts/`  
   -> `20260430_multimodal_BRCA_v1/scripts/`  
   - files: `7`

3. `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_protocol_choi/data/`  
   -> `20260430_multimodal_BRCA_v1/20260415_preproject_protocol_choi/data/`  
   - files: `17`

4. `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/`  
   -> `20260430_multimodal_BRCA_v1/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/`  
   - files: `6391` (S3 current count)

5. `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/curated_data/admet/tdc_admet_group/admet_group/`  
   -> `20260430_multimodal_BRCA_v1/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/curated_data/admet/tdc_admet_group/admet_group/`  
   - files: `44` (22 assay structure)

## Validation totals

- Total copied files: `6763`
- Total copied bytes: `3860958192`

## Notes

- Previous manifest had `6387` files for rerun result bundle, but current S3 has `6391`.  
  Local copy matches the current S3 count (`6391`).
- No pipeline execution was performed in this task; only dataset readiness check and copy.
