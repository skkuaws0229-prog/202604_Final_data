#!/usr/bin/env python3
"""
STAD Phase-3 style ensemble: CatBoost (ML) + best DL + best Graph — Lung `phase3_ensemble_analysis.py` 와 동일한
아이디어(OOF 기반 Simple / GroupCV Spearman 비례 Weighted, gain·diversity·consensus).

입력 OOF는 Step4 산출물:
  results/<result_tag>/ml|dl|graph/<stem>_<eval_mode>_oof/<Model>.npy

기본은 eval_mode=groupcv, 각 phase(2A/2B/2C)별로
  - ML: CatBoost.npy (없으면 CatBoost_Fallback_GBR2.npy)
  - DL: 해당 phase OOF 디렉터리에서 y 와 Spearman 최대인 모델
  - Graph: 동일

출력:
  results/<result_tag>/ensemble_catboost_dl_graph_<eval_mode>.json
"""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import spearmanr


PHASES: tuple[tuple[str, str, str, str], ...] = (
    ("2A", "stad_numeric_ml_v1", "stad_numeric_dl_v1", "stad_numeric_graph_v1"),
    ("2B", "stad_numeric_smiles_ml_v1", "stad_numeric_smiles_dl_v1", "stad_numeric_smiles_graph_v1"),
    (
        "2C",
        "stad_numeric_context_smiles_ml_v1",
        "stad_numeric_context_smiles_dl_v1",
        "stad_numeric_context_smiles_graph_v1",
    ),
)


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def val_spearman_from_groupcv(jpath: Path, model: str) -> float | None:
    data = load_json(jpath)
    if not data or model not in data:
        return None
    summ = data[model].get("summary") or {}
    v = summ.get("val_spearman_mean")
    return float(v) if v is not None else None


def finite_spearman(y: np.ndarray, pred: np.ndarray) -> float:
    m = np.isfinite(y) & np.isfinite(pred)
    if int(m.sum()) < 3:
        return float("nan")
    r, _ = spearmanr(y[m], pred[m])
    return float(r)


def load_catboost_oof(ml_oof_dir: Path) -> tuple[np.ndarray, str] | tuple[None, None]:
    for name in ("CatBoost", "CatBoost_Fallback_GBR2"):
        p = ml_oof_dir / f"{name}.npy"
        if p.exists():
            return np.load(p).astype(np.float32), name
    return None, None


def load_graphsage_oof(gr_oof_dir: Path) -> tuple[np.ndarray, str] | tuple[None, None]:
    """Graph slot is fixed to GraphSAGE for Step5 policy."""
    p = gr_oof_dir / "GraphSAGE.npy"
    if p.exists():
        return np.load(p).astype(np.float32), "GraphSAGE"
    return None, None


def pick_best_oof_in_dir(oof_dir: Path, y: np.ndarray) -> tuple[str, np.ndarray, float] | None:
    if not oof_dir.is_dir():
        return None
    best_name: str | None = None
    best_oof: np.ndarray | None = None
    best_score = float("-inf")
    for p in sorted(oof_dir.glob("*.npy")):
        oof = np.load(p).astype(np.float32)
        s = finite_spearman(y, oof)
        if np.isfinite(s) and s > best_score:
            best_score = s
            best_name = p.stem
            best_oof = oof
    if best_name is None or best_oof is None:
        return None
    return best_name, best_oof, best_score


def mean_pairwise_oof_prediction_spearman(oofs: list[np.ndarray]) -> float:
    """Pairwise Spearman ρ between *OOF prediction vectors* (not error diversity).

    Lung `phase3_ensemble_analysis.calculate_diversity` 이름은 'diversity'지만,
    값이 **클수록** 세 모델의 랭킹/예측이 **서로 더 닮음** (보완적 다양성은 오히려 작음).
    직관적 '다양성' 지표로 쓰려면 `1 - rho` 형태의 complementarity를 함께 보면 됨.
    """
    if len(oofs) < 2:
        return 0.0
    cors: list[float] = []
    for i, j in combinations(range(len(oofs)), 2):
        m = np.isfinite(oofs[i]) & np.isfinite(oofs[j])
        if int(m.sum()) < 3:
            continue
        c, _ = spearmanr(oofs[i][m], oofs[j][m])
        cors.append(float(c))
    return float(np.mean(cors)) if cors else float("nan")


