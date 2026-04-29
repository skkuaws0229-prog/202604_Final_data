#!/usr/bin/env python3
"""Overfitting/stability checks for STAD Step 4."""

from __future__ import annotations

from typing import Dict, List
import numpy as np


def check_overfitting(fold_results: List[dict], threshold: float = 0.15) -> Dict:
    """Check train-vs-val Spearman gap across folds."""
    gaps = []
    flags = []
    for result in fold_results:
        gap = float(result["train"]["spearman"] - result["val"]["spearman"])
        gaps.append(gap)
        flags.append(gap > threshold)
    out = {
        "threshold": float(threshold),
        "gaps": gaps,
        "mean_gap": float(np.mean(gaps)) if gaps else 0.0,
        "max_gap": float(np.max(gaps)) if gaps else 0.0,
        "overfitting_flags": [bool(x) for x in flags],
        "n_overfitting_folds": int(sum(flags)),
    }
    if any(flags):
        out["warning"] = f"Overfitting detected in {sum(flags)} fold(s)"
    return out


def check_stability(fold_results: List[dict], threshold: float = 0.05) -> Dict:
    """Check std-dev of validation Spearman across folds."""
    val_scores = [float(r["val"]["spearman"]) for r in fold_results]
    std_val = float(np.std(val_scores)) if val_scores else 0.0
    out = {
        "threshold": float(threshold),
        "val_spearman_std": std_val,
        "val_spearman_scores": val_scores,
        "unstable": bool(std_val > threshold),
    }
    if out["unstable"]:
        out["warning"] = f"Unstable across folds (std={std_val:.4f})"
    return out

