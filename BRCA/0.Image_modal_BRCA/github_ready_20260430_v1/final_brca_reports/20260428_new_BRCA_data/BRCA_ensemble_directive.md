# BRCA (유방암) 앙상블 구성 지시서

## 1. 목적

유방암(BRCA) 모델 학습 결과(Phase 2A/2B/2C)를 기반으로, **일반화 성능(GroupCV/ScaffoldCV ρ)**과 **과적합 억제(gap 최소화)**를 동시에 달성하는 앙상블을 구성하여 약물 추천에 활용한다.

---

## 2. BRCA 데이터 특성 (이전 암종과의 차이)

BRCA는 이전 암종(PDAC)과 데이터 특성이 근본적으로 다르며, 앙상블 전략도 이에 맞게 조정되었다.

| 항목 | PDAC (이전 암종) | BRCA (유방암) |
|------|-----------------|--------------|
| Phase 2C 효과 | cv5만 상승, 일반화 하락 → **제외** | groupcv ρ 상승 + gap 감소 → **채택** |
| Phase 2A 유용성 | 일부 모델 활용 가능 | ρ ≈ 0.21~0.26, 전 모델 동급 → **제외** |
| ML vs DL 우위 | DL 우세 (DL 75%) | ML·DL 동급 (ML ≈ 47~55%) |
| 최고 모델 | MLP_3x512 (DL) | **CatBoost (ML)** |

### BRCA에서 Phase 2C가 유효한 근거

| 모델 | 2B groupcv ρ | 2C groupcv ρ | Δρ | 2B gap | 2C gap | Δgap |
|------|-------------|-------------|-----|--------|--------|------|
| CatBoost | 0.4212 | 0.4695 | **+0.0483** | 0.3215 | 0.2865 | **−0.0350** |
| XGBoost | 0.4147 | 0.4601 | **+0.0454** | 0.3925 | 0.3592 | **−0.0333** |
| LightGBM | 0.4176 | 0.4604 | **+0.0428** | 0.3860 | 0.3556 | **−0.0304** |
| ResidualMLP | 0.4319 | 0.4390 | +0.0071 | 0.3575 | 0.3421 | −0.0154 |
| WideDeep | 0.4085 | 0.4328 | +0.0243 | 0.3762 | 0.3524 | −0.0238 |
| FTTransformer | 0.4043 | 0.4269 | +0.0226 | 0.3520 | 0.3372 | −0.0148 |

→ 대부분의 모델에서 **ρ 상승과 gap 감소가 동시에** 발생하여, context 피처가 BRCA에서는 실제 유효한 정보를 제공함.

---

## 3. 최종 앙상블 구성

두 가지 안을 모두 validation에서 테스트한 후, GroupCV ρ가 높은 쪽을 최종 채택한다.

### 3.1 A안: 아키텍처 다양성 중심

5개 모델이 전부 서로 다른 아키텍처로 구성됨.

| 역할 | 모델 | Phase | 가중치 | 선정 근거 |
|------|------|-------|--------|----------|
| 메인 1 | CatBoost | 2C | **0.30** | 전체 1위, gen_mean=0.4426, gap=0.2865 |
| 메인 2 | ResidualMLP | 2C | **0.25** | DL 1위, gen_mean=0.4133, gap=0.3421 |
| 보조 1 | WideDeep | 2C | **0.20** | DL 2위, gen_mean=0.4088, gap=0.3524 |
| 보조 2 | LightGBM | 2C | **0.15** | ML 2위, gen_mean=0.4264, gap=0.3556 |
| 안정성 | FTTransformer | 2C | **0.10** | gap=0.3372 (DL 최소), Transformer 계열 다양성 |

```
최종 예측 = 0.30 × CatBoost_2C(x)
           + 0.25 × ResidualMLP_2C(x)
           + 0.20 × WideDeep_2C(x)
           + 0.15 × LightGBM_2C(x)
           + 0.10 × FTTransformer_2C(x)
```

**비율**: DL 55% (0.25 + 0.20 + 0.10) / ML 45% (0.30 + 0.15)

**장점**: 5개 모델 아키텍처가 모두 달라 예측 상관이 낮고, 앙상블 다양성이 극대화됨.

