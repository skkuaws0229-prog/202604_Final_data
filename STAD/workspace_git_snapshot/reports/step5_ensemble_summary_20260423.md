# STAD Step5 Ensemble Summary

- 문서 버전: `v2026.04.23-r1`
- 작성일: `2026-04-23`
- 기준 산출물: `results/20260422_stad_step4_v2/ensemble_catboost_dl_graph_groupcv.json`
- 실행 스크립트: `scripts/run_ensemble_catboost_dl_graph_stad.py`
- 평가 모드: `groupcv`

## 정책

- Step 4: 단일 모델 학습/평가(ML, DL, Graph)
- Step 5: 앙상블 전용
  - ML 슬롯 고정: `CatBoost`
  - Graph 슬롯 고정: `GraphSAGE`
  - DL 슬롯: phase별 OOF Spearman 상위 모델 자동 선택
  - 블렌드: Simple / JSON Spearman 가중 / GridOpt(3-weight grid)

## Phase별 결과 요약

| Phase | Models (ML + DL + Graph) | Best Single ρ | Simple ρ | Weighted ρ | GridOpt ρ | GridOpt Gain |
| --- | --- | ---:| ---:| ---:| ---:| ---:|
| 2A | CatBoost + DL_MLP_ResidualStyle + GraphSAGE | 0.4969 | 0.5127 | 0.5143 | **0.5153** | +0.0184 |
| 2B | CatBoost + DL_MLP_3x512 + GraphSAGE | 0.5001 | 0.5092 | 0.5115 | **0.5143** | +0.0142 |
| 2C | CatBoost + DL_MLP_ResidualStyle + GraphSAGE | 0.4963 | 0.5079 | 0.5087 | **0.5130** | +0.0166 |

## Diversity/Complementarity 해석

- `pred_pairwise_rho_mean` (기존 diversity): 약 `0.654`, `0.665`, `0.729` (2A~2C)
- `complementarity_1_minus_rho`: 약 `0.346`, `0.335`, `0.271`

해석:
- diversity 필드는 예측쌍 Spearman 평균(ρ)이므로, 값이 높을수록 모델 예측 패턴이 유사함.
- 보완적 다양성은 `1 - rho`로 보는 것이 직관적이며, 본 실험은 중간~낮은 보완성을 보임.
- 그럼에도 3개 phase 모두 블렌드 gain이 양수이므로 Step5 적용은 타당.

## 대시보드 반영 상태

- `stad_dashboard/app.py`
  - Step 4: 모델 학습/평가 전용(최고 성능 카드 포함)
  - Step 5: 앙상블 전용(표 1~3, 가중치, 차트, JSON 다운로드)

## 다음 업데이트 시 규칙

- 본 보고서 업데이트 시 반드시 다음 메타를 유지:
  - 문서 버전
  - 작성일/수정일
  - 기준 result_tag / run_id / eval_mode

