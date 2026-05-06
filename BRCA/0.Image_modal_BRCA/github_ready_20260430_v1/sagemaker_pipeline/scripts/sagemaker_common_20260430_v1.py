#!/usr/bin/env python3
"""Shared helpers for the 20260430_v1 SageMaker image-modal pipeline."""

from __future__ import annotations

import json
import logging
import math
import os
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, KFold, train_test_split, cross_val_predict

PIPELINE_TAG = "20260430_v1"
RANDOM_SEED = 42
EMBEDDING_DIM = 1024


def setup_logging(log_dir: Path, name: str) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"{name}_{PIPELINE_TAG}")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(log_dir / f"{name}_{PIPELINE_TAG}.log", encoding="utf-8")
    ch = logging.StreamHandler()
    fh.setLevel(logging.DEBUG)
    ch.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def ensure_processing_output_dirs(base: Path = Path("/opt/ml/processing/output")) -> None:
    for name in ["wsi_raw", "wsi_tiles", "embeddings", "results", "logs"]:
        (base / name).mkdir(parents=True, exist_ok=True)


def parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Not an S3 URI: {uri}")
    bucket, _, key = uri[5:].partition("/")
    return bucket, key


def upload_file_to_s3(path: Path, s3_uri: str) -> None:
    import boto3

    bucket, key_prefix = parse_s3_uri(s3_uri.rstrip("/") + "/" + path.name)
    boto3.client("s3").upload_file(str(path), bucket, key_prefix)


def tcga_patient_barcode(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.search(r"(TCGA-[A-Z0-9]{2}-[A-Z0-9]{4})", value.upper())
    return match.group(1) if match else None


def embedding_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith("emb_")]


def load_slide_embeddings(path: Path) -> pd.DataFrame:
    if path.is_dir():
        path = path / f"all_slide_embeddings_{PIPELINE_TAG}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"slide embedding table not found: {path}")
    df = pd.read_parquet(path)
    if "patient_barcode" not in df.columns:
        df["patient_barcode"] = df["slide_id"].map(tcga_patient_barcode)
    return df


def patient_embedding_table(slide_embeddings: pd.DataFrame) -> pd.DataFrame:
    emb_cols = embedding_columns(slide_embeddings)
    if not emb_cols:
        raise ValueError("No emb_* columns found in slide embedding table")
    df = slide_embeddings.copy()
    df["patient_barcode"] = df["patient_barcode"].fillna(df["slide_id"].map(tcga_patient_barcode))
    df = df.dropna(subset=["patient_barcode"])
    return df.groupby("patient_barcode", as_index=False)[emb_cols].mean()


def attach_patient_embeddings(rows: pd.DataFrame, patient_embeddings: pd.DataFrame, id_col: str = "sample_id") -> pd.DataFrame:
    emb_cols = embedding_columns(patient_embeddings)
    out = rows.copy()
    out["patient_barcode"] = out[id_col].map(tcga_patient_barcode) if id_col in out.columns else None
    out = out.merge(patient_embeddings, on="patient_barcode", how="left")
    out[emb_cols] = out[emb_cols].fillna(0.0)
    return out


def smiles_to_scaffold(smiles: str) -> str:
    try:
        from rdkit import Chem
        from rdkit.Chem.Scaffolds import MurckoScaffold
    except Exception:
        return ""
    if not isinstance(smiles, str) or not smiles:
        return ""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return ""
    scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False)
    return scaffold or smiles


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    rho, pval = stats.spearmanr(y_true, y_pred)
    if math.isnan(float(rho)):
        rho, pval = 0.0, 1.0
    return {
        "spearman": float(rho),
        "spearman_p": float(pval),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def make_lgbm():
    import lightgbm as lgb

    return lgb.LGBMRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=RANDOM_SEED,
        verbose=-1,
    )


def evaluate_regressor(X: pd.DataFrame, y: np.ndarray, eval_mode: str, groups: Iterable | None = None) -> tuple[dict, np.ndarray]:
    model = make_lgbm()
    if eval_mode == "holdout":
        idx = np.arange(len(y))
        train_idx, test_idx = train_test_split(idx, test_size=0.2, random_state=RANDOM_SEED)
        model.fit(X.iloc[train_idx], y[train_idx])
        preds = np.full(len(y), np.nan, dtype=np.float32)
        preds[test_idx] = model.predict(X.iloc[test_idx])
        metrics = regression_metrics(y[test_idx], preds[test_idx])
        metrics.update({"n_train": int(len(train_idx)), "n_test": int(len(test_idx))})
        return metrics, preds
    if eval_mode == "cv5":
        cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
        preds = cross_val_predict(model, X, y, cv=cv)
        metrics = regression_metrics(y, preds)
        metrics.update({"n_train": int(len(y)), "n_test": int(len(y))})
        return metrics, preds
    if eval_mode in {"groupcv", "scaffoldcv"}:
        if groups is None:
            raise ValueError(f"{eval_mode} requires groups")
        cv = GroupKFold(n_splits=3)
        preds = cross_val_predict(model, X, y, cv=cv, groups=np.asarray(list(groups)))
        metrics = regression_metrics(y, preds)
        metrics.update({"n_train": int(len(y)), "n_test": int(len(y))})
        return metrics, preds
    raise ValueError(f"Unknown eval mode: {eval_mode}")


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