### 3.2 B안: Phase 다양성 중심

같은 모델(ResidualMLP)을 Phase 2C·2B로 나누어 Phase 다양성을 확보.

| 역할 | 모델 | Phase | 가중치 | 선정 근거 |
|------|------|-------|--------|----------|
| 메인 1 | CatBoost | 2C | **0.30** | 전체 1위, gen_mean=0.4426, gap=0.2865 |
| 메인 2 | ResidualMLP | 2C | **0.23** | DL 1위, gen_mean=0.4133, gap=0.3421 |
| 보조 1 | LightGBM | 2C | **0.17** | ML 2위, gen_mean=0.4264, gap=0.3556 |
| 보조 2 | WideDeep | 2C | **0.15** | DL 2위, gen_mean=0.4088, gap=0.3524 |
| Phase 보완 | ResidualMLP | 2B | **0.15** | 2B 안정 보조, gen_mean=0.4047, gap=0.3575 |

```
최종 예측 = 0.30 × CatBoost_2C(x)
           + 0.23 × ResidualMLP_2C(x)
           + 0.17 × LightGBM_2C(x)
           + 0.15 × WideDeep_2C(x)
           + 0.15 × ResidualMLP_2B(x)
```

**비율**: DL 53% (0.23 + 0.15 + 0.15) / ML 47% (0.30 + 0.17)

**장점**: 2B Phase가 포함되어 context 피처 과의존 리스크를 완화. ResidualMLP가 2B에서도 DL 최고(gen_mean=0.4047)이므로 수치적으로 정당화됨.

### 3.3 A안 vs B안 비교

| 비교 항목 | A안 | B안 |
|----------|-----|-----|
| 아키텍처 종류 | **5종** (모두 다름) | 4종 (ResidualMLP 중복) |
| Phase 종류 | 2C만 | **2C + 2B** |
| 다양성 방향 | 아키텍처 다양성 | Phase 다양성 |
| 2C 의존도 | 100% | **85%** (2B 15% 포함) |
| DL:ML | 55:45 | 53:47 |

→ **선택 기준**: Validation에서 GroupCV ρ를 비교하여 최종 결정.

---

## 4. 설계 원칙

### 4.1 Phase 선택 기준

- **Phase 2C 채택**: BRCA에서는 context 피처가 일반화를 실제 개선 (groupcv ρ 상승 + gap 감소 동시 달성).
- **Phase 2A 전면 제외**: 모든 모델 ρ ≈ 0.21~0.26으로 동급, 앙상블에 기여 불가.
- **Phase 2B는 보완 용도**: B안에서 Phase 다양성 확보 목적으로만 사용.

### 4.2 모델 제외 사유

| 제외 모델 | 사유 |
|----------|------|
| GAT | groupcv ρ=0.2669 (2C), gap=0.5396, 학습 불안정 |
| GraphSAGE | groupcv ρ=0.2939 (2C), fold std=0.114, 불안정 |
| TabNet | groupcv gap=0.4641 (2C), 과적합 심각 |
| ExtraTrees | groupcv gap=0.5890 (2C), 과적합 최악 |
| RandomForest | groupcv gap=0.4865 (2C), 과적합 심각 |
| XGBoost | scaffoldcv ρ=0.3189 (2C)로 급락, 불안정 |
| CrossAttention | groupcv ρ=0.3850 (2C), 2B→2C에서 오히려 하락 |
| TabTransformer | 성능 중위권, 상위 모델로 충분 |
| FlatMLP | 성능 중위권, ResidualMLP·WideDeep이 상위 |
| ElasticNet | 2B/2C 결과 없음 (학습 실패) |

### 4.3 다양성 확보 구조

**A안 다양성 매트릭스**

| 모델 | Family | 아키텍처 유형 | Phase |
|------|--------|-------------|-------|
| CatBoost | ML | Ordered GBDT | 2C |
| ResidualMLP | DL | Residual 연결 MLP | 2C |
| WideDeep | DL | Wide & Deep 이중 경로 | 2C |
| LightGBM | ML | Histogram GBDT | 2C |
| FTTransformer | DL | Feature Tokenizer + Transformer | 2C |

**B안 다양성 매트릭스**

