#!/usr/bin/env python3
"""Create CLAM-style tissue tile coordinates for SageMaker Processing."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import h5py
import numpy as np
import pandas as pd
from PIL import Image
from tqdm import tqdm

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.sagemaker_common_20260430_v1 import PIPELINE_TAG, ensure_processing_output_dirs, setup_logging

try:
    import openslide
except ImportError as exc:
    raise SystemExit("Install openslide-python plus openslide-tools/libopenslide0") from exc


def tissue_ratio(patch: Image.Image) -> float:
    arr = np.asarray(patch.convert("RGB"))
    brightness = arr.mean(axis=2)
    saturation = arr.max(axis=2) - arr.min(axis=2)
    mask = (brightness < 225) & (saturation > 18)
    return float(mask.mean())


def process_slide(svs_path: Path, out_dir: Path, patch_size: int, max_tiles: int, tissue_threshold: float) -> dict:
    slide_id = svs_path.stem
    slide = openslide.OpenSlide(str(svs_path))
    level = 0
    dims = slide.level_dimensions[level]
    coords = []
    checked = 0
    for y in tqdm(range(0, dims[1] - patch_size + 1, patch_size), desc=slide_id[:32], leave=False):
        for x in range(0, dims[0] - patch_size + 1, patch_size):
            checked += 1
            patch = slide.read_region((x, y), level, (patch_size, patch_size)).convert("RGB").resize((64, 64))
            if tissue_ratio(patch) >= tissue_threshold:
                coords.append((x, y))
                if max_tiles and len(coords) >= max_tiles:
                    break
        if max_tiles and len(coords) >= max_tiles:
            break
    slide.close()
    slide_out = out_dir / slide_id
    slide_out.mkdir(parents=True, exist_ok=True)
    coords_arr = np.asarray(coords, dtype=np.int64)
    with h5py.File(slide_out / f"coords_{PIPELINE_TAG}.h5", "w") as h5:
        h5.create_dataset("coords", data=coords_arr)
        h5.attrs["patch_size"] = patch_size
        h5.attrs["target_level"] = level
        h5.attrs["source_svs"] = str(svs_path)
    return {
        "slide_id": slide_id,
        "svs_path": str(svs_path),
        "status": "success",
        "n_tiles": int(len(coords_arr)),
        "checked_grid_tiles": int(checked),
        "tissue_fraction_grid": float(len(coords_arr) / max(checked, 1)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("/opt/ml/processing/input/wsi_raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("/opt/ml/processing/output/wsi_tiles"))
    parser.add_argument("--patch-size", type=int, default=256)
    parser.add_argument("--max-tiles-per-slide", type=int, default=10000)
    parser.add_argument("--tissue-threshold", type=float, default=0.5)
    args = parser.parse_args()

    ensure_processing_output_dirs()
    logger = setup_logging(Path("/opt/ml/processing/output/logs"), "step2_preprocessing_sagemaker")
    svs_files = sorted(args.input_dir.glob("*.svs"))
    logger.info("Found %d SVS files in %s", len(svs_files), args.input_dir)
    results = []
    for i, svs in enumerate(svs_files, 1):
        logger.info("[%d/%d] %s", i, len(svs_files), svs.name)
        try:
            res = process_slide(svs, args.output_dir, args.patch_size, args.max_tiles_per_slide, args.tissue_threshold)
            logger.info("  %s: tiles=%d tissue_grid=%.2f%%", res["slide_id"], res["n_tiles"], 100 * res["tissue_fraction_grid"])
        except Exception as exc:
            logger.exception("  failed: %s", exc)
            res = {"slide_id": svs.stem, "svs_path": str(svs), "status": "failed", "error": str(exc), "n_tiles": 0}
        results.append(res)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_csv(args.output_dir / f"tile_summary_{PIPELINE_TAG}.csv", index=False)
    ok = sum(r["status"] == "success" for r in results)
    logger.info("Step 2 complete: success=%d/%d tiles=%d", ok, len(results), sum(r["n_tiles"] for r in results))
    return 0 if ok == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
