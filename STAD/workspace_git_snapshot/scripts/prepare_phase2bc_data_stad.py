#!/usr/bin/env python3
"""
Prepare STAD Step 4 Phase 2B/2C inputs.

Phase 2B:
- X_numeric_smiles.npy
- smiles_token_ids.npy

Phase 2C:
- context_codes.npy
- X_numeric_context_smiles.npy
- context_vocab.json
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List
import json
import argparse

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import AllChem


def log(msg: str) -> None:
    """Print timestamped message."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


def smiles_to_fingerprint(smiles: str, radius: int = 2, n_bits: int = 64) -> np.ndarray:
    """Convert SMILES to Morgan fingerprint vector."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return np.zeros(n_bits, dtype=np.float32)
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
        return np.array(fp, dtype=np.float32)
    except Exception:
        return np.zeros(n_bits, dtype=np.float32)


def tokenize_smiles(smiles: str, max_len: int = 256) -> np.ndarray:
    """Character-level SMILES tokenization."""
    chars: List[str] = [
        "<PAD>", "<START>", "<END>", "<UNK>",
        "C", "c", "O", "N", "n", "S", "s", "F", "Cl", "Br", "I",
        "(", ")", "[", "]", "=", "#", "@", "+", "-", "/", "\\",
        "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
    ]
    char_to_idx: Dict[str, int] = {c: i for i, c in enumerate(chars)}

    tokens: List[int] = [char_to_idx["<START>"]]
    if smiles and isinstance(smiles, str):
        for ch in smiles[: max_len - 2]:
            tokens.append(char_to_idx.get(ch, char_to_idx["<UNK>"]))
    tokens.append(char_to_idx["<END>"])

    while len(tokens) < max_len:
        tokens.append(char_to_idx["<PAD>"])
    return np.array(tokens[:max_len], dtype=np.int32)


def create_context_features(drug_ids: List[str], context_dim: int = 64) -> Dict[str, np.ndarray]:
    """Create deterministic hash-based context vectors per drug."""
    out: Dict[str, np.ndarray] = {}
    for drug_id in drug_ids:
        np.random.seed(hash(str(drug_id)) % 2**32)
        out[str(drug_id)] = (np.random.randn(context_dim) * 0.1).astype(np.float32)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare STAD Phase 2B/2C input arrays")
    parser.add_argument(
        "--run-id",
        default="step4_stad_inputs_v1",
        help="Subdirectory under data/ used by prepare_phase2a_data_stad.py",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting existing Phase 2B/2C arrays for this run-id",
    )
    args = parser.parse_args()

    base_dir: Path = Path(__file__).resolve().parents[1]
    data_dir: Path = base_dir / "data" / args.run_id
    features_slim_path: Path = base_dir / "fe_qc" / "20260421_stad_fe_v1" / "features_slim.parquet"
    drug_features_path: Path = data_dir / "drug_features.parquet"

    x_numeric_path: Path = data_dir / "X_numeric.npy"
    y_train_path: Path = data_dir / "y_train.npy"

    log("=" * 90)
    log("Phase 2B/2C input preparation (STAD)")
    log("=" * 90)

    for req in [x_numeric_path, y_train_path, features_slim_path, drug_features_path]:
        if not req.exists():
            raise FileNotFoundError(f"Missing required file: {req}")
        log(f"Found: {req}")

    output_targets: List[Path] = [
        data_dir / "X_numeric_smiles.npy",
        data_dir / "smiles_token_ids.npy",
        data_dir / "context_codes.npy",
        data_dir / "X_numeric_context_smiles.npy",
        data_dir / "context_vocab.json",
    ]
    if not args.force and any(p.exists() for p in output_targets):
        raise FileExistsError(
            f"Some outputs already exist under {data_dir}. "
            "Use a new --run-id or pass --force."
        )

    x_numeric: np.ndarray = np.load(x_numeric_path)
    _y_train: np.ndarray = np.load(y_train_path)
    df_features: pd.DataFrame = pd.read_parquet(features_slim_path, columns=["sample_id", "canonical_drug_id"])
    df_drugs: pd.DataFrame = pd.read_parquet(drug_features_path, columns=["canonical_drug_id", "canonical_smiles"])

    log(f"X_numeric shape: {x_numeric.shape}")
    log(f"Feature rows: {len(df_features)}")
    log(f"Unique drugs in features: {df_features['canonical_drug_id'].nunique()}")

    df_merged: pd.DataFrame = df_features.merge(
        df_drugs[["canonical_drug_id", "canonical_smiles"]],
        on="canonical_drug_id",
        how="left",
    )
    smiles_cov: float = float(df_merged["canonical_smiles"].notna().mean() * 100.0)
    log(f"SMILES coverage: {smiles_cov:.1f}%")

    # Phase 2B SMILES fingerprints
    log("Generating 64-bit Morgan fingerprints...")
    smiles_fps: List[np.ndarray] = []
    for idx, smiles in enumerate(df_merged["canonical_smiles"].tolist(), start=1):
        if pd.isna(smiles):
            smiles_fps.append(np.zeros(64, dtype=np.float32))
        else:
            smiles_fps.append(smiles_to_fingerprint(str(smiles), n_bits=64))
        if idx % 1000 == 0:
            log(f"Fingerprint progress: {idx}/{len(df_merged)}")
    smiles_fp_arr: np.ndarray = np.array(smiles_fps, dtype=np.float32)

    x_numeric_smiles: np.ndarray = np.concatenate([x_numeric, smiles_fp_arr], axis=1)
    np.save(data_dir / "X_numeric_smiles.npy", x_numeric_smiles)
    log(f"Saved: {data_dir / 'X_numeric_smiles.npy'} shape={x_numeric_smiles.shape}")

    # Token IDs
    log("Generating SMILES token IDs...")
    token_rows: List[np.ndarray] = []
    for idx, smiles in enumerate(df_merged["canonical_smiles"].tolist(), start=1):
        if pd.isna(smiles):
            token_rows.append(np.zeros(256, dtype=np.int32))
        else:
            token_rows.append(tokenize_smiles(str(smiles), max_len=256))
        if idx % 1000 == 0:
            log(f"Token progress: {idx}/{len(df_merged)}")
    smiles_tokens: np.ndarray = np.array(token_rows, dtype=np.int32)
    np.save(data_dir / "smiles_token_ids.npy", smiles_tokens)
    log(f"Saved: {data_dir / 'smiles_token_ids.npy'} shape={smiles_tokens.shape}")

    # Phase 2C context
    log("Generating context vectors...")
    unique_drug_ids: List[str] = [str(x) for x in df_drugs["canonical_drug_id"].dropna().astype(str).tolist()]
    drug_to_context: Dict[str, np.ndarray] = create_context_features(unique_drug_ids, context_dim=64)
    context_rows: List[np.ndarray] = [
        drug_to_context.get(str(drug_id), np.zeros(64, dtype=np.float32))
        for drug_id in df_merged["canonical_drug_id"].tolist()
    ]
    context_arr: np.ndarray = np.array(context_rows, dtype=np.float32)
    np.save(data_dir / "context_codes.npy", context_arr)
    log(f"Saved: {data_dir / 'context_codes.npy'} shape={context_arr.shape}")

    x_numeric_context_smiles: np.ndarray = np.concatenate([x_numeric, context_arr, smiles_fp_arr], axis=1)
    np.save(data_dir / "X_numeric_context_smiles.npy", x_numeric_context_smiles)
    log(
        f"Saved: {data_dir / 'X_numeric_context_smiles.npy'} "
        f"shape={x_numeric_context_smiles.shape}"
    )

    context_vocab_path: Path = data_dir / "context_vocab.json"
    context_vocab_path.write_text(
        json.dumps(
            {
                "context_dim": 64,
                "description": "Drug context embeddings (hash-based, STAD)",
                "num_drugs": len(drug_to_context),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    log(f"Saved: {context_vocab_path}")

    log("=" * 90)
    log("Phase 2B/2C preparation complete (STAD)")
    log(f"Phase 2A: X_numeric {x_numeric.shape}")
    log(f"Phase 2B: X_numeric_smiles {x_numeric_smiles.shape}")
    log(f"Phase 2C: X_numeric_context_smiles {x_numeric_context_smiles.shape}")
    log("=" * 90)


if __name__ == "__main__":
    main()

