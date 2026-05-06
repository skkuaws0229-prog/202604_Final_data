#!/usr/bin/env python3
"""Install Processing dependencies, then run the requested pipeline step."""

from __future__ import annotations

import argparse
import runpy
import subprocess
import sys
from pathlib import Path

PIPELINE_TAG = "20260430_v1"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="Step script path relative to package root")
    parser.add_argument("target_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    mounted_package = Path("/opt/ml/processing/input/package")
    root = mounted_package if mounted_package.exists() else Path(__file__).resolve().parents[1]
    setup_script = root / f"sagemaker_setup_{PIPELINE_TAG}.sh"
    target_script = (root / args.target).resolve()

    if not target_script.exists():
        raise FileNotFoundError(f"Target step script not found: {target_script}")

    subprocess.check_call(["bash", str(setup_script)])

    target_args = args.target_args
    if target_args and target_args[0] == "--":
        target_args = target_args[1:]

    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "scripts"))
    sys.argv = [str(target_script)] + target_args
    runpy.run_path(str(target_script), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
