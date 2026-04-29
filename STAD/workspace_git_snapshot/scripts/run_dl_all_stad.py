#!/usr/bin/env python3
"""
Run STAD Step 4 DL experiments (7 models x 3 phases x 4 eval modes).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import argparse
import copy
import json

import numpy as np
import pandas as pd
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.model_selection import GroupKFold, KFold, train_test_split
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from phase2_utils_stad import calculate_metrics, save_results
from data_validation_stad import check_overfitting, check_stability
from device_utils_stad import resolve_torch_device


def log(msg: str) -> None:
    """Timestamped log."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


@dataclass
class DLSpec:
    """DL model hyper-parameter set."""
    name: str
    hidden_dims: Tuple[int, ...]
    dropout: float
    activation: str
    use_bn: bool


class MLPRegressor(nn.Module):
    """Simple configurable MLP regressor."""

    def __init__(self, input_dim: int, spec: DLSpec) -> None:
        super().__init__()
        layers: List[nn.Module] = []
        prev = input_dim
        for dim in spec.hidden_dims:
            layers.append(nn.Linear(prev, dim))
            if spec.use_bn:
                layers.append(nn.BatchNorm1d(dim))
            if spec.activation == "relu":
                layers.append(nn.ReLU())
            elif spec.activation == "gelu":
                layers.append(nn.GELU())
            elif spec.activation == "selu":
                layers.append(nn.SELU())
            else:
                raise ValueError(f"Unsupported activation: {spec.activation}")
            if spec.dropout > 0:
                layers.append(nn.Dropout(spec.dropout))
            prev = dim
        layers.append(nn.Linear(prev, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def dl_specs() -> List[DLSpec]:
    """Return fixed 7 DL specs."""
    return [
        DLSpec("DL_MLP_2x512", (512, 512), 0.20, "relu", True),
        DLSpec("DL_MLP_3x512", (512, 512, 512), 0.25, "relu", True),
        DLSpec("DL_MLP_2x1024", (1024, 1024), 0.30, "relu", True),
        DLSpec("DL_MLP_1024_512_256", (1024, 512, 256), 0.25, "gelu", True),
        DLSpec("DL_MLP_SELU_3x256", (256, 256, 256), 0.10, "selu", False),
        DLSpec("DL_MLP_WideNarrow", (2048, 512, 128), 0.30, "gelu", True),
        DLSpec("DL_MLP_ResidualStyle", (768, 768, 384), 0.20, "relu", True),
    ]


def build_scaffold_groups(features: pd.DataFrame, drug_features: pd.DataFrame) -> np.ndarray:
    """Create scaffold group IDs aligned with features rows."""
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


def train_one_fold(
    x_tr: np.ndarray,
    y_tr: np.ndarray,
    x_va: np.ndarray,
    y_va: np.ndarray,
    spec: DLSpec,
    device: torch.device,
    max_epochs: int,
    batch_size: int,
    lr: float,
    patience: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Train one fold and return train/val predictions."""
    model = MLPRegressor(x_tr.shape[1], spec).to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

    ds_tr = TensorDataset(
        torch.from_numpy(x_tr.astype(np.float32)),
        torch.from_numpy(y_tr.astype(np.float32)),
    )
    loader = DataLoader(ds_tr, batch_size=batch_size, shuffle=True, drop_last=False)

    best_state = copy.deepcopy(model.state_dict())
    best_val = float("inf")
    bad_epochs = 0

    x_va_t = torch.from_numpy(x_va.astype(np.float32)).to(device)
    y_va_t = torch.from_numpy(y_va.astype(np.float32)).to(device)

    for _ in range(max_epochs):
        model.train()
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            optimizer.zero_grad(set_to_none=True)
            pred = model(xb)
            loss = criterion(pred, yb)
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            va_pred = model(x_va_t)
            va_loss = float(criterion(va_pred, y_va_t).item())
        if va_loss < best_val:
            best_val = va_loss
            best_state = copy.deepcopy(model.state_dict())
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                break

    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        tr_pred = model(torch.from_numpy(x_tr.astype(np.float32)).to(device)).cpu().numpy()
        va_pred = model(torch.from_numpy(x_va.astype(np.float32)).to(device)).cpu().numpy()
    return tr_pred, va_pred


def train_eval_model(
    spec: DLSpec,
    x: np.ndarray,
    y: np.ndarray,
    splits: List[Tuple[np.ndarray, np.ndarray]],
    device: torch.device,
    max_epochs: int,
    batch_size: int,
    lr: float,
    patience: int,
) -> Dict:
    """Fit one DL model across predefined splits and aggregate metrics."""
    fold_results: List[Dict] = []
    oof_pred = np.full(shape=(len(y),), fill_value=np.nan, dtype=np.float32)

    for fold_idx, (tr_idx, va_idx) in enumerate(splits, start=1):
        x_tr, y_tr = x[tr_idx], y[tr_idx]
        x_va, y_va = x[va_idx], y[va_idx]
        tr_pred, va_pred = train_one_fold(
            x_tr, y_tr, x_va, y_va, spec, device, max_epochs, batch_size, lr, patience
        )
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
        "model_name": spec.name,
        "n_folds": len(splits),
        "device": str(device),
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
    device: torch.device,
    max_epochs: int,
    batch_size: int,
    lr: float,
    patience: int,
) -> None:
    """Run all DL models for one phase matrix."""
    log(f"Running {phase_name}: {x_file}")
    x = np.load(x_file).astype(np.float32)
    if x.shape[0] != y.shape[0]:
        raise ValueError(f"Row mismatch for {x_file}: X={x.shape[0]}, y={y.shape[0]}")

    specs = dl_specs()
    for eval_mode in eval_modes:
        mode_groups = groups_scaffold if eval_mode == "scaffoldcv" else groups_drug
        splits = iter_splits(eval_mode, y, mode_groups)
        per_model: Dict[str, Dict] = {}
        oof_dir = results_dir / f"{output_stem}_{eval_mode}_oof"
        oof_dir.mkdir(parents=True, exist_ok=True)

        log(f"  Eval mode: {eval_mode}, n_splits={len(splits)}")
        for spec in specs:
            log(f"    Model: {spec.name}")
            try:
                result = train_eval_model(
                    spec, x, y, splits, device, max_epochs, batch_size, lr, patience
                )
            except RuntimeError as ex:
                err = str(ex).lower()
                if "mps" in err or "out of memory" in err:
                    log(f"    Device runtime issue on {device}: {ex}")
                    log("    Switching to CPU fallback and retrying.")
                    cpu_device = torch.device("cpu")
                    result = train_eval_model(
                        spec, x, y, splits, cpu_device, max_epochs, batch_size, lr, patience
                    )
                else:
                    raise

            oof = np.array(result.pop("oof_pred"), dtype=np.float32)
            np.save(oof_dir / f"{spec.name}.npy", oof)
            per_model[spec.name] = result

        out_json = results_dir / f"{output_stem}_{eval_mode}.json"
        save_results(per_model, out_json)
        log(f"  Saved mode result: {out_json}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run STAD DL experiments")
    parser.add_argument("--run-id", default="step4_stad_inputs_v1")
    parser.add_argument("--result-tag", default="20260421_stad_step4_v1")
    parser.add_argument("--max-epochs", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument(
        "--eval-modes",
        default="holdout,cv5,groupcv,scaffoldcv",
        help="Comma-separated: holdout,cv5,groupcv,scaffoldcv",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data" / args.run_id
    results_dir = base_dir / "results" / args.result_tag / "dl"
    results_dir.mkdir(parents=True, exist_ok=True)

    features_slim_path = base_dir / "fe_qc" / "20260421_stad_fe_v1" / "features_slim.parquet"
    drug_features_path = data_dir / "drug_features.parquet"
    y_path = data_dir / "y_train.npy"
    for req in [features_slim_path, drug_features_path, y_path]:
        if not req.exists():
            raise FileNotFoundError(f"Missing required input: {req}")

    df_features = pd.read_parquet(features_slim_path, columns=["sample_id", "canonical_drug_id"])
    df_drugs = pd.read_parquet(drug_features_path, columns=["canonical_drug_id", "canonical_smiles"])
    y = np.load(y_path).astype(np.float32)
    groups_drug = df_features["canonical_drug_id"].values
    groups_scaffold = build_scaffold_groups(df_features, df_drugs)

    eval_modes = [x.strip() for x in args.eval_modes.split(",") if x.strip()]
    allowed = {"holdout", "cv5", "groupcv", "scaffoldcv"}
    invalid = [x for x in eval_modes if x not in allowed]
    if invalid:
        raise ValueError(f"Invalid eval modes: {invalid}, allowed={sorted(allowed)}")

    device, reason = resolve_torch_device()
    log("=" * 100)
    log("STAD Step 4 DL run start")
    log(f"run_id={args.run_id}")
    log(f"result_tag={args.result_tag}")
    log(f"eval_modes={eval_modes}")
    log(f"device={device} ({reason})")
    log("=" * 100)

    run_phase(
        phase_name="Phase 2A",
        x_file=data_dir / "X_numeric.npy",
        y=y,
        groups_drug=groups_drug,
        groups_scaffold=groups_scaffold,
        eval_modes=eval_modes,
        results_dir=results_dir,
        output_stem="stad_numeric_dl_v1",
        device=device,
        max_epochs=args.max_epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        patience=args.patience,
    )
    run_phase(
        phase_name="Phase 2B",
        x_file=data_dir / "X_numeric_smiles.npy",
        y=y,
        groups_drug=groups_drug,
        groups_scaffold=groups_scaffold,
        eval_modes=eval_modes,
        results_dir=results_dir,
        output_stem="stad_numeric_smiles_dl_v1",
        device=device,
        max_epochs=args.max_epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        patience=args.patience,
    )
    run_phase(
        phase_name="Phase 2C",
        x_file=data_dir / "X_numeric_context_smiles.npy",
        y=y,
        groups_drug=groups_drug,
        groups_scaffold=groups_scaffold,
        eval_modes=eval_modes,
        results_dir=results_dir,
        output_stem="stad_numeric_context_smiles_dl_v1",
        device=device,
        max_epochs=args.max_epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        patience=args.patience,
    )

    run_meta = {
        "run_id": args.run_id,
        "result_tag": args.result_tag,
        "eval_modes": eval_modes,
        "device": str(device),
        "timestamp": datetime.now().isoformat(),
    }
    meta_path = results_dir / "run_meta_dl_stad.json"
    meta_path.write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    log(f"Saved run meta: {meta_path}")
    log("STAD Step 4 DL run complete")


if __name__ == "__main__":
    main()