def consensus_mean(oofs: list[np.ndarray]) -> float:
    stacked = np.stack(oofs, axis=0)
    return float(np.mean(np.std(stacked, axis=0)))


def weighted_stack(oofs: list[np.ndarray], weights: np.ndarray) -> np.ndarray:
    w = weights.astype(np.float64)
    w = np.clip(w, 1e-8, None)
    w = w / w.sum()
    out = np.zeros_like(oofs[0], dtype=np.float64)
    for i, o in enumerate(oofs):
        out += w[i] * o.astype(np.float64)
    return out.astype(np.float32)


def find_best_weights_3(oofs: list[np.ndarray], y: np.ndarray, n_steps: int = 11) -> tuple[list[float], float]:
    """Colon `run_ensemble.py` 와 동일한 3-model grid (w1,w2,w3)."""
    if len(oofs) != 3:
        raise ValueError("Expected 3 OOF vectors")
    best_score = float("-inf")
    best_w: list[float] | None = None
    grid = np.linspace(0.0, 1.0, n_steps)
    for w1 in grid:
        for w2 in grid:
            w3 = 1.0 - w1 - w2
            if w3 < -1e-12:
                continue
            pred = (w1 * oofs[0] + w2 * oofs[1] + w3 * oofs[2]).astype(np.float32)
            s = finite_spearman(y, pred)
            if np.isfinite(s) and s > best_score:
                best_score = s
                best_w = [float(w1), float(w2), float(max(w3, 0.0))]
    if best_w is None:
        return [1 / 3, 1 / 3, 1 / 3], float("nan")
    return best_w, best_score


