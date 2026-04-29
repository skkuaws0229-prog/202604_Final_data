# CPTAC-STAD — omics, proteomics, and imaging (what to fetch, where, and size)

CPTAC-STAD (stomach adenocarcinoma) spans **multiple modalities**. None of these are a single `curl`-friendly file; expect **portal clients, manifests, and large transfers**.

## Quick comparison

| Modality | Typical portal | Order of magnitude | Notes |
|----------|----------------|-------------------|--------|
| **Radiology / pathology imaging** | [TCIA CPTAC-STAD](https://www.cancerimagingarchive.net/collection/cptac-stad/), [IDC](https://portal.imaging.datacommons.cancer.gov/explore/filters/?collection_id=cptac_stad) | **~1 TB+** for a full public imaging collection | Main **volume** bottleneck. TCIA **Data Retriever** + **Aspera**; not practical to mirror entirely without dedicated storage. |
| **Proteomics / phosphoproteomics** | [PDC](https://pdc.cancer.gov/pdc/browse/filters/program_name:CPTAC&disease_type:Stomach%20Adenocarcinoma) | Often **tens of GB** depending on study depth | Usually smaller than full imaging; still large. Use PDC manifest / API, download only needed assays. |
| **Genomics (WGS/WES/RNA-seq)** | [GDC CPTAC-3](https://portal.gdc.cancer.gov/projects/CPTAC-3) | Variable (**GB scale** common) | Overlaps conceptually with TCGA-STAD for some questions; pick cohort + file types deliberately. |

## Is “capacity” only an imaging problem?

**No — but imaging is usually the worst case.** Proteomics and aligned BAMs can also reach **many GB**. The reason `Stad_raw/cptac_stad/` started with **documentation only** was to avoid committing the bucket to **hundreds of GB–TB** without an explicit team decision on **which files** and **which storage class** (e.g. S3 Intelligent-Tiering, Glacier).

## Recommended workflow (include omics + imaging intentionally)

1. **Define the validation question** (e.g. proteome vs radiomics vs survival linkage).
2. **PDC**: filter CPTAC + stomach adenocarcinoma → export a **file manifest** → download a **subset** (e.g. one proteome + PSM summary tables first).
3. **GDC**: filter CPTAC-3 case/file metadata → download **gene expression / somatic mutation** tables before raw BAMs.
4. **TCIA / IDC**: choose **series or cases** (not the whole collection) → download via **TCIA Data Retriever** or IDC tooling → `aws s3 sync` into `s3://say2-4team/Stad_raw/cptac_stad/...` under a clear subprefix (`imaging/`, `omics/`, etc.).

## Official links

- **TCIA collection:** https://www.cancerimagingarchive.net/collection/cptac-stad/ — DOI https://doi.org/10.7937/jw9a-8k71  
- **TCIA download guide:** https://wiki.cancerimagingarchive.net/display/NBIA/Downloading+TCIA+Images  
- **IDC (DICOM in cloud):** https://portal.imaging.datacommons.cancer.gov/explore/filters/?collection_id=cptac_stad  
- **PDC (proteomics):** https://pdc.cancer.gov/pdc/browse/filters/program_name:CPTAC&disease_type:Stomach%20Adenocarcinoma  
- **GDC project CPTAC-3:** https://portal.gdc.cancer.gov/projects/CPTAC-3  

## S3 layout suggestion (when you upload subsets)

```
Stad_raw/cptac_stad/
  README_CPTAC_STAD_ACCESS.md          # this file (copy)
  pdc_manifests/<YYYYMMDD>/            # generated: `scripts/fetch_pdc_cptac_stad_manifest.py` (filesPerStudy JSON + index)
  manifests/                           # optional: extra PDC/GDC JSON/TSV you curate by hand
  proteomics_pdc/                      # optional: subset downloads (mzML, PSM tables, …)
  genomics_gdc/                        # optional: subset downloads
  imaging_tcia/                        # optional: subset DICOM (can grow large)
```

Generated / maintained for: `20260421_new_pre_project_biso_STAD` — README upload via `scripts/sync_stad_geo_suppl_and_cptac_pointer.sh`; PDC manifests via `scripts/fetch_pdc_cptac_stad_manifest.py`.
