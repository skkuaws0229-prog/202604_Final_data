#!/usr/bin/env python3
"""Full ablation evaluation for SageMaker image-modal BRCA runs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.sagemaker_common_20260430_v1 import (
    PIPELINE_TAG,
    attach_patient_embeddings,
    embedding_columns,
    ensure_processing_output_dirs,
    evaluate_regressor,
    load_slide_embeddings,
    patient_embedding_table,
    setup_logging,
    smiles_to_scaffold,
)

EVAL_MODES = ["holdout", "cv5", "groupcv", "scaffoldcv"]
EXPERIMENTS = ["baseline_no_image", "with_image_mean_pool", "with_image_abmil", "image_only"]


def find_holdout(existing_dir: Path) -> pd.DataFrame:
    path = next(existing_dir.rglob("*holdout*predictions*.csv"), None)
    if path is None:
        raise FileNotFoundError(f"Holdout prediction CSV not found under {existing_dir}")
    return pd.read_csv(path)


def groups(df: pd.DataFrame, mode: str):
    if mode == "groupcv":
        return df["canonical_drug_id"].astype(str)
    if mode == "scaffoldcv":
        if "canonical_smiles" in df.columns:
            return df["canonical_smiles"].map(smiles_to_scaffold).replace("", np.nan).fillna(df["canonical_drug_id"].astype(str))
        return df["canonical_drug_id"].astype(str)
    return None


def feature_cols(df: pd.DataFrame, emb_cols: list[str], experiment: str) -> list[str]:
    base = [c for c in ["ensemble_pred", "component_pred_std"] if c in df.columns]
    if experiment == "baseline_no_image":
        return base
    if experiment in {"with_image_mean_pool", "with_image_abmil"}:
        return base + emb_cols
    if experiment == "image_only":
        return emb_cols
    raise ValueError(experiment)


def infer_model_used(slide_embeddings: pd.DataFrame, label: str | None) -> str:
    if label:
        return label
    if "model_used" in slide_embeddings.columns:
        vals = slide_embeddings["model_used"].dropna().unique()
        if len(vals):
            return str(vals[0])
    return "unknown"


def plot(results: pd.DataFrame, output_path: Path, logger) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        logger.warning("matplotlib unavailable; skipping chart")
        return
    fig, axes = plt.subplots(1, 4, figsize=(18, 5))
    metrics = [("spearman", True), ("rmse", False), ("mae", False), ("r2", True)]
    subset = results[results["eval_mode"] == "cv5"]
    for ax, (metric, higher) in zip(axes, metrics):
        vals = subset.set_index("experiment")[metric].reindex(EXPERIMENTS)
        bars = ax.bar(range(len(vals)), vals.values)
        best = int(np.nanargmax(vals.values) if higher else np.nanargmin(vals.values))
        bars[best].set_edgecolor("#10b981")
        bars[best].set_linewidth(2)
        ax.set_title(metric)
        ax.set_xticks(range(len(vals)))
        ax.set_xticklabels([x.replace("_", "\n") for x in vals.index], fontsize=8)
    fig.suptitle(f"Ablation comparison ({PIPELINE_TAG}, cv5)")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--existing-dir", type=Path, default=Path("/opt/ml/processing/input/existing"))
    parser.add_argument("--embedding-path", type=Path, default=Path("/opt/ml/processing/input/embeddings/slide_embeddings"))
    parser.add_argument("--vit-baseline-path", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("/opt/ml/processing/output/results/ablation"))
    parser.add_argument("--model-used", default=None)
    args = parser.parse_args()

    ensure_processing_output_dirs()
    logger = setup_logging(Path("/opt/ml/processing/output/logs"), "step5_ablation_sagemaker")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    holdout = find_holdout(args.existing_dir)
    slide_embeddings = load_slide_embeddings(args.embedding_path)
    patient_embeddings = patient_embedding_table(slide_embeddings)
    train_df = attach_patient_embeddings(holdout, patient_embeddings, id_col="sample_id")
    emb_cols = embedding_columns(patient_embeddings)
    y = train_df["target"].values.astype(np.float32)
    model_used = infer_model_used(slide_embeddings, args.model_used)

    rows = []
    for experiment in EXPERIMENTS:
        cols = feature_cols(train_df, emb_cols, experiment)
        if not cols:
            logger.warning("Skipping %s: no features", experiment)
            continue
        X = train_df[cols].astype(np.float32)
        for mode in EVAL_MODES:
            metrics, _ = evaluate_regressor(X, y, mode, groups(train_df, mode))
            rows.append({
                "experiment": experiment,
                "eval_mode": mode,
                "model_used": model_used,
                "spearman": metrics["spearman"],
                "rmse": metrics["rmse"],
                "mae": metrics["mae"],
                "r2": metrics["r2"],
                "n_train": metrics["n_train"],
                "n_test": metrics["n_test"],
                "n_features": int(X.shape[1]),
            })
            logger.info("[%s/%s] spearman=%.4f rmse=%.4f r2=%.4f", experiment, mode, metrics["spearman"], metrics["rmse"], metrics["r2"])

    results = pd.DataFrame(rows)
    if args.vit_baseline_path and args.vit_baseline_path.exists():
        vit = pd.read_csv(args.vit_baseline_path)
        if "model_used" not in vit.columns:
            vit["model_used"] = "ViT-Large"
        results = pd.concat([vit, results], ignore_index=True, sort=False)

    csv_path = args.output_dir / f"ablation_comparison_full_{PIPELINE_TAG}.csv"
    results.to_csv(csv_path, index=False)
    plot(results, args.output_dir / f"ablation_chart_full_{PIPELINE_TAG}.png", logger)
    report = [
        f"# Ablation Report ({PIPELINE_TAG})",
        "",
        f"- model_used: {model_used}",
        f"- rows: {len(results)}",
        "- note: GDSC rows without TCGA patient barcodes receive zero image vectors; patient-level TCGA embeddings are used for patient-specific reranking.",
        "",
        results.to_markdown(index=False),
    ]
    (args.output_dir / f"ablation_report_full_{PIPELINE_TAG}.md").write_text("\n".join(report), encoding="utf-8")
    logger.info("Step 5 complete: %s", csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
