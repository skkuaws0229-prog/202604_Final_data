#!/usr/bin/env python3
"""
Run STAD Step 4 ML experiments (6 models x 3 phases x 4 eval modes).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import argparse
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold, KFold, train_test_split
from sklearn.svm import SVR
from rdkit.Chem.Scaffolds import MurckoScaffold

from phase2_utils_stad import calculate_metrics, save_results
from data_validation_stad import check_overfitting, check_stability

try:
    from lightgbm import LGBMRegressor
except Exception:  # pragma: no cover
    LGBMRegressor = None  # type: ignore[assignment]

try:
    from xgboost import XGBRegressor
except Exception:  # pragma: no cover
    XGBRegressor = None  # type: ignore[assignment]

try:
    from catboost import CatBoostRegressor
except Exception:  # pragma: no cover
    CatBoostRegressor = None  # type: ignore[assignment]


def log(msg: str) -> None:
    """Timestamped log."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


def model_factories() -> Dict[str, object]:
    """Build fixed 6-model registry; fallback when optional libs are missing."""
    models: Dict[str, object] = {
        "RandomForest": RandomForestRegressor(
            n_estimators=400, max_depth=None, random_state=42, n_jobs=-1
        ),
        "ExtraTrees": ExtraTreesRegressor(
            n_estimators=400, max_depth=None, random_state=42, n_jobs=-1
        ),
        "SVR_RBF": SVR(C=5.0, epsilon=0.1, kernel="rbf"),
    }
    if LGBMRegressor is not None:
        models["LightGBM"] = LGBMRegressor(
            n_estimators=700,
            learning_rate=0.03,
            num_leaves=63,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
    else:
        models["LightGBM_Fallback_GBR"] = GradientBoostingRegressor(random_state=42)

    if XGBRegressor is not None:
        models["XGBoost"] = XGBRegressor(
            n_estimators=700,
            learning_rate=0.03,
            max_depth=7,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            objective="reg:squarederror",
            n_jobs=-1,
            verbosity=0,
        )
    else:
        models["XGBoost_Fallback_HGBR"] = HistGradientBoostingRegressor(random_state=42)

    if CatBoostRegressor is not None:
        models["CatBoost"] = CatBoostRegressor(
            iterations=700,
            learning_rate=0.03,
            depth=8,
            loss_function="RMSE",
            random_seed=42,
            verbose=False,
        )
    else:
        models["CatBoost_Fallback_GBR2"] = GradientBoostingRegressor(random_state=7)
    if len(models) != 6:
        raise RuntimeError(f"Expected 6 ML models, got {len(models)}: {list(models.keys())}")
    return models


def build_scaffold_groups(features: pd.DataFrame, drug_features: pd.DataFrame) -> np.ndarray:
    """Create scaffold group IDs aligned with features rows."""
    required = {"canonical_drug_id", "canonical_smiles"}
    if not required.issubset(set(drug_features.columns)):
        raise ValueError(f"drug_features.parquet must include columns: {required}")

    smiles_map = (
        drug_features[["canonical_drug_id", "canonical_smiles"]]
        .drop_duplicates("canonical_drug_id")
        .set_index("canonical_drug_id")["canonical_smiles"]
        .to_dict()
    )

    scaffolds: List[str] = []
    for drug_id in features["canonical_drug_id"].tolist():
        smiles = smiles_map.get(drug_id)
        if isinstance(smiles, str) and smiles.strip():
            scaffold = MurckoScaffold.MurckoScaffoldSmiles(smiles=smiles)
            scaffolds.append(scaffold if scaffold else f"NO_SCAFFOLD::{drug_id}")
        else:
            scaffolds.append(f"NO_SMILES::{drug_id}")
    return np.array(scaffolds)


def iter_splits(eval_mode: str, y: np.ndarray, groups: np.ndarray) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Create index splits for one eval mode."""
    if eval_mode == "holdout":
        idx = np.arange(len(y))
        tr, va = train_test_split(idx, test_size=0.2, random_state=42, shuffle=True)
        return [(tr, va)]
    if eval_mode == "cv5":
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        return list(kf.split(np.zeros(len(y))))
    if eval_mode in {"groupcv", "scaffoldcv"}:
        unique_groups = np.unique(groups)
        if len(unique_groups) < 3:
            raise ValueError(f"Need >=3 unique groups for {eval_mode}, got {len(unique_groups)}")
        gkf = GroupKFold(n_splits=3)
        return list(gkf.split(np.zeros(len(y)), y, groups=groups))
    raise ValueError(f"Unsupported eval mode: {eval_mode}")


def train_eval_model(
    model_name: str,
    model_obj: object,
    x: np.ndarray,
    y: np.ndarray,
    splits: List[Tuple[np.ndarray, np.ndarray]],
) -> Dict:
    """Fit one model across predefined splits and aggregate metrics."""
    fold_results: List[Dict] = []
    oof_pred = np.full(shape=(len(y),), fill_value=np.nan, dtype=np.float32)

    for fold_idx, (tr_idx, va_idx) in enumerate(splits, start=1):
        x_tr, y_tr = x[tr_idx], y[tr_idx]
        x_va, y_va = x[va_idx], y[va_idx]

        model = model_obj
        model.fit(x_tr, y_tr)
        tr_pred = model.predict(x_tr)
        va_pred = model.predict(x_va)
        oof_pred[va_idx] = va_pred.astype(np.float32)

        fold_results.append(
            {
                "fold": fold_idx,
                "n_train": int(len(tr_idx)),
                "n_val": int(len(va_idx)),
                "train": calculate_metrics(y_tr, tr_pred),
                "val": calculate_metrics(y_va, va_pred),
            }
        )

    train_sps = [x["train"]["spearman"] for x in fold_results]
    val_sps = [x["val"]["spearman"] for x in fold_results]
    return {
        "model_name": model_name,
        "n_folds": len(splits),
        "fold_results": fold_results,
        "summary": {
            "train_spearman_mean": float(np.mean(train_sps)),
            "val_spearman_mean": float(np.mean(val_sps)),
            "train_spearman_std": float(np.std(train_sps)),
            "val_spearman_std": float(np.std(val_sps)),
            "gap_spearman_mean": float(np.mean(np.array(train_sps) - np.array(val_sps))),
        },
        "overfitting_check": check_overfitting(fold_results),
        "stability_check": check_stability(fold_results),
        "oof_pred": oof_pred.tolist(),
    }


def run_phase(
    phase_name: str,
    x_file: Path,
    y: np.ndarray,
    groups_drug: np.ndarray,
    groups_scaffold: np.ndarray,
    eval_modes: List[str],
    results_dir: Path,
    output_stem: str,
) -> None:
    """Run all ML models for one phase input matrix."""
    log(f"Running {phase_name}: {x_file}")
    x = np.load(x_file)
    log(f"Loaded X shape: {x.shape}")
    if x.shape[0] != y.shape[0]:
        raise ValueError(f"Row mismatch for {x_file}: X={x.shape[0]}, y={y.shape[0]}")

    models = model_factories()
    log(f"Enabled models: {list(models.keys())}")
    if len(models) == 0:
        raise RuntimeError("No ML models are available in this environment.")

    for eval_mode in eval_modes:
        mode_groups = groups_scaffold if eval_mode == "scaffoldcv" else groups_drug
        splits = iter_splits(eval_mode, y, mode_groups)

        per_model: Dict[str, Dict] = {}
        oof_dir = results_dir / f"{output_stem}_{eval_mode}_oof"
        oof_dir.mkdir(parents=True, exist_ok=True)

        log(f"  Eval mode: {eval_mode}, n_splits={len(splits)}")
        for name, model in models.items():
            log(f"    Model: {name}")
            result = train_eval_model(name, model, x, y, splits)
            oof = np.array(result.pop("oof_pred"), dtype=np.float32)
            np.save(oof_dir / f"{name}.npy", oof)
            per_model[name] = result

        out_json = results_dir / f"{output_stem}_{eval_mode}.json"
        save_results(per_model, out_json)
        log(f"  Saved mode result: {out_json}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run STAD ML experiments")
    parser.add_argument("--run-id", default="step4_stad_inputs_v1")
    parser.add_argument("--result-tag", default="20260421_stad_step4_v1")
    parser.add_argument(
        "--eval-modes",
        default="holdout,cv5,groupcv,scaffoldcv",
        help="Comma-separated: holdout,cv5,groupcv,scaffoldcv",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data" / args.run_id
    results_dir = base_dir / "results" / args.result_tag / "ml"
    results_dir.mkdir(parents=True, exist_ok=True)

    features_slim_path = base_dir / "fe_qc" / "20260421_stad_fe_v1" / "features_slim.parquet"
    drug_features_path = data_dir / "drug_features.parquet"
    y_path = data_dir / "y_train.npy"

    for req in [features_slim_path, drug_features_path, y_path]:
        if not req.exists():
            raise FileNotFoundError(f"Missing required input: {req}")

    df_features = pd.read_parquet(features_slim_path, columns=["sample_id", "canonical_drug_id"])
    df_drugs = pd.read_parquet(drug_features_path, columns=["canonical_drug_id", "canonical_smiles"])
    y = np.load(y_path)
    groups_drug = df_features["canonical_drug_id"].values
    groups_scaffold = build_scaffold_groups(df_features, df_drugs)

    eval_modes = [x.strip() for x in args.eval_modes.split(",") if x.strip()]
    allowed = {"holdout", "cv5", "groupcv", "scaffoldcv"}
    invalid = [x for x in eval_modes if x not in allowed]
    if invalid:
        raise ValueError(f"Invalid eval modes: {invalid}, allowed={sorted(allowed)}")

    log("=" * 100)
    log("STAD Step 4 ML run start")
    log(f"run_id={args.run_id}")
    log(f"result_tag={args.result_tag}")
    log(f"eval_modes={eval_modes}")
    log(f"rows={len(y)}, unique_drugs={len(np.unique(groups_drug))}, unique_scaffolds={len(np.unique(groups_scaffold))}")
    log("=" * 100)

    run_phase(
        phase_name="Phase 2A",
        x_file=data_dir / "X_numeric.npy",
        y=y,
        groups_drug=groups_drug,
        groups_scaffold=groups_scaffold,
        eval_modes=eval_modes,
        results_dir=results_dir,
        output_stem="stad_numeric_ml_v1",
    )
    run_phase(
        phase_name="Phase 2B",
        x_file=data_dir / "X_numeric_smiles.npy",
        y=y,
        groups_drug=groups_drug,
        groups_scaffold=groups_scaffold,
        eval_modes=eval_modes,
        results_dir=results_dir,
        output_stem="stad_numeric_smiles_ml_v1",
    )
    run_phase(
        phase_name="Phase 2C",
        x_file=data_dir / "X_numeric_context_smiles.npy",
        y=y,
        groups_drug=groups_drug,
        groups_scaffold=groups_scaffold,
        eval_modes=eval_modes,
        results_dir=results_dir,
        output_stem="stad_numeric_context_smiles_ml_v1",
    )

    run_meta = {
        "run_id": args.run_id,
        "result_tag": args.result_tag,
        "eval_modes": eval_modes,
        "timestamp": datetime.now().isoformat(),
    }
    meta_path = results_dir / "run_meta_ml_stad.json"
    meta_path.write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    log(f"Saved run meta: {meta_path}")
    log("STAD Step 4 ML run complete")


if __name__ == "__main__":
    main()

