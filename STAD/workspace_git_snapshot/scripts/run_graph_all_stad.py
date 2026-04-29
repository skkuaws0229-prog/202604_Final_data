#!/usr/bin/env python3
"""
Run STAD Step 4 Graph experiments (GraphSAGE, GAT).
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
from sklearn.neighbors import NearestNeighbors
import torch
from torch import nn

from phase2_utils_stad import calculate_metrics, save_results
from data_validation_stad import check_overfitting, check_stability
from device_utils_stad import resolve_torch_device

try:
    from torch_geometric.data import Data
    from torch_geometric.nn import GATConv, SAGEConv
except Exception as ex:  # pragma: no cover
    raise ImportError(
        "torch_geometric is required for run_graph_all_stad.py. "
        "Install torch-geometric in the current environment."
    ) from ex


def log(msg: str) -> None:
    """Timestamped log."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


@dataclass
class GraphSpec:
    """Graph model configuration."""
    name: str
    kind: str  # 'sage' or 'gat'
    hidden_dim: int = 128
    dropout: float = 0.20
    heads: int = 4


class GraphSAGERegressor(nn.Module):
    """Two-layer GraphSAGE regressor."""

    def __init__(self, input_dim: int, hidden_dim: int, dropout: float) -> None:
        super().__init__()
        self.conv1 = SAGEConv(input_dim, hidden_dim)
        self.conv2 = SAGEConv(hidden_dim, hidden_dim)
        self.head = nn.Linear(hidden_dim, 1)
        self.dropout = dropout

    def forward(self, data: Data) -> torch.Tensor:
        x, edge_index = data.x, data.edge_index
        x = self.conv1(x, edge_index).relu()
        x = nn.functional.dropout(x, p=self.dropout, training=self.training)
        x = self.conv2(x, edge_index).relu()
        x = nn.functional.dropout(x, p=self.dropout, training=self.training)
        return self.head(x).squeeze(-1)


class GATRegressor(nn.Module):
    """Two-layer GAT regressor."""

    def __init__(self, input_dim: int, hidden_dim: int, heads: int, dropout: float) -> None:
        super().__init__()
        self.conv1 = GATConv(input_dim, hidden_dim, heads=heads, dropout=dropout)
        self.conv2 = GATConv(hidden_dim * heads, hidden_dim, heads=1, dropout=dropout)
        self.head = nn.Linear(hidden_dim, 1)
        self.dropout = dropout

    def forward(self, data: Data) -> torch.Tensor:
        x, edge_index = data.x, data.edge_index
        x = self.conv1(x, edge_index).relu()
        x = nn.functional.dropout(x, p=self.dropout, training=self.training)
        x = self.conv2(x, edge_index).relu()
        x = nn.functional.dropout(x, p=self.dropout, training=self.training)
        return self.head(x).squeeze(-1)


