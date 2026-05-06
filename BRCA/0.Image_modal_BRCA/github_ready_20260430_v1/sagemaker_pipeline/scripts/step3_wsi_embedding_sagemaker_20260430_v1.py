#!/usr/bin/env python3
"""Extract UNI2 or fallback ViT-Large WSI tile embeddings on SageMaker CUDA."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import h5py
import numpy as np
import pandas as pd
import torch
from tqdm import tqdm

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.sagemaker_common_20260430_v1 import EMBEDDING_DIM, PIPELINE_TAG, ensure_processing_output_dirs, setup_logging

try:
    import openslide
    import timm
    from timm.data import resolve_data_config
    from timm.data.transforms_factory import create_transform
    import torchvision.transforms as T
except ImportError as exc:
    raise SystemExit("Install openslide-python, timm, torch, torchvision") from exc

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def load_model(device: str, logger):
    token = os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token:
        os.environ.setdefault("HF_TOKEN", token)
    model_used = "UNI2"
    try:
        logger.info("Loading UNI2: hf-hub:MahmoodLab/UNI2-h")
        timm_kwargs = {
            "img_size": 224,
            "patch_size": 14,
            "depth": 24,
            "num_heads": 24,
            "init_values": 1e-5,
            "embed_dim": 1536,
            "mlp_ratio": 2.66667 * 2,
            "num_classes": 0,
            "no_embed_class": True,
            "mlp_layer": timm.layers.SwiGLUPacked,
            "act_layer": torch.nn.SiLU,
            "reg_tokens": 8,
            "dynamic_img_size": True,
        }
        model = timm.create_model("hf-hub:MahmoodLab/UNI2-h", pretrained=True, **timm_kwargs)
    except Exception as exc:
        logger.warning("UNI2 load failed, falling back to ViT-Large ImageNet: %s", exc)
        model_used = "ViT-Large"
        model = timm.create_model("vit_large_patch16_224", pretrained=True, num_classes=0)
    model = model.to(device).eval()
    for p in model.parameters():
        p.requires_grad = False
    feature_dim = int(getattr(model, "num_features", EMBEDDING_DIM))
    tfm = create_transform(**resolve_data_config(model.pretrained_cfg, model=model))
    logger.info(
        "Model used: %s, params=%.1fM, dim=%d, device=%s",
        model_used,
        sum(p.numel() for p in model.parameters()) / 1e6,
        feature_dim,
        device,
    )
    return model, model_used, tfm, feature_dim


def transform():
    return T.Compose([
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


def read_coords(path: Path):
    with h5py.File(path, "r") as h5:
        return h5["coords"][:], int(h5.attrs["patch_size"]), int(h5.attrs["target_level"])


def embed_slide(
    svs_path: Path,
    coords_h5: Path,
    model,
    tfm,
    device: str,
    batch_size: int,
    out_dir: Path,
    model_used: str,
    embedding_dim: int,
):
    coords, patch_size, level = read_coords(coords_h5)
    slide = openslide.OpenSlide(str(svs_path))
    embs = []
    for start in tqdm(range(0, len(coords), batch_size), desc=svs_path.stem[:32], leave=False):
        batch_coords = coords[start:start + batch_size]
        tensors = []
        for x, y in batch_coords:
            patch = slide.read_region((int(x), int(y)), level, (patch_size, patch_size)).convert("RGB")
            tensors.append(tfm(patch))
        x_tensor = torch.stack(tensors).to(device)
        with torch.no_grad():
            y_tensor = model(x_tensor.float())
        embs.append(y_tensor.detach().cpu().numpy())
    slide.close()
    tile_embeddings = np.concatenate(embs, axis=0).astype(np.float32) if embs else np.empty((0, embedding_dim), dtype=np.float32)
    slide_embedding = tile_embeddings.mean(axis=0).astype(np.float32) if len(tile_embeddings) else np.zeros(embedding_dim, dtype=np.float32)

    slide_out = out_dir / "wsi_embeddings" / svs_path.stem
    slide_out.mkdir(parents=True, exist_ok=True)
    with h5py.File(slide_out / f"tile_embeddings_{PIPELINE_TAG}.h5", "w") as h5:
        h5.create_dataset("embeddings", data=tile_embeddings, compression="gzip")
        h5.create_dataset("coords", data=coords, compression="gzip")
        h5.attrs["model_used"] = model_used
        h5.attrs["n_tiles"] = len(tile_embeddings)
        h5.attrs["embedding_dim"] = tile_embeddings.shape[1] if len(tile_embeddings) else EMBEDDING_DIM

    slide_emb_dir = out_dir / "slide_embeddings"
    slide_emb_dir.mkdir(parents=True, exist_ok=True)
    np.save(slide_emb_dir / f"slide_embedding_{svs_path.stem}_{PIPELINE_TAG}.npy", slide_embedding)
    return {
        "slide_id": svs_path.stem,
        "n_tiles": int(len(tile_embeddings)),
        "embedding_dim": int(slide_embedding.shape[0]),
        "model_used": model_used,
        **{f"emb_{i}": float(v) for i, v in enumerate(slide_embedding)},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wsi-dir", type=Path, default=Path("/opt/ml/processing/input/wsi_raw"))
    parser.add_argument("--tiles-dir", type=Path, default=Path("/opt/ml/processing/input/wsi_tiles"))
    parser.add_argument("--output-dir", type=Path, default=Path("/opt/ml/processing/output/embeddings"))
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--model-label", default=None)
    args = parser.parse_args()

    ensure_processing_output_dirs()
    logger = setup_logging(Path("/opt/ml/processing/output/logs"), "step3_embedding_sagemaker")
    device = args.device if args.device == "cuda" and torch.cuda.is_available() else "cpu"
    model, model_used, tfm, embedding_dim = load_model(device, logger)
    if args.model_label:
        model_used = args.model_label if model_used == "UNI2" else f"{args.model_label}_fallback_{model_used}"
    coord_files = sorted(args.tiles_dir.glob(f"*/coords_{PIPELINE_TAG}.h5"))
    records = []
    for i, coords_h5 in enumerate(coord_files, 1):
        slide_id = coords_h5.parent.name
        svs_path = args.wsi_dir / f"{slide_id}.svs"
        logger.info("[%d/%d] %s", i, len(coord_files), slide_id)
        if not svs_path.exists():
            logger.warning("SVS missing: %s", svs_path)
            continue
        rec = embed_slide(svs_path, coords_h5, model, tfm, device, args.batch_size, args.output_dir, model_used, embedding_dim)
        records.append(rec)
        logger.info("  %s: %d tiles -> %dd", slide_id, rec["n_tiles"], rec["embedding_dim"])
    df = pd.DataFrame(records)
    slide_dir = args.output_dir / "slide_embeddings"
    slide_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(slide_dir / f"all_slide_embeddings_{PIPELINE_TAG}.parquet", index=False)
    (slide_dir / f"embedding_metadata_{PIPELINE_TAG}.json").write_text(
        json.dumps({"model_used": model_used, "n_slides": len(records), "device": device, "batch_size": args.batch_size}, indent=2),
        encoding="utf-8",
    )
    logger.info("Step 3 complete: slides=%d model_used=%s", len(records), model_used)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
