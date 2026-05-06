#!/usr/bin/env python3
"""Download TCGA diagnostic WSI files inside SageMaker Processing."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from pathlib import Path
import sys

import pandas as pd
import requests
from tqdm import tqdm

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.sagemaker_common_20260430_v1 import PIPELINE_TAG, ensure_processing_output_dirs, setup_logging, upload_file_to_s3

GDC_API_BASE = "https://api.gdc.cancer.gov"
GDC_FILES_ENDPOINT = f"{GDC_API_BASE}/files"
GDC_DATA_ENDPOINT = f"{GDC_API_BASE}/data"
CHUNK_SIZE = 1024 * 1024


def query_slides(projects: list[str], n_slides: int, logger: logging.Logger) -> list[dict]:
    size = 2000 if n_slides == 0 else n_slides
    logger.info("Querying GDC diagnostic slides: projects=%s n_slides=%s", ",".join(projects), n_slides or "ALL")
    filters = {
        "op": "and",
        "content": [
            {"op": "in", "content": {"field": "cases.project.project_id", "value": projects}},
            {"op": "=", "content": {"field": "data_type", "value": "Slide Image"}},
            {"op": "=", "content": {"field": "experimental_strategy", "value": "Diagnostic Slide"}},
            {"op": "=", "content": {"field": "data_format", "value": "SVS"}},
        ],
    }
    fields = [
        "file_id", "file_name", "file_size", "md5sum",
        "cases.case_id", "cases.submitter_id", "cases.samples.sample_type",
        "cases.project.project_id",
    ]
    params = {
        "filters": json.dumps(filters),
        "fields": ",".join(fields),
        "format": "JSON",
        "size": size,
        "sort": "file_size:asc",
    }
    response = requests.get(GDC_FILES_ENDPOINT, params=params, timeout=90)
    response.raise_for_status()
    data = response.json()["data"]
    total = data["pagination"]["total"]
    hits = data["hits"]
    if n_slides == 0 and total > len(hits):
        params["size"] = total
        response = requests.get(GDC_FILES_ENDPOINT, params=params, timeout=120)
        response.raise_for_status()
        hits = response.json()["data"]["hits"]
    slides = []
    for hit in hits:
        case = hit.get("cases", [{}])[0] if hit.get("cases") else {}
        project = case.get("project", {}).get("project_id", "")
        slides.append({
            "file_id": hit["file_id"],
            "file_name": hit["file_name"],
            "file_size_bytes": int(hit["file_size"]),
            "file_size_gb": round(int(hit["file_size"]) / (1024 ** 3), 3),
            "md5sum": hit.get("md5sum", ""),
            "case_id": case.get("case_id", ""),
            "submitter_id": case.get("submitter_id", ""),
            "project_id": project,
        })
    logger.info("GDC total=%d selected=%d selected_size=%.2f GB", total, len(slides), sum(s["file_size_gb"] for s in slides))
    return slides


def md5sum(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def download(slide: dict, output_dir: Path, logger: logging.Logger) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / slide["file_name"]
    result = dict(slide)
    result.update({"path": str(path), "status": "failed", "md5_verified": False})
    if path.exists() and slide["md5sum"] and md5sum(path) == slide["md5sum"]:
        result.update({"status": "skipped_existing", "md5_verified": True})
        return result
    url = f"{GDC_DATA_ENDPOINT}/{slide['file_id']}"
    for attempt in range(1, 4):
        try:
            with requests.get(url, stream=True, timeout=600) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                with path.open("wb") as f, tqdm(total=total, unit="B", unit_scale=True, desc=slide["file_name"][:42]) as bar:
                    for chunk in r.iter_content(CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            bar.update(len(chunk))
            if slide["md5sum"]:
                result["md5_verified"] = md5sum(path) == slide["md5sum"]
                if not result["md5_verified"]:
                    raise RuntimeError("MD5 mismatch")
            result["status"] = "success"
            return result
        except Exception as exc:
            logger.warning("Download attempt %d failed for %s: %s", attempt, slide["file_name"], exc)
            if path.exists():
                path.unlink()
            time.sleep(10 * attempt)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-slides", type=int, default=0)
    parser.add_argument("--projects", default="TCGA-BRCA")
    parser.add_argument("--output-dir", type=Path, default=Path("/opt/ml/processing/output/wsi_raw"))
    parser.add_argument("--s3-uri", default=None, help="Optional direct-upload S3 prefix")
    parser.add_argument("--query-only", action="store_true")
    args = parser.parse_args()

    ensure_processing_output_dirs()
    logger = setup_logging(Path("/opt/ml/processing/output/logs"), "step1_download_sagemaker")
    slides = query_slides([p.strip() for p in args.projects.split(",") if p.strip()], args.n_slides, logger)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / f"manifest_{PIPELINE_TAG}.csv"
    pd.DataFrame(slides).to_csv(manifest_path, index=False)
    (args.output_dir / f"metadata_{PIPELINE_TAG}.json").write_text(json.dumps(slides, indent=2), encoding="utf-8")
    if args.query_only:
        logger.info("Query-only mode complete: %s", manifest_path)
        return 0
    results = []
    for i, slide in enumerate(slides, 1):
        logger.info("[%d/%d] %s", i, len(slides), slide["file_name"])
        res = download(slide, args.output_dir, logger)
        results.append(res)
        if args.s3_uri and res["status"] in {"success", "skipped_existing"}:
            upload_file_to_s3(Path(res["path"]), args.s3_uri)
    results_path = args.output_dir / f"download_results_{PIPELINE_TAG}.csv"
    pd.DataFrame(results).to_csv(results_path, index=False)
    if args.s3_uri:
        upload_file_to_s3(manifest_path, args.s3_uri)
        upload_file_to_s3(results_path, args.s3_uri)
    ok = sum(r["status"] in {"success", "skipped_existing"} and r["md5_verified"] for r in results)
    logger.info("Step 1 complete: success=%d/%d", ok, len(results))
    return 0 if ok == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
