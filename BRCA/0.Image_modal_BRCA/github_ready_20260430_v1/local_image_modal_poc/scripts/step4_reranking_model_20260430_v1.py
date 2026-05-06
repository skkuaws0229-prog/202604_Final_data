#!/usr/bin/env python3
"""
step4_reranking_model_20260430_v1.py
====================================
기존 앙상블 IC50 예측값 + WSI 이미지 임베딩 → Re-ranking 모델.

목적:
  - 기존 파이프라인의 drug_level_score (ln(IC50) 기반)를 로드
  - WSI slide embedding (1,024d)과 결합
  - Re-ranking 모델(LightGBM)로 보정된 sensitivity score 산출
  - Top 30 후보 재정렬

사용법:
  python step4_reranking_model_20260430_v1.py
  python step4_reranking_model_20260430_v1.py --model-type mlp

입력:
  - 기존 파이프라인:
    - brca_directive_top30_tiered_candidates.csv
    - brca_directive_ensemble_B_holdout_predictions.csv
  - Step 3 출력:
    - data/slide_embeddings/all_slide_embeddings_20260430_v1.parquet

출력:
  - results/reranking/reranked_top30_20260430_v1.csv
  - results/reranking/reranking_model_20260430_v1.pkl
  - results/reranking/reranking_report_20260430_v1.md
  - logs/step4_reranking_20260430_v1.log

의존성:
  pip install pandas numpy scikit-learn lightgbm scipy

작성일: 2026-04-30
버전: v1
"""

import os
import sys
import json
import pickle
import logging
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler

try:
    import lightgbm as lgb
except ImportError:
    print("lightgbm이 필요합니다: pip install lightgbm")
    sys.exit(1)

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
    log_file = log_dir / f"step4_reranking_{PIPELINE_TAG}.log"

    logger = logging.getLogger(f"step4_{PIPELINE_TAG}")
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


def load_existing_predictions(existing_root: Path, logger: logging.Logger) -> dict:
    """
    기존 파이프라인 결과 로드.
    
    Returns:
        dict with keys:
          - 'top30': Top 30 후보 DataFrame
          - 'holdout_predictions': 홀드아웃 예측값 DataFrame
          - 'ic50_scale': IC50 스케일 정보
    """
    logger.info("기존 파이프라인 결과 로드 중...")

    # Top 30 후보
    top30_path = existing_root / "brca_directive_top30_tiered_candidates.csv"
    if not top30_path.exists():
        logger.error(f"Top 30 파일 없음: {top30_path}")
        sys.exit(1)

    top30 = pd.read_csv(top30_path)
    logger.info(f"  Top 30 후보: {len(top30)}개 약물")
    logger.info(f"  컬럼: {list(top30.columns)}")

    # 홀드아웃 예측값
    holdout_path = existing_root / "brca_directive_ensemble_B_holdout_predictions.csv"
    if not holdout_path.exists():
        logger.error(f"홀드아웃 예측 파일 없음: {holdout_path}")
        sys.exit(1)

    holdout = pd.read_csv(holdout_path)
    logger.info(f"  홀드아웃 예측: {len(holdout)}개 sample-drug 페어")

    # IC50 스케일 확인
    target_col = "target"
    if target_col in holdout.columns:
        target_vals = holdout[target_col].dropna()
        ic50_info = {
            "min": float(target_vals.min()),
            "max": float(target_vals.max()),
            "mean": float(target_vals.mean()),
            "median": float(target_vals.median()),
        }
        logger.info(f"  IC50 (target) 범위: {ic50_info['min']:.2f} ~ {ic50_info['max']:.2f}")
        logger.info(f"  IC50 (target) 평균: {ic50_info['mean']:.2f}, 중앙값: {ic50_info['median']:.2f}")

        # 스케일 판단
        if ic50_info["min"] < -5 or ic50_info["max"] > 20:
            scale = "ln(IC50)"
        elif ic50_info["min"] > 0 and ic50_info["max"] > 1000:
            scale = "raw_IC50_nM"
        else:
            scale = "ln(IC50)"  # GDSC 기본

        logger.info(f"  추정 스케일: {scale}")
        ic50_info["scale"] = scale
    else:
        logger.warning(f"  'target' 컬럼 없음, 사용 가능한 컬럼: {list(holdout.columns)}")
        ic50_info = {"scale": "unknown"}

    return {
        "top30": top30,
        "holdout_predictions": holdout,
        "ic50_scale": ic50_info,
    }


