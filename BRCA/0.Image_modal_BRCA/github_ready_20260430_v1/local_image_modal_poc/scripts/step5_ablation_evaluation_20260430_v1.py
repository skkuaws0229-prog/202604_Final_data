#!/usr/bin/env python3
"""
step5_ablation_evaluation_20260430_v1.py
========================================
Ablation 실험: 이미지 모달 추가에 따른 성능 비교.

목적:
  - Baseline (이미지 없음) vs +Image (mean pool) vs +Image (ABMIL) vs Image only
  - 각 조건별 Spearman ρ, RMSE, MAE, R² 비교
  - 비교 테이블 및 시각화 생성

사용법:
  python step5_ablation_evaluation_20260430_v1.py

입력:
  - 기존 파이프라인 예측값 (brca_directive_ensemble_B_holdout_predictions.csv)
  - Step 3 임베딩 (all_slide_embeddings_20260430_v1.parquet)
  - Step 4 Re-ranking 결과 (reranking_metrics_20260430_v1.json)

출력:
  - results/ablation/ablation_comparison_20260430_v1.csv
  - results/ablation/ablation_report_20260430_v1.md
  - results/ablation/ablation_chart_20260430_v1.png
  - logs/step5_ablation_20260430_v1.log

의존성:
  pip install pandas numpy scikit-learn lightgbm scipy matplotlib

작성일: 2026-04-30
버전: v1
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

try:
    import lightgbm as lgb
except ImportError:
    print("lightgbm이 필요합니다: pip install lightgbm")
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# ============================================================
# 설정
# ============================================================
PIPELINE_DATE = "20260430"
PIPELINE_VERSION = "v1"
PIPELINE_TAG = f"{PIPELINE_DATE}_{PIPELINE_VERSION}"

DEFAULT_WORK_ROOT = Path.home() / "20260415_preproject_choi_protocol_v1_bisotest" / \
    "20260415_preproject_choi_protocol_v1_bisotest" / \
    "20260430_multimodal_BRCA_v1" / f"image_modal_{PIPELINE_TAG}"

DEFAULT_EXISTING_ROOT = Path.home() / "20260415_preproject_choi_protocol_v1_bisotest" / \
    "20260415_preproject_choi_protocol_v1_bisotest" / \
    "20260430_multimodal_BRCA_v1" / "20260428_new_BRCA_data"

RANDOM_SEED = 42
CV_FOLDS = 5
EMBEDDING_DIM = 1024


def setup_logging(log_dir: Path) -> logging.Logger:
    """로깅 설정."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"step5_ablation_{PIPELINE_TAG}.log"

    logger = logging.getLogger(f"step5_{PIPELINE_TAG}")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def evaluate_model(X, y, model_params, cv_folds, logger, exp_name):
    """단일 ablation 조건에서 모델 학습 + CV 평가."""
    model = lgb.LGBMRegressor(**model_params)
    kf = KFold(n_splits=cv_folds, shuffle=True, random_state=RANDOM_SEED)
    cv_preds = cross_val_predict(model, X, y, cv=kf)

    spearman_rho, spearman_p = stats.spearmanr(y, cv_preds)
    rmse = np.sqrt(mean_squared_error(y, cv_preds))
    mae = mean_absolute_error(y, cv_preds)
    r2 = r2_score(y, cv_preds)

    metrics = {
        "experiment": exp_name,
        "spearman_rho": round(float(spearman_rho), 4),
        "spearman_p": float(spearman_p),
        "rmse": round(float(rmse), 4),
        "mae": round(float(mae), 4),
        "r_squared": round(float(r2), 4),
        "n_samples": len(y),
        "n_features": X.shape[1],
    }

    logger.info(
        f"  [{exp_name}] Spearman={metrics['spearman_rho']:.4f}, "
        f"RMSE={metrics['rmse']:.4f}, R²={metrics['r_squared']:.4f}"
    )

    return metrics


