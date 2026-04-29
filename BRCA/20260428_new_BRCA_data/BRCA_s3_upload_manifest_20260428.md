# BRCA S3 Upload Manifest

- S3 prefix: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/`
- Purpose: store all BRCA deliverables plus the exact data dependencies required to rerun Step4 -> Step7 from the protocol.
- Included roots: `5`
- Total files: `6757`
- Total bytes: `3860872976`

## Included Roots

| Relative Root | Files | Bytes | S3 Prefix |
| --- | ---: | ---: | --- |
| `20260428_new_BRCA_data` | 302 | 15141986 | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260428_new_BRCA_data/` |
| `scripts` | 7 | 90222 | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/scripts/` |
| `20260415_preproject_protocol_choi/data` | 17 | 839236219 | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_protocol_choi/data/` |
| `20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun` | 6387 | 3000975908 | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/` |
| `20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/curated_data/admet/tdc_admet_group/admet_group` | 44 | 5428641 | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/curated_data/admet/tdc_admet_group/admet_group/` |

## Notes

- These paths are uploaded with workspace-relative structure preserved.
- If downloaded back under the same workspace root, the current BRCA reproduction scripts can be executed without changing hard-coded relative paths.
- `20260428_new_BRCA_data` includes the protocol, report, dashboard, manifests, Top30/Top15 outputs, and validation summaries.
- `scripts` includes the BRCA rerun scripts used for Step4, Step5, Step6, Step7, reporting, and S3 manifest generation.
- `20260415_preproject_protocol_choi/data` includes BRCA model inputs, drug catalog, and METABRIC parquet files.
- `results/20260424_multicancer_stad_protocol_rerun` is required because Step4 and Step5 scripts read the original step4 metrics/predictions from there.
- `curated_data/admet/tdc_admet_group/admet_group` is required because Step7 reads the 22-assay ADMET reference library from there.