| 모델 | Family | 아키텍처 유형 | Phase |
|------|--------|-------------|-------|
| CatBoost | ML | Ordered GBDT | 2C |
| ResidualMLP | DL | Residual 연결 MLP | 2C |
| LightGBM | ML | Histogram GBDT | 2C |
| WideDeep | DL | Wide & Deep 이중 경로 | 2C |
| ResidualMLP | DL | Residual 연결 MLP | 2B |

---

## 5. 앙상블 방법

### 5.1 기본 방식: 가중 평균 (Weighted Average)

A안 또는 B안의 가중치로 예측값을 가중 평균하여 최종 예측을 산출.

### 5.2 고급 방식: Stacking (선택 사항)

가중 평균으로 충분한 성능이 나오지 않을 경우 적용.

- **1층**: 선택된 5개 모델의 예측값 출력
- **2층 메타 러너**: Ridge Regression 또는 ElasticNet
- **핵심**: 메타 러너 학습 시 반드시 **GroupCV 또는 ScaffoldCV 분할** 사용 (CV5 사용 금지)

---

## 6. 약물 추천 적용

### 6.1 추천 기준

1. 앙상블 예측값 상위 N개 약물 선정
2. 예측 불확실성 필터링: 5개 모델 간 예측값 분산이 낮은 약물 우선 추천

### 6.2 신뢰도 등급

| 등급 | 조건 | 해석 |
|------|------|------|
| A (높음) | 5개 모델 모두 상위 예측 + 분산 낮음 | 강력 추천 |
| B (보통) | 다수 모델 상위 예측 + 분산 중간 | 조건부 추천 |
| C (낮음) | 모델 간 예측 불일치 + 분산 높음 | 추가 검증 필요 |

---

## 7. 검증 계획

1. **A안 vs B안 비교**: 두 구성 모두 GroupCV 기준으로 앙상블 ρ를 측정하여 최종 채택
2. **가중치 미세 조정**: Optuna 등으로 GroupCV 기준 최적 가중치 탐색
3. **Ablation 테스트**: 모델 1개씩 제거하며 각 모델의 기여도 확인
4. **개별 모델 대비 개선 확인**: 앙상블 ρ > 최고 단일 모델 ρ (CatBoost 2C groupcv ρ=0.4695) 달성 여부

---

## 8. 참고: 주요 수치 근거

### 8.1 앙상블 포함 모델 상세 수치

| 모델 | Phase | CV5 ρ | GroupCV ρ | ScaffoldCV ρ | CV gap | GroupCV gap | ScaffoldCV gap | Gen Mean |
|------|-------|-------|-----------|-------------|--------|------------|---------------|----------|
| CatBoost | 2C | 0.7108 | **0.4695** | **0.4157** | 0.0248 | **0.2865** | 0.3386 | **0.4426** |
| LightGBM | 2C | 0.7615 | 0.4604 | 0.3925 | 0.0431 | 0.3556 | 0.4230 | 0.4264 |
| ResidualMLP | 2C | 0.7645 | 0.4390 | 0.3876 | 0.0246 | 0.3421 | 0.4004 | 0.4133 |
| WideDeep | 2C | 0.7530 | 0.4328 | 0.3847 | 0.0213 | 0.3524 | 0.3980 | 0.4088 |
| FTTransformer | 2C | 0.7404 | 0.4269 | 0.3680 | 0.0199 | **0.3372** | 0.4061 | 0.3974 |
| ResidualMLP | 2B | 0.7514 | 0.4319 | 0.3776 | 0.0216 | 0.3575 | 0.4073 | 0.4047 |

### 8.2 PDAC vs BRCA 앙상블 비교

| 항목 | PDAC | BRCA |
|------|------|------|
| DL:ML 비율 | 75:25 | 53~55:45~47 |
| Phase 전략 | 2C 전면 제외, 2A/2B만 | **2C 중심**, 2B 보완 |
| 최고 모델 | MLP_3x512 (DL) | CatBoost (ML) |
| 앙상블 모델 수 | 5개 (중복 없음) | 5개 (A안: 중복 없음 / B안: ResidualMLP 2개) |
| Context 피처 | 과적합 유발 → 제외 | 일반화 개선 → 채택 |