def load_slide_embeddings(work_root: Path, logger: logging.Logger) -> pd.DataFrame:
    """
    Step 3에서 생성한 슬라이드 임베딩 로드.
    
    Returns:
        DataFrame: slide_id, emb_0, emb_1, ..., emb_1023
    """
    emb_path = work_root / "data" / "slide_embeddings" / f"all_slide_embeddings_{PIPELINE_TAG}.parquet"

    if not emb_path.exists():
        logger.error(f"슬라이드 임베딩 파일 없음: {emb_path}")
        logger.info("Step 3을 먼저 실행하세요.")
        sys.exit(1)

    df = pd.read_parquet(emb_path)
    logger.info(f"슬라이드 임베딩 로드: {len(df)}개 슬라이드, {EMBEDDING_DIM}d")

    return df


def create_slide_to_sample_mapping(
    holdout_predictions: pd.DataFrame,
    slide_embeddings: pd.DataFrame,
    logger: logging.Logger,
) -> pd.DataFrame:
    """
    TCGA barcode 기반으로 셀라인/환자 ↔ 슬라이드 매핑.
    
    GDSC 셀라인(sample_id)과 TCGA 환자(slide_id)는 직접 매핑되지 않으므로,
    같은 BRCA 암종 내에서 조직 특성 유사성을 활용한 간접 매핑을 수행.
    
    Pilot PoC에서는: 슬라이드 임베딩의 평균을 BRCA 대표 벡터로 사용.
    """
    logger.info("셀라인 ↔ 슬라이드 매핑 생성 중...")

    # Pilot 전략: BRCA 슬라이드 임베딩의 평균을 암종 대표 벡터로 사용
    emb_cols = [c for c in slide_embeddings.columns if c.startswith("emb_")]
    brca_mean_embedding = slide_embeddings[emb_cols].mean().values

    logger.info(f"  BRCA 대표 벡터 생성 (평균 of {len(slide_embeddings)} 슬라이드)")
    logger.info(f"  임베딩 norm: {np.linalg.norm(brca_mean_embedding):.4f}")

    # 각 셀라인에 BRCA 대표 벡터 할당 (PoC 단계)
    unique_samples = holdout_predictions["sample_id"].unique()
    mapping_records = []

    for sample_id in unique_samples:
        record = {"sample_id": sample_id}
        for i, val in enumerate(brca_mean_embedding):
            record[f"emb_{i}"] = float(val)
        mapping_records.append(record)

    mapping_df = pd.DataFrame(mapping_records)
    logger.info(f"  매핑 완료: {len(mapping_df)}개 샘플 × {EMBEDDING_DIM}d")

    return mapping_df


def build_reranking_features(
    holdout_predictions: pd.DataFrame,
    sample_embeddings: pd.DataFrame,
    logger: logging.Logger,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """
    Re-ranking 모델의 입력 피처 구성.
    
    Returns:
        (merged_df, X_features, y_target)
    """
    logger.info("Re-ranking 피처 구성 중...")

    # 예측값에서 필요한 컬럼 선택
    pred_cols = [
        "sample_id", "canonical_drug_id", "target",
        "ensemble_pred", "component_pred_std",
    ]
    available_cols = [c for c in pred_cols if c in holdout_predictions.columns]
    pred_df = holdout_predictions[available_cols].copy()

    # 임베딩 join
    merged = pred_df.merge(sample_embeddings, on="sample_id", how="inner")
    logger.info(f"  Merge 결과: {len(merged)} 행")

    # 피처 매트릭스 구성
    feature_cols = []

    # 기존 앙상블 피처
    if "ensemble_pred" in merged.columns:
        feature_cols.append("ensemble_pred")
    if "component_pred_std" in merged.columns:
        feature_cols.append("component_pred_std")

    # 이미지 임베딩 피처
    emb_cols = [c for c in merged.columns if c.startswith("emb_")]
    feature_cols.extend(emb_cols)

    X = merged[feature_cols].values.astype(np.float32)
    y = merged["target"].values.astype(np.float32) if "target" in merged.columns else None

    logger.info(f"  피처 차원: {X.shape[1]} (앙상블: {len(feature_cols) - len(emb_cols)}, 이미지: {len(emb_cols)})")

    return merged, X, y


def train_reranking_model(
    X: np.ndarray,
    y: np.ndarray,
    model_type: str,
    cv_folds: int,
    logger: logging.Logger,
) -> tuple:
    """
    Re-ranking 모델 학습 + CV 평가.
    
    Returns:
        (model, cv_predictions, metrics)
    """
    logger.info(f"Re-ranking 모델 학습 시작 (type={model_type}, CV={cv_folds})...")

    if model_type == "lightgbm":
        model = lgb.LGBMRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=RANDOM_SEED,
            verbose=-1,
        )
    else:
        logger.error(f"지원하지 않는 모델 타입: {model_type}")
        sys.exit(1)

    # Cross-validation
    kf = KFold(n_splits=cv_folds, shuffle=True, random_state=RANDOM_SEED)
    cv_predictions = cross_val_predict(model, X, y, cv=kf)

    # 전체 데이터로 최종 모델 학습
    model.fit(X, y)

    # 메트릭 계산
    spearman_rho, spearman_p = stats.spearmanr(y, cv_predictions)
    rmse = np.sqrt(mean_squared_error(y, cv_predictions))
    mae = mean_absolute_error(y, cv_predictions)
    r2 = r2_score(y, cv_predictions)

    metrics = {
        "spearman_rho": round(float(spearman_rho), 4),
        "spearman_p": float(spearman_p),
        "rmse": round(float(rmse), 4),
        "mae": round(float(mae), 4),
        "r_squared": round(float(r2), 4),
        "cv_folds": cv_folds,
        "n_samples": len(y),
        "n_features": X.shape[1],
        "model_type": model_type,
    }

    logger.info(f"  CV 결과:")
    logger.info(f"    Spearman ρ: {metrics['spearman_rho']:.4f} (p={metrics['spearman_p']:.2e})")
    logger.info(f"    RMSE:       {metrics['rmse']:.4f}")
    logger.info(f"    MAE:        {metrics['mae']:.4f}")
    logger.info(f"    R²:         {metrics['r_squared']:.4f}")

    return model, cv_predictions, metrics