def run_ablation(
    holdout_df: pd.DataFrame,
    slide_embeddings: pd.DataFrame,
    cv_folds: int,
    logger: logging.Logger,
) -> list[dict]:
    """
    4가지 ablation 조건 실행.
    """
    logger.info("Ablation 실험 시작...")

    model_params = {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": RANDOM_SEED,
        "verbose": -1,
    }

    # 피처 컬럼 정의
    omic_pred_cols = ["ensemble_pred", "component_pred_std"]
    omic_pred_cols = [c for c in omic_pred_cols if c in holdout_df.columns]

    emb_cols = [c for c in slide_embeddings.columns if c.startswith("emb_")]

    # 타겟
    y = holdout_df["target"].values.astype(np.float32)

    # 이미지 임베딩 join (PoC: BRCA 대표 벡터)
    brca_mean_emb = slide_embeddings[emb_cols].mean().values
    emb_matrix = np.tile(brca_mean_emb, (len(holdout_df), 1)).astype(np.float32)

    results = []

    # ---- Experiment 1: Baseline (omic + drug, 이미지 없음) ----
    X_baseline = holdout_df[omic_pred_cols].values.astype(np.float32)
    results.append(evaluate_model(
        X_baseline, y, model_params, cv_folds, logger,
        "baseline_no_image"
    ))

    # ---- Experiment 2: +Image (mean pool) ----
    X_with_image = np.hstack([X_baseline, emb_matrix])
    results.append(evaluate_model(
        X_with_image, y, model_params, cv_folds, logger,
        "with_image_mean_pool"
    ))

    # ---- Experiment 3: +Image (ABMIL) — PoC에서는 mean과 동일 ----
    # ABMIL은 별도 학습이 필요하므로 Pilot에서는 mean pool과 동일하게 처리
    # 향후 ABMIL 학습 후 이 부분을 교체
    results.append(evaluate_model(
        X_with_image, y, model_params, cv_folds, logger,
        "with_image_abmil_placeholder"
    ))

    # ---- Experiment 4: Image only ----
    X_image_only = emb_matrix
    results.append(evaluate_model(
        X_image_only, y, model_params, cv_folds, logger,
        "image_only"
    ))

    return results


def plot_ablation_chart(
    results: list[dict],
    output_path: Path,
    logger: logging.Logger,
):
    """Ablation 결과 바 차트 생성."""
    if not HAS_MATPLOTLIB:
        logger.warning("matplotlib 없음, 차트 생성 스킵")
        return

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))

    experiments = [r["experiment"] for r in results]
    short_names = [
        "Baseline\n(no image)",
        "+Image\n(mean pool)",
        "+Image\n(ABMIL)",
        "Image\nonly",
    ]

    metrics_to_plot = [
        ("spearman_rho", "Spearman ρ", True),    # higher is better
        ("rmse", "RMSE", False),                   # lower is better
        ("mae", "MAE", False),                     # lower is better
        ("r_squared", "R²", True),                 # higher is better
    ]

    colors = ["#94a3b8", "#3b82f6", "#8b5cf6", "#ec4899"]

    for ax, (metric_key, metric_label, higher_better) in zip(axes, metrics_to_plot):
        values = [r[metric_key] for r in results]
        bars = ax.bar(range(len(values)), values, color=colors, edgecolor="white", linewidth=0.5)

        # 최적값 강조
        best_idx = np.argmax(values) if higher_better else np.argmin(values)
        bars[best_idx].set_edgecolor("#10b981")
        bars[best_idx].set_linewidth(2.5)

        ax.set_title(metric_label, fontsize=12, fontweight="bold")
        ax.set_xticks(range(len(short_names)))
        ax.set_xticklabels(short_names, fontsize=8)

        for i, v in enumerate(values):
            ax.text(i, v + 0.01 * max(values), f"{v:.4f}", ha="center", va="bottom", fontsize=8)

    fig.suptitle(
        f"Ablation Study — Image Modal Contribution ({PIPELINE_TAG})",
        fontsize=14, fontweight="bold", y=1.02
    )
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"차트 저장: {output_path}")