def graph_specs() -> List[GraphSpec]:
    """Return 2 graph model definitions."""
    return [
        GraphSpec(name="GraphSAGE", kind="sage", hidden_dim=128, dropout=0.20, heads=1),
        GraphSpec(name="GAT", kind="gat", hidden_dim=96, dropout=0.25, heads=4),
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


def select_top_variance_features(x: np.ndarray, top_k: int) -> np.ndarray:
    """Reduce feature dimension for graph training speed/stability."""
    if x.shape[1] <= top_k:
        return x
    vars_ = np.var(x, axis=0)
    idx = np.argsort(vars_)[::-1][:top_k]
    return x[:, idx]


def build_knn_edge_index(x: np.ndarray, k_neighbors: int) -> torch.Tensor:
    """Build directed edge index from kNN graph."""
    knn = NearestNeighbors(n_neighbors=k_neighbors + 1, metric="euclidean")
    knn.fit(x)
    indices = knn.kneighbors(x, return_distance=False)
    src: List[int] = []
    dst: List[int] = []
    for i, neigh in enumerate(indices):
        for j in neigh[1:]:
            src.append(i)
            dst.append(int(j))
    edge_index = torch.tensor([src, dst], dtype=torch.long)
    return edge_index


def build_model(spec: GraphSpec, input_dim: int) -> nn.Module:
    """Build graph model instance from spec."""
    if spec.kind == "sage":
        return GraphSAGERegressor(input_dim, spec.hidden_dim, spec.dropout)
    if spec.kind == "gat":
        return GATRegressor(input_dim, spec.hidden_dim, spec.heads, spec.dropout)
    raise ValueError(f"Unknown graph model kind: {spec.kind}")


def train_eval_model(
    spec: GraphSpec,
    x: np.ndarray,
    y: np.ndarray,
    edge_index: torch.Tensor,
    splits: List[Tuple[np.ndarray, np.ndarray]],
    device: torch.device,
    max_epochs: int,
    lr: float,
    patience: int,
) -> Dict:
    """Train one graph model across splits."""
    fold_results: List[Dict] = []
    oof_pred = np.full(shape=(len(y),), fill_value=np.nan, dtype=np.float32)
    criterion = nn.MSELoss()

    x_t = torch.from_numpy(x.astype(np.float32)).to(device)
    y_t = torch.from_numpy(y.astype(np.float32)).to(device)
    edge_index_t = edge_index.to(device)

    for fold_idx, (tr_idx, va_idx) in enumerate(splits, start=1):
        train_mask = torch.zeros(len(y), dtype=torch.bool, device=device)
        val_mask = torch.zeros(len(y), dtype=torch.bool, device=device)
        train_mask[torch.from_numpy(tr_idx).to(device)] = True
        val_mask[torch.from_numpy(va_idx).to(device)] = True

        data = Data(x=x_t, edge_index=edge_index_t, y=y_t)
        model = build_model(spec, input_dim=x.shape[1]).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

        best_state = copy.deepcopy(model.state_dict())
        best_val = float("inf")
        bad_epochs = 0

        for _ in range(max_epochs):
            model.train()
            optimizer.zero_grad(set_to_none=True)
            pred = model(data)
            loss = criterion(pred[train_mask], y_t[train_mask])
            loss.backward()
            optimizer.step()

            model.eval()
            with torch.no_grad():
                val_pred = model(data)
                val_loss = float(criterion(val_pred[val_mask], y_t[val_mask]).item())
            if val_loss < best_val:
                best_val = val_loss
                best_state = copy.deepcopy(model.state_dict())
                bad_epochs = 0
            else:
                bad_epochs += 1
                if bad_epochs >= patience:
                    break

        model.load_state_dict(best_state)
        model.eval()
        with torch.no_grad():
            pred_all = model(data).detach().cpu().numpy()
        y_tr = y[tr_idx]
        y_va = y[va_idx]
        tr_pred = pred_all[tr_idx]
        va_pred = pred_all[va_idx]
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
    lr: float,
    patience: int,
    k_neighbors: int,
    fs_top_k: int,
) -> None:
    """Run graph models for one phase matrix."""
    log(f"Running {phase_name}: {x_file}")
    x_full = np.load(x_file).astype(np.float32)
    if x_full.shape[0] != y.shape[0]:
        raise ValueError(f"Row mismatch for {x_file}: X={x_full.shape[0]}, y={y.shape[0]}")

    x = select_top_variance_features(x_full, fs_top_k)
    log(f"Feature reduction: {x_full.shape[1]} -> {x.shape[1]} (top variance)")
    edge_index = build_knn_edge_index(x, k_neighbors=k_neighbors)
    log(f"edge_index shape: {tuple(edge_index.shape)}")

    for eval_mode in eval_modes:
        mode_groups = groups_scaffold if eval_mode == "scaffoldcv" else groups_drug
        splits = iter_splits(eval_mode, y, mode_groups)
        per_model: Dict[str, Dict] = {}
        oof_dir = results_dir / f"{output_stem}_{eval_mode}_oof"
        oof_dir.mkdir(parents=True, exist_ok=True)

        log(f"  Eval mode: {eval_mode}, n_splits={len(splits)}")
        for spec in graph_specs():
            log(f"    Model: {spec.name}")
            try:
                result = train_eval_model(
                    spec, x, y, edge_index, splits, device, max_epochs, lr, patience
                )
            except RuntimeError as ex:
                err = str(ex).lower()
                if "mps" in err or "out of memory" in err:
                    log(f"    Device runtime issue on {device}: {ex}")
                    log("    Switching to CPU fallback and retrying.")
                    result = train_eval_model(
                        spec,
                        x,
                        y,
                        edge_index,
                        splits,
                        torch.device("cpu"),
                        max_epochs,
                        lr,
                        patience,
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
    parser = argparse.ArgumentParser(description="Run STAD Graph experiments")
    parser.add_argument("--run-id", default="step4_stad_inputs_v1")
    parser.add_argument("--result-tag", default="20260421_stad_step4_v1")
    parser.add_argument("--max-epochs", type=int, default=80)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--k-neighbors", type=int, default=7)
    parser.add_argument("--fs-top-k", type=int, default=1000)
    parser.add_argument(
        "--eval-modes",
        default="holdout,cv5,groupcv,scaffoldcv",
        help="Comma-separated: holdout,cv5,groupcv,scaffoldcv",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data" / args.run_id
    results_dir = base_dir / "results" / args.result_tag / "graph"
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
    log("STAD Step 4 Graph run start")
    log(f"run_id={args.run_id}")
    log(f"result_tag={args.result_tag}")
    log(f"eval_modes={eval_modes}")
    log(f"device={device} ({reason})")
    log(f"k_neighbors={args.k_neighbors}, fs_top_k={args.fs_top_k}")
    log("=" * 100)

    run_phase(
        phase_name="Phase 2A",
        x_file=data_dir / "X_numeric.npy",
        y=y,
        groups_drug=groups_drug,
        groups_scaffold=groups_scaffold,
        eval_modes=eval_modes,
        results_dir=results_dir,
        output_stem="stad_numeric_graph_v1",
        device=device,
        max_epochs=args.max_epochs,
        lr=args.lr,
        patience=args.patience,
        k_neighbors=args.k_neighbors,
        fs_top_k=args.fs_top_k,
    )
    run_phase(
        phase_name="Phase 2B",
        x_file=data_dir / "X_numeric_smiles.npy",
        y=y,
        groups_drug=groups_drug,
        groups_scaffold=groups_scaffold,
        eval_modes=eval_modes,
        results_dir=results_dir,
        output_stem="stad_numeric_smiles_graph_v1",
        device=device,
        max_epochs=args.max_epochs,
        lr=args.lr,
        patience=args.patience,
        k_neighbors=args.k_neighbors,
        fs_top_k=args.fs_top_k,
    )
    run_phase(
        phase_name="Phase 2C",
        x_file=data_dir / "X_numeric_context_smiles.npy",
        y=y,
        groups_drug=groups_drug,
        groups_scaffold=groups_scaffold,
        eval_modes=eval_modes,
        results_dir=results_dir,
        output_stem="stad_numeric_context_smiles_graph_v1",
        device=device,
        max_epochs=args.max_epochs,
        lr=args.lr,
        patience=args.patience,
        k_neighbors=args.k_neighbors,
        fs_top_k=args.fs_top_k,
    )

    run_meta = {
        "run_id": args.run_id,
        "result_tag": args.result_tag,
        "eval_modes": eval_modes,
        "device": str(device),
        "timestamp": datetime.now().isoformat(),
    }
    meta_path = results_dir / "run_meta_graph_stad.json"
    meta_path.write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    log(f"Saved run meta: {meta_path}")
    log("STAD Step 4 Graph run complete")


if __name__ == "__main__":
    main()

