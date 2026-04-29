#!/usr/bin/env python3
"""Shared utility functions for STAD Step 4."""

from __future__ import annotations

from pathlib import Path
from typing import Dict
import json

import numpy as np
from scipy.stats import kendalltau, pearsonr, spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate regression metrics from prediction vectors."""
    spearman, _ = spearmanr(y_true, y_pred)
    pearson, _ = pearsonr(y_true, y_pred)
    kendall, _ = kendalltau(y_true, y_pred)
    return {
        "spearman": float(spearman),
        "pearson": float(pearson),
        "r2": float(r2_score(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "kendall_tau": float(kendall),
    }


def save_results(results: Dict, output_path: Path) -> None:
    """Save dict as JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved results: {output_path}", flush=True)

