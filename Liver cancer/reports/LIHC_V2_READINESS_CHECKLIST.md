# LIHC v2 Readiness Checklist

## Goal
Start formal v2 flow from candidate-pool expansion before Step4 scoring.

## Current Check Status
- Candidate pool build script: `scripts/build_v2_candidate_pool_lihc.py` (READY)
- Candidate pool artifact: `results/lihc_candidate_pool_v2.csv` (READY)
- Top50 proxy artifact: `results/lihc_top50_candidate_pre_step4_v2.csv` (READY)
- Summary artifact: `results/lihc_v2_candidate_pool_summary.json` (READY)

## Findings
- Candidate pool size: `243`
- HCC approved in pool: `1` (Sorafenib)
- Sorafenib proxy rank: `84` (not in proxy top50)

## Blockers for Full v2 Step4-5 Retrain
- Additional HCC approved drugs need to be added to upstream LIHC drug library.
- Protocol Step4 scripts must point to expanded v2 drug pool inputs.

## Next Actions
1. Expand LIHC standardized/model_input drug tables with HCC approved drug set.
2. Rebuild v2 feature table for Step4 scoring rows.
3. Re-run Step4/5 and regenerate Top30/Top50.
4. Re-run Step6/7 and update v2 dashboard/report/protocol.
