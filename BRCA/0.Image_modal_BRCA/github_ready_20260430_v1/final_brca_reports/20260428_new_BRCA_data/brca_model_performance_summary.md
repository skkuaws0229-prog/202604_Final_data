# BRCA Step4 Model Performance Summary

- Source: latest BRCA results from `20260424_multicancer_stad_protocol_rerun`
- Note: latest artifacts expose `cv` as 3-fold (`cv_fold1~3`), not a separate `5foldcv` artifact
- Overfit gap = `train_spearman - test_spearman`; lower is better
- Summary sort = `generalization_mean` desc, then `groupcv_spearman` desc, then `primary_overfit_gap` asc

## 2A

| Family | Model | CV Spearman | GroupCV Spearman | ScaffoldCV Spearman | Overfit Gap (GroupCV) | Mean(Group+Scaffold) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| ML | CatBoost | 0.2499 | 0.2637 | 0.2591 | 0.0068 | 0.2614 |
| ML | XGBoost | 0.2452 | 0.2636 | 0.2582 | 0.0091 | 0.2609 |
| ML | ElasticNet | 0.2497 | 0.2631 | 0.2581 | 0.0052 | 0.2606 |
| ML | LightGBM | 0.2445 | 0.2637 | 0.2573 | 0.0086 | 0.2605 |
| Graph | GAT | 0.2501 | 0.2630 | 0.2580 | 0.0052 | 0.2605 |
| ML | ExtraTrees | 0.2441 | 0.2635 | 0.2573 | 0.0090 | 0.2604 |
| Graph | GraphSAGE | 0.2502 | 0.2627 | 0.2580 | 0.0056 | 0.2603 |
| ML | RandomForest | 0.2432 | 0.2626 | 0.2575 | 0.0099 | 0.2600 |
| DL | FlatMLP | 0.2468 | 0.2631 | 0.2555 | 0.0014 | 0.2593 |
| DL | CrossAttention | 0.2453 | 0.2615 | 0.2545 | 0.0023 | 0.2580 |
| DL | WideDeep | 0.2483 | 0.2632 | 0.2525 | 0.0011 | 0.2578 |
| DL | ResidualMLP | 0.2459 | 0.2612 | 0.2538 | 0.0025 | 0.2575 |
| DL | TabNet | 0.2403 | 0.2491 | 0.2487 | 0.0016 | 0.2489 |
| DL | TabTransformer | 0.2128 | 0.2158 | 0.2160 | 0.0086 | 0.2159 |
| DL | FTTransformer | 0.2160 | 0.2086 | 0.2201 | 0.0005 | 0.2144 |

## 2B

| Family | Model | CV Spearman | GroupCV Spearman | ScaffoldCV Spearman | Overfit Gap (GroupCV) | Mean(Group+Scaffold) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| ML | ElasticNet | NA | NA | NA | NA | NA |
| DL | ResidualMLP | 0.7514 | 0.4319 | 0.3776 | 0.3575 | 0.4047 |
| ML | CatBoost | 0.6967 | 0.4212 | 0.3828 | 0.3215 | 0.4020 |
| DL | CrossAttention | 0.7620 | 0.4013 | 0.3728 | 0.3707 | 0.3871 |
| DL | WideDeep | 0.7411 | 0.4085 | 0.3596 | 0.3762 | 0.3841 |
| ML | LightGBM | 0.7505 | 0.4176 | 0.3488 | 0.3860 | 0.3832 |
| ML | RandomForest | 0.7699 | 0.4329 | 0.3329 | 0.4664 | 0.3829 |
| ML | XGBoost | 0.7418 | 0.4147 | 0.3378 | 0.3925 | 0.3762 |
| DL | FTTransformer | 0.7394 | 0.4043 | 0.3460 | 0.3520 | 0.3751 |
| DL | TabTransformer | 0.7486 | 0.3850 | 0.3614 | 0.3767 | 0.3732 |
| DL | FlatMLP | 0.7562 | 0.3792 | 0.3521 | 0.3867 | 0.3656 |
| DL | TabNet | 0.7582 | 0.3465 | 0.3317 | 0.4649 | 0.3391 |
| Graph | GraphSAGE | 0.7096 | 0.2954 | 0.3705 | 0.4450 | 0.3329 |
| ML | ExtraTrees | 0.7663 | 0.3289 | 0.3263 | 0.5853 | 0.3276 |
| Graph | GAT | 0.7664 | 0.2597 | 0.2821 | 0.5351 | 0.2709 |

## 2C

| Family | Model | CV Spearman | GroupCV Spearman | ScaffoldCV Spearman | Overfit Gap (GroupCV) | Mean(Group+Scaffold) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| ML | ElasticNet | NA | NA | NA | NA | NA |
| ML | CatBoost | 0.7108 | 0.4695 | 0.4157 | 0.2865 | 0.4426 |
| ML | LightGBM | 0.7615 | 0.4604 | 0.3925 | 0.3556 | 0.4264 |
| DL | ResidualMLP | 0.7645 | 0.4390 | 0.3876 | 0.3421 | 0.4133 |
| DL | WideDeep | 0.7530 | 0.4328 | 0.3847 | 0.3524 | 0.4088 |
| ML | RandomForest | 0.7761 | 0.4450 | 0.3617 | 0.4865 | 0.4033 |
| DL | FlatMLP | 0.7600 | 0.4218 | 0.3832 | 0.3653 | 0.4025 |
| DL | TabTransformer | 0.7552 | 0.4195 | 0.3855 | 0.3575 | 0.4025 |
| DL | FTTransformer | 0.7404 | 0.4269 | 0.3680 | 0.3372 | 0.3975 |
| ML | XGBoost | 0.7535 | 0.4601 | 0.3189 | 0.3592 | 0.3895 |
| DL | CrossAttention | 0.7605 | 0.3850 | 0.3774 | 0.3952 | 0.3812 |
| ML | ExtraTrees | 0.7629 | 0.3597 | 0.3566 | 0.5890 | 0.3582 |
| DL | TabNet | 0.7587 | 0.3584 | 0.3351 | 0.4641 | 0.3467 |
| Graph | GraphSAGE | 0.7397 | 0.2939 | 0.3562 | 0.4543 | 0.3250 |
| Graph | GAT | 0.7777 | 0.2669 | 0.3342 | 0.5396 | 0.3005 |