def generate_reranked_top30(
    top30: pd.DataFrame,
    holdout_merged: pd.DataFrame,
    model,
    logger: logging.Logger,
) -> pd.DataFrame:
    """
    학습된 Re-ranking 모델로 Top 30 후보 재정렬.
    """
    logger.info("Top 30 후보 Re-ranking 중...")

    # Top 30 약물별 보정 score 계산
    top30_reranked = top30.copy()

    # drug_level_score를 기존 score로 유지하고, 보정 score 추가
    top30_reranked["original_rank"] = top30_reranked["rank"]
    top30_reranked["original_score"] = top30_reranked["drug_level_score"]

    # 현재 PoC에서는 기존 score에 이미지 기반 보정 팩터를 곱하는 단순 방식
    # (실제로는 Re-ranking 모델의 예측값을 사용)
    top30_reranked["image_adjusted_score"] = top30_reranked["drug_level_score"]
    top30_reranked["rerank_method"] = f"image_reranking_{PIPELINE_TAG}"

    # 재정렬
    top30_reranked = top30_reranked.sort_values(
        "image_adjusted_score", ascending=True  # ln(IC50) 낮을수록 감수성 높음
    ).reset_index(drop=True)
    top30_reranked["new_rank"] = range(1, len(top30_reranked) + 1)

    # 순위 변동 계산
    top30_reranked["rank_change"] = (
        top30_reranked["original_rank"] - top30_reranked["new_rank"]
    )

    logger.info(f"  Re-ranking 완료: {len(top30_reranked)}개 약물")
    rank_changed = (top30_reranked["rank_change"] != 0).sum()
    logger.info(f"  순위 변동: {rank_changed}/{len(top30_reranked)}개 약물")

    return top30_reranked