def main() -> None:
    parser = argparse.ArgumentParser(description="STAD CatBoost + DL + Graph ensemble (Lung-style OOF)")
    parser.add_argument("--run-id", default="step4_stad_inputs_20260422_002")
    parser.add_argument("--result-tag", default="20260422_stad_step4_v2")
    parser.add_argument("--eval-mode", default="groupcv", help="OOF suffix, e.g. groupcv")
    args = parser.parse_args()

    base = Path(__file__).resolve().parents[1]
    data_dir = base / "data" / args.run_id
    y_path = data_dir / "y_train.npy"
    if not y_path.exists():
        raise FileNotFoundError(f"Missing {y_path}")

    y = np.load(y_path).astype(np.float64)
    results_root = base / "results" / args.result_tag
    out_path = results_root / f"ensemble_catboost_dl_graph_{args.eval_mode}.json"

    phase_results: list[dict[str, Any]] = []

    for phase_label, ml_stem, dl_stem, gr_stem in PHASES:
        ml_oof_dir = results_root / "ml" / f"{ml_stem}_{args.eval_mode}_oof"
        dl_oof_dir = results_root / "dl" / f"{dl_stem}_{args.eval_mode}_oof"
        gr_oof_dir = results_root / "graph" / f"{gr_stem}_{args.eval_mode}_oof"

        cat_oof, cat_key = load_catboost_oof(ml_oof_dir)
        dl_pick = pick_best_oof_in_dir(dl_oof_dir, y)
        gr_oof, gr_name = load_graphsage_oof(gr_oof_dir)

        if cat_oof is None or dl_pick is None or gr_oof is None:
            phase_results.append(
                {
                    "phase": phase_label,
                    "ok": False,
                    "reason": "missing_catboost_or_dl_or_graphsage_oof",
                    "paths_checked": {
                        "ml_oof_dir": str(ml_oof_dir),
                        "dl_oof_dir": str(dl_oof_dir),
                        "gr_oof_dir": str(gr_oof_dir),
                    },
                }
            )
            continue

        dl_name, dl_oof, _ = dl_pick

        ml_json = results_root / "ml" / f"{ml_stem}_{args.eval_mode}.json"
        dl_json = results_root / "dl" / f"{dl_stem}_{args.eval_mode}.json"
        gr_json = results_root / "graph" / f"{gr_stem}_{args.eval_mode}.json"

        s_cat_json = val_spearman_from_groupcv(ml_json, cat_key) if args.eval_mode == "groupcv" else None
        s_dl_json = val_spearman_from_groupcv(dl_json, dl_name) if args.eval_mode == "groupcv" else None
        s_gr_json = val_spearman_from_groupcv(gr_json, gr_name) if args.eval_mode == "groupcv" else None

        oofs = [cat_oof, dl_oof, gr_oof]
        singles_oof = [
            finite_spearman(y, cat_oof),
            finite_spearman(y, dl_oof),
            finite_spearman(y, gr_oof),
        ]
        best_single = float(np.nanmax(singles_oof))

        simple_pred = np.mean(np.stack(oofs, axis=0), axis=0).astype(np.float32)
        simple_s = finite_spearman(y, simple_pred)

        json_scores = [s_cat_json, s_dl_json, s_gr_json]
        if all(v is not None and v > 0 for v in json_scores):
            w_json = np.array(json_scores, dtype=np.float64)
            weighted_pred = weighted_stack(oofs, w_json)
            weighted_s = finite_spearman(y, weighted_pred)
            w_json_list = (w_json / w_json.sum()).tolist()
        else:
            weighted_pred = simple_pred
            weighted_s = simple_s
            w_json_list = None

        opt_w, opt_s = find_best_weights_3(oofs, y)

        rho_pair = mean_pairwise_oof_prediction_spearman(oofs)
        complementarity = float(1.0 - rho_pair) if np.isfinite(rho_pair) else float("nan")
        cons = consensus_mean(oofs)

        phase_results.append(
            {
                "phase": phase_label,
                "ok": True,
                "models": {
                    "catboost_ml": cat_key,
                    "dl": dl_name,
                    "graph": gr_name,
                },
                "oof_spearman_vs_y": {
                    "catboost": singles_oof[0],
                    "dl": singles_oof[1],
                    "graph": singles_oof[2],
                    "best_single": best_single,
                },
                "groupcv_json_val_spearman_mean": {
                    "catboost": s_cat_json,
                    "dl": s_dl_json,
                    "graph": s_gr_json,
                },
                "ensemble": {
                    "simple_spearman": simple_s,
                    "weighted_json_spearman": weighted_s,
                    "weighted_json_weights": w_json_list,
                    "optimal_grid_weights": opt_w,
                    "optimal_grid_spearman": opt_s,
                },
                "lung_style_aux": {
                    "diversity_mean_pairwise_spearman": rho_pair,
                    "mean_pairwise_oof_prediction_spearman": rho_pair,
                    "complementarity_1_minus_pairwise_pred_rho": complementarity,
                    "consensus_mean_std_across_models": cons,
                    "gain_simple_vs_best_single": simple_s - best_single,
                    "gain_weighted_vs_best_single": weighted_s - best_single,
                    "gain_optimal_vs_best_single": opt_s - best_single,
                },
                "oof_dirs": {
                    "ml": str(ml_oof_dir),
                    "dl": str(dl_oof_dir),
                    "graph": str(gr_oof_dir),
                },
            }
        )

    payload = {
        "experiment": "STAD CatBoost + DL + Graph ensemble (Lung-style)",
        "run_id": args.run_id,
        "result_tag": args.result_tag,
        "eval_mode": args.eval_mode,
        "y_n": int(len(y)),
        "phases": phase_results,
        "metric_notes": {
            "diversity_field": "Lung `diversity` = mean pairwise Spearman ρ of OOF *predictions* across ensemble members. "
            "Higher ρ ⇒ predictions/ranks are more aligned (less complementary diversity). "
            "See complementarity_1_minus_pairwise_pred_rho for an intuitive 'higher is more distinct' view.",
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
