#!/usr/bin/env python3
"""Cancer-type wrapper for the 20260430_v1 image-modal SageMaker pipeline."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PIPELINE_TAG = "20260430_v1"
CANCER_MAP = {
    "BRCA": {"projects": ["TCGA-BRCA"], "existing": "20260428_new_BRCA_data"},
    "LUAD": {"projects": ["TCGA-LUAD"], "existing": ""},
    "CRC": {"projects": ["TCGA-COAD", "TCGA-READ"], "existing": ""},
    "STAD": {"projects": ["TCGA-STAD"], "existing": ""},
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cancer", required=True, choices=sorted(CANCER_MAP))
    parser.add_argument("--mode", choices=["full", "embedding", "reranking"], default="full")
    parser.add_argument("--n-slides", type=int, default=0)
    parser.add_argument("--existing-s3-uri", default=None)
    args = parser.parse_args()

    cancer = args.cancer.upper()
    base_uri = f"s3://say2-4team/{cancer}_image_modal_{PIPELINE_TAG}/"
    env = os.environ.copy()
    env["IMAGE_MODAL_CANCER"] = cancer
    env["IMAGE_MODAL_TCGA_PROJECTS"] = ",".join(CANCER_MAP[cancer]["projects"])
    env["IMAGE_MODAL_S3_BASE_URI"] = base_uri
    env["IMAGE_MODAL_EXISTING_HINT"] = CANCER_MAP[cancer]["existing"]

    runner = Path(__file__).resolve().parent / f"run_brca_image_sagemaker_{PIPELINE_TAG}.py"
    cmd = [
        sys.executable,
        str(runner),
        "--mode",
        args.mode,
        "--n-slides",
        str(args.n_slides),
    ]
    if args.existing_s3_uri:
        cmd.extend(["--existing-s3-uri", args.existing_s3_uri])

    print(f"[{cancer}] TCGA projects: {env['IMAGE_MODAL_TCGA_PROJECTS']}")
    print(f"[{cancer}] S3 base: {base_uri}")
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