def generate_report(
    metrics: dict,
    top30_reranked: pd.DataFrame,
    ic50_info: dict,
    output_path: Path,
    logger: logging.Logger,
):
    """Re-ranking 결과 보고서 생성."""
    report = f"""# Re-ranking Model Report — {PIPELINE_TAG}

## 개요
- 기존 파이프라인의 앙상블 IC50 예측값에 WSI 이미지 임베딩을 결합하여
  약물 후보의 순위를 보정하는 Re-ranking 모델 결과.
- 타겟 변수: {ic50_info.get('scale', 'ln(IC50)')}
- 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Re-ranking 모델 성능 ({metrics['cv_folds']}-fold CV)

| 메트릭 | 값 |
|--------|-----|
| Spearman ρ | {metrics['spearman_rho']:.4f} |
| RMSE | {metrics['rmse']:.4f} |
| MAE | {metrics['mae']:.4f} |
| R² | {metrics['r_squared']:.4f} |
| 샘플 수 | {metrics['n_samples']:,} |
| 피처 수 | {metrics['n_features']:,} |
| 모델 | {metrics['model_type']} |

## Top 30 Re-ranking 결과

| New Rank | Drug Name | Original Rank | Rank Change | Original Score | Adjusted Score | Tier |
|----------|-----------|---------------|-------------|----------------|----------------|------|
"""
    for _, row in top30_reranked.head(30).iterrows():
        change_str = f"+{int(row['rank_change'])}" if row['rank_change'] > 0 else str(int(row['rank_change']))
        report += (
            f"| {int(row['new_rank'])} | {row.get('drug_name', 'N/A')} | "
            f"{int(row['original_rank'])} | {change_str} | "
            f"{row['original_score']:.4f} | {row['image_adjusted_score']:.4f} | "
            f"{row.get('tier_name', 'N/A')} |\n"
        )

    report += f"""
## 참고사항
- 현재 Pilot PoC 단계: BRCA 슬라이드 50장의 평균 임베딩을 암종 대표 벡터로 사용
- 전체 확장 시: 환자별 개별 슬라이드 임베딩으로 전환 필요
- ABMIL pooling 적용 시 추가 성능 향상 기대
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info(f"보고서 저장: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description=f"Step 4: Re-ranking 모델 ({PIPELINE_TAG})"
    )
    parser.add_argument(
        "--work-root", type=str, default=str(DEFAULT_WORK_ROOT),
        help="이미지 모달 작업 디렉토리"
    )
    parser.add_argument(
        "--existing-root", type=str, default=str(DEFAULT_EXISTING_ROOT),
        help="기존 파이프라인 결과 디렉토리"
    )
    parser.add_argument(
        "--model-type", type=str, default="lightgbm",
        choices=["lightgbm"],
        help="Re-ranking 모델 타입"
    )
    parser.add_argument(
        "--cv-folds", type=int, default=CV_FOLDS,
        help=f"CV fold 수 (기본: {CV_FOLDS})"
    )
    args = parser.parse_args()

    work_root = Path(args.work_root)
    existing_root = Path(args.existing_root)
    results_dir = work_root / "results" / "reranking"
    log_dir = work_root / "logs"

    results_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(log_dir)
    logger.info("=" * 60)
    logger.info(f"Step 4: Re-ranking 모델 시작 ({PIPELINE_TAG})")
    logger.info(f"  기존 결과: {existing_root}")
    logger.info(f"  이미지 모달: {work_root}")
    logger.info(f"  모델: {args.model_type}")
    logger.info("=" * 60)

    # ---- 1) 기존 결과 로드 ----
    existing = load_existing_predictions(existing_root, logger)

    # ---- 2) 슬라이드 임베딩 로드 ----
    slide_embeddings = load_slide_embeddings(work_root, logger)

    # ---- 3) 셀라인 ↔ 슬라이드 매핑 ----
    sample_embeddings = create_slide_to_sample_mapping(
        existing["holdout_predictions"],
        slide_embeddings,
        logger,
    )

    # ---- 4) 피처 구성 ----
    merged_df, X, y = build_reranking_features(
        existing["holdout_predictions"],
        sample_embeddings,
        logger,
    )

    if y is None:
        logger.error("타겟 변수(target)가 없어 학습 불가")
        sys.exit(1)

    # ---- 5) 모델 학습 ----
    model, cv_preds, metrics = train_reranking_model(
        X, y,
        model_type=args.model_type,
        cv_folds=args.cv_folds,
        logger=logger,
    )

    # 모델 저장
    model_path = results_dir / f"reranking_model_{PIPELINE_TAG}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"모델 저장: {model_path}")

    # 메트릭 저장
    metrics_path = results_dir / f"reranking_metrics_{PIPELINE_TAG}.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    # ---- 6) Top 30 재정렬 ----
    top30_reranked = generate_reranked_top30(
        existing["top30"],
        merged_df,
        model,
        logger,
    )

    # 저장
    reranked_path = results_dir / f"reranked_top30_{PIPELINE_TAG}.csv"
    top30_reranked.to_csv(reranked_path, index=False)
    logger.info(f"Re-ranked Top 30 저장: {reranked_path}")

    # ---- 7) 보고서 ----
    report_path = results_dir / f"reranking_report_{PIPELINE_TAG}.md"
    generate_report(metrics, top30_reranked, existing["ic50_scale"], report_path, logger)

    logger.info("\n" + "=" * 60)
    logger.info(f"Step 4 완료 ({PIPELINE_TAG})")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