def generate_ablation_report(
    results: list[dict],
    output_path: Path,
    logger: logging.Logger,
):
    """Ablation 실험 보고서 생성."""
    df = pd.DataFrame(results)

    # Baseline 대비 개선율 계산
    baseline = results[0]
    improvements = []
    for r in results:
        imp = {
            "experiment": r["experiment"],
            "spearman_delta": r["spearman_rho"] - baseline["spearman_rho"],
            "rmse_delta": r["rmse"] - baseline["rmse"],
            "r2_delta": r["r_squared"] - baseline["r_squared"],
        }
        improvements.append(imp)

    report = f"""# Ablation Study Report — {PIPELINE_TAG}

## 개요
이미지 모달(WSI embedding)이 약물 감수성 예측에 기여하는지 확인하기 위한
ablation 실험 결과.

생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 실험 조건

| # | 실험 | 피처 구성 | 피처 수 |
|---|------|----------|--------|
| 1 | Baseline (no image) | ensemble_pred + pred_std | {results[0]['n_features']} |
| 2 | +Image (mean pool) | ensemble_pred + pred_std + slide_emb(1024d) | {results[1]['n_features']} |
| 3 | +Image (ABMIL) | (placeholder — pilot에서는 mean과 동일) | {results[2]['n_features']} |
| 4 | Image only | slide_emb(1024d) only | {results[3]['n_features']} |

## 결과 비교 ({CV_FOLDS}-fold CV)

| 실험 | Spearman ρ | RMSE | MAE | R² |
|------|-----------|------|-----|-----|
"""
    for r in results:
        report += (
            f"| {r['experiment']} | {r['spearman_rho']:.4f} | "
            f"{r['rmse']:.4f} | {r['mae']:.4f} | {r['r_squared']:.4f} |\n"
        )

    report += f"""
## Baseline 대비 변화

| 실험 | Spearman Δ | RMSE Δ | R² Δ |
|------|-----------|--------|------|
"""
    for imp in improvements:
        sp_sign = "+" if imp["spearman_delta"] >= 0 else ""
        rmse_sign = "+" if imp["rmse_delta"] >= 0 else ""
        r2_sign = "+" if imp["r2_delta"] >= 0 else ""
        report += (
            f"| {imp['experiment']} | {sp_sign}{imp['spearman_delta']:.4f} | "
            f"{rmse_sign}{imp['rmse_delta']:.4f} | {r2_sign}{imp['r2_delta']:.4f} |\n"
        )

    report += f"""
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
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info(f"보고서 저장: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description=f"Step 5: Ablation 실험 ({PIPELINE_TAG})"
    )
    parser.add_argument(
        "--work-root", type=str, default=str(DEFAULT_WORK_ROOT),
    )
    parser.add_argument(
        "--existing-root", type=str, default=str(DEFAULT_EXISTING_ROOT),
    )
    parser.add_argument(
        "--cv-folds", type=int, default=CV_FOLDS,
    )
    args = parser.parse_args()

    work_root = Path(args.work_root)
    existing_root = Path(args.existing_root)
    ablation_dir = work_root / "results" / "ablation"
    log_dir = work_root / "logs"

    ablation_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(log_dir)
    logger.info("=" * 60)
    logger.info(f"Step 5: Ablation 실험 시작 ({PIPELINE_TAG})")
    logger.info("=" * 60)

    # 데이터 로드
    holdout_path = existing_root / "brca_directive_ensemble_B_holdout_predictions.csv"
    holdout_df = pd.read_csv(holdout_path)
    logger.info(f"홀드아웃 데이터: {len(holdout_df)} 행")

    emb_path = work_root / "data" / "slide_embeddings" / f"all_slide_embeddings_{PIPELINE_TAG}.parquet"
    if emb_path.exists():
        slide_embeddings = pd.read_parquet(emb_path)
        logger.info(f"슬라이드 임베딩: {len(slide_embeddings)}개")
    else:
        logger.warning(f"슬라이드 임베딩 없음: {emb_path}")
        logger.info("Step 3을 먼저 실행하세요. 임시 랜덤 임베딩으로 진행합니다.")
        # 임시 랜덤 임베딩 (구조 테스트용)
        np.random.seed(RANDOM_SEED)
        n_slides = 50
        data = {"slide_id": [f"slide_{i}" for i in range(n_slides)]}
        for j in range(EMBEDDING_DIM):
            data[f"emb_{j}"] = np.random.randn(n_slides).tolist()
        slide_embeddings = pd.DataFrame(data)

    # Ablation 실행
    results = run_ablation(holdout_df, slide_embeddings, args.cv_folds, logger)

    # 결과 저장
    comparison_path = ablation_dir / f"ablation_comparison_{PIPELINE_TAG}.csv"
    pd.DataFrame(results).to_csv(comparison_path, index=False)
    logger.info(f"비교 테이블 저장: {comparison_path}")

    # 차트 생성
    chart_path = ablation_dir / f"ablation_chart_{PIPELINE_TAG}.png"
    plot_ablation_chart(results, chart_path, logger)

    # 보고서 생성
    report_path = ablation_dir / f"ablation_report_{PIPELINE_TAG}.md"
    generate_ablation_report(results, report_path, logger)

    logger.info("\n" + "=" * 60)
    logger.info(f"Step 5 Ablation 실험 완료 ({PIPELINE_TAG})")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
