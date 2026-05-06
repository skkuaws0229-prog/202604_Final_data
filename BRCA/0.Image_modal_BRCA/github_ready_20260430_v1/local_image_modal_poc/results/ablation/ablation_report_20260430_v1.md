# Ablation Study Report — 20260430_v1

## 개요
이미지 모달(WSI embedding)이 약물 감수성 예측에 기여하는지 확인하기 위한
ablation 실험 결과.

생성일: 2026-04-30 09:50:50

## 실험 조건

| # | 실험 | 피처 구성 | 피처 수 |
|---|------|----------|--------|
| 1 | Baseline (no image) | ensemble_pred + pred_std | 2 |
| 2 | +Image (mean pool) | ensemble_pred + pred_std + slide_emb(1024d) | 1026 |
| 3 | +Image (ABMIL) | (placeholder — pilot에서는 mean과 동일) | 1026 |
| 4 | Image only | slide_emb(1024d) only | 1024 |

## 결과 비교 (5-fold CV)

| 실험 | Spearman ρ | RMSE | MAE | R² |
|------|-----------|------|-----|-----|
| baseline_no_image | 0.7498 | 1.4580 | 1.0903 | 0.6896 |
| with_image_mean_pool | 0.7498 | 1.4580 | 1.0903 | 0.6896 |
| with_image_abmil_placeholder | 0.7498 | 1.4580 | 1.0903 | 0.6896 |
| image_only | -0.0208 | 2.6174 | 1.9890 | -0.0003 |

## Baseline 대비 변화

| 실험 | Spearman Δ | RMSE Δ | R² Δ |
|------|-----------|--------|------|
| baseline_no_image | +0.0000 | +0.0000 | +0.0000 |
| with_image_mean_pool | +0.0000 | +0.0000 | +0.0000 |
| with_image_abmil_placeholder | +0.0000 | +0.0000 | +0.0000 |
| image_only | -0.7706 | +1.1594 | -0.6899 |

## 판단 기준

- **이미지 유지 조건**: +Image가 Baseline 대비 Spearman ρ 0.01 이상 개선
- **이미지 제외 조건**: 개선 없거나 RMSE 악화 시 이미지 모달 제외
- **ABMIL 고도화 조건**: mean pool로 효과 확인 시 ABMIL 학습 진행

## 다음 단계

- 이미지 기여도가 확인되면 → Step 6 (Top 30 재선정 + METABRIC 외부 검증)
- 기여도 미확인 시 → 다른 모달(단백질 구조, CT 등) 또는 피처 엔지니어링 재검토

## 주의사항 (Pilot PoC)

- 현재 BRCA 슬라이드 50장의 **평균 임베딩**을 암종 대표 벡터로 사용
- 셀라인별 개별 슬라이드가 아닌 공통 벡터이므로, 이미지의 **환자별 변이** 정보는 반영되지 않음
- 전체 확장(Phase 2) 시 환자별 개별 임베딩으로 전환하면 실제 기여도를 정확히 측정 가능
