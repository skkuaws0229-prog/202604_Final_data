# BRCA Directive Ensemble Summary

- Directive source: `/Users/skku_aws2_14/Downloads/BRCA_ensemble_directive.md`
- Selection rule: higher GroupCV Spearman, then ScaffoldCV Spearman, then Holdout Spearman
- Final recommendation split: holdout predictions of the winning configuration
- Top30 dedup rule: same `drug_name` removed, highest-ranked one kept

## Validation

| Config | Eval Mode | Spearman | Pearson | RMSE | MAE | R2 | Mean Component Std | Rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | groupcv | 0.4834 | 0.5279 | 2.2362 | 1.6741 | 0.2744 | 0.5863 | 7730 |
| B | groupcv | 0.4826 | 0.5282 | 2.2310 | 1.6831 | 0.2778 | 0.4632 | 7730 |
| A | holdout | 0.7847 | 0.8439 | 1.4343 | 1.0936 | 0.6996 | 0.5433 | 1546 |
| B | holdout | 0.7878 | 0.8473 | 1.4259 | 1.0923 | 0.7031 | 0.4433 | 1546 |
| A | scaffoldcv | 0.3644 | 0.3289 | 2.6779 | 2.0128 | -0.0405 | 0.6769 | 7730 |
| B | scaffoldcv | 0.3622 | 0.3399 | 2.6321 | 1.9716 | -0.0052 | 0.5988 | 7730 |

## Winner

- Selected configuration: **A**

## Top 10 Preview

| Rank | Drug ID | Drug Name | Score | Pred Std | Grade |
| --- | ---: | --- | ---: | ---: | --- |
| 1 | 2438 | ascorbate (vitamin C) | 8.5058 | 1.0744 | C |
| 2 | 2499 | N-acetyl cysteine | 7.8483 | 0.9254 | C |
| 3 | 2439 | glutathione | 7.4384 | 0.5589 | A |
| 4 | 2498 | alpha-lipoic acid | 6.3771 | 0.7167 | B |
| 5 | 1375 | Temozolomide | 6.2014 | 0.6435 | B |
| 6 | 1815 | Dacarbazine | 5.6518 | 0.8832 | C |
| 7 | 1615 | CZC24832 | 5.5331 | 0.8068 | C |
| 8 | 1847 | BEN | 5.4729 | 1.1110 | C |
| 9 | 1089 | Oxaliplatin | 5.3569 | 0.4956 | A |
| 10 | 1813 | Fludarabine | 5.1769 | 0.8098 | C |
