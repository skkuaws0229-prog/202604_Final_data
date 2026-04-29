#!/usr/bin/env python3
"""
Prepare STAD Step 4 Phase 2A inputs.

Input files:
- fe_qc/20260421_stad_fe_v1/features_slim.parquet
- fe_qc/20260421_stad_fe_v1/features/labels.parquet

Output files:
- data/X_numeric.npy
- data/y_train.npy
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List
import argparse

import numpy as np
import pandas as pd


def log(msg: str) -> None:
    """Print timestamped message."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare STAD Phase 2A input arrays")
    parser.add_argument(
        "--run-id",
        default="step4_stad_inputs_v1",
        help="Subdirectory under data/ to avoid overwriting prior runs",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow writing even if output files already exist",
    )
    args = parser.parse_args()

    base_dir: Path = Path(__file__).resolve().parents[1]
    data_dir: Path = base_dir / "data" / args.run_id
    data_dir.mkdir(parents=True, exist_ok=True)

    features_slim_path: Path = base_dir / "fe_qc" / "20260421_stad_fe_v1" / "features_slim.parquet"
    labels_path: Path = base_dir / "fe_qc" / "20260421_stad_fe_v1" / "features" / "labels.parquet"

    log("=" * 90)
    log("Phase 2A input preparation (STAD)")
    log(f"Reading: {features_slim_path}")
    log(f"Reading: {labels_path}")
    log("=" * 90)

    if not features_slim_path.exists():
        raise FileNotFoundError(f"Missing file: {features_slim_path}")
    if not labels_path.exists():
        raise FileNotFoundError(f"Missing file: {labels_path}")

    x_path: Path = data_dir / "X_numeric.npy"
    y_path: Path = data_dir / "y_train.npy"
    if not args.force and (x_path.exists() or y_path.exists()):
        raise FileExistsError(
            f"Output already exists under {data_dir}. "
            "Use a new --run-id or pass --force."
        )

    df: pd.DataFrame = pd.read_parquet(features_slim_path)
    log(f"features_slim shape: {df.shape}")

    numeric_cols: List[str] = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols: List[str] = [c for c in numeric_cols if c not in ["sample_id", "canonical_drug_id"]]
    non_numeric_cols: List[str] = [c for c in df.columns if c not in numeric_cols]

    log(f"Numeric feature cols: {len(feature_cols)}")
    log(f"Non-numeric cols excluded: {non_numeric_cols}")

    x_numeric: np.ndarray = df[feature_cols].values.astype(np.float32)
    log(f"X_numeric shape: {x_numeric.shape}")
    log(f"X_numeric NaN count: {int(np.isnan(x_numeric).sum())}")
    log(f"X_numeric Inf count: {int(np.isinf(x_numeric).sum())}")

    np.save(x_path, x_numeric)
    log(f"Saved: {x_path} ({x_path.stat().st_size / (1024 ** 2):.2f} MB)")

    df_labels: pd.DataFrame = pd.read_parquet(labels_path)
    if "label_regression" not in df_labels.columns:
        raise ValueError(f"`label_regression` not found in labels columns: {list(df_labels.columns)}")

    y_train: np.ndarray = df_labels["label_regression"].values.astype(np.float32)
    log(f"y_train shape: {y_train.shape}")
    log(f"y_train range: {float(y_train.min()):.4f} ~ {float(y_train.max()):.4f}")
    log(f"y_train NaN count: {int(np.isnan(y_train).sum())}")

    if x_numeric.shape[0] != y_train.shape[0]:
        raise ValueError(f"Row mismatch: X_numeric={x_numeric.shape[0]}, y_train={y_train.shape[0]}")

    np.save(y_path, y_train)
    log(f"Saved: {y_path} ({y_path.stat().st_size / 1024:.2f} KB)")

    src_drug_features: Path = base_dir / "data" / "drug_features.parquet"
    dst_drug_features: Path = data_dir / "drug_features.parquet"
    if src_drug_features.exists():
        if not dst_drug_features.exists() or args.force:
            df_drug_full: pd.DataFrame = pd.read_parquet(src_drug_features)
            df_drug_full.to_parquet(dst_drug_features, index=False)
            log(f"Copied drug_features to run dir: {dst_drug_features}")
        df_drug: pd.DataFrame = pd.read_parquet(dst_drug_features, columns=["canonical_drug_id", "canonical_smiles"])
        coverage: float = float(df_drug["canonical_smiles"].notna().mean() * 100.0)
        log(f"drug_features.parquet coverage: {coverage:.1f}%")
    else:
        log(f"WARNING: Missing source {src_drug_features} (required for Phase 2B/2C)")

    log("=" * 90)
    log("Phase 2A input preparation complete (STAD)")
    log("=" * 90)


if __name__ == "__main__":
    main()

