#!/usr/bin/env python3
"""
step1_wsi_download_tcga_brca_20260430_v1.py
===========================================
TCGA-BRCA H&E Diagnostic Slide(WSI) 다운로드 스크립트.

목적:
  - GDC Data Portal API로 BRCA diagnostic slide 목록을 쿼리
  - Pilot 50장을 선별하여 다운로드
  - 다운로드 매니페스트 및 메타데이터 저장

사용법:
  python step1_wsi_download_tcga_brca_20260430_v1.py

출력:
  - data/wsi_raw/*.svs              : WSI 원본 파일
  - data/wsi_raw/manifest_20260430_v1.csv : 다운로드 매니페스트
  - data/wsi_raw/metadata_20260430_v1.json : 슬라이드 메타데이터
  - logs/step1_download_20260430_v1.log

의존성:
  pip install requests tqdm pandas

작성일: 2026-04-30
버전: v1
"""

import os
import sys
import json
import time
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime

import requests
import pandas as pd
from tqdm import tqdm

# ============================================================
# 설정
# ============================================================
PIPELINE_DATE = "20260430"
PIPELINE_VERSION = "v1"
PIPELINE_TAG = f"{PIPELINE_DATE}_{PIPELINE_VERSION}"

# GDC API 설정
GDC_API_BASE = "https://api.gdc.cancer.gov"
GDC_FILES_ENDPOINT = f"{GDC_API_BASE}/files"
GDC_DATA_ENDPOINT = f"{GDC_API_BASE}/data"
GDC_CASES_ENDPOINT = f"{GDC_API_BASE}/cases"

# 기본 경로 (M4 Mac 로컬 기준)
DEFAULT_WORK_ROOT = Path.home() / "20260415_preproject_choi_protocol_v1_bisotest" / \
    "20260415_preproject_choi_protocol_v1_bisotest" / \
    "20260430_multimodal_BRCA_v1" / f"image_modal_{PIPELINE_TAG}"

# 다운로드 설정
DEFAULT_N_SLIDES = 50
CHUNK_SIZE = 8192  # 8KB chunks for download
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def setup_logging(log_dir: Path) -> logging.Logger:
    """로깅 설정."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"step1_download_{PIPELINE_TAG}.log"

    logger = logging.getLogger(f"step1_{PIPELINE_TAG}")
    logger.setLevel(logging.DEBUG)

    # 파일 핸들러
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)

    # 콘솔 핸들러
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def query_brca_diagnostic_slides(n_slides: int, logger: logging.Logger) -> list[dict]:
    """
    GDC API로 TCGA-BRCA diagnostic slide 목록을 쿼리.
    
    Returns:
        list of dict: 각 슬라이드의 file_id, file_name, file_size, md5sum,
                      case_id, submitter_id 등 메타데이터
    """
    logger.info(f"GDC API에서 TCGA-BRCA diagnostic slides 쿼리 중... (요청: {n_slides}장)")

    # GDC 필터: TCGA-BRCA, Slide Image, Diagnostic Slide, SVS
    filters = {
        "op": "and",
        "content": [
            {
                "op": "=",
                "content": {
                    "field": "cases.project.project_id",
                    "value": "TCGA-BRCA"
                }
            },
            {
                "op": "=",
                "content": {
                    "field": "data_type",
                    "value": "Slide Image"
                }
            },
            {
                "op": "=",
                "content": {
                    "field": "experimental_strategy",
                    "value": "Diagnostic Slide"
                }
            },
            {
                "op": "=",
                "content": {
                    "field": "data_format",
                    "value": "SVS"
                }
            }
        ]
    }

    # 요청 필드
    fields = [
        "file_id",
        "file_name",
        "file_size",
        "md5sum",
        "cases.case_id",
        "cases.submitter_id",
        "cases.diagnoses.tumor_stage",
        "cases.diagnoses.primary_diagnosis",
        "cases.demographic.gender",
        "cases.demographic.race",
        "cases.samples.sample_type",
    ]

    params = {
        "filters": json.dumps(filters),
        "fields": ",".join(fields),
        "format": "JSON",
        "size": n_slides,
        "sort": "file_size:asc",  # 작은 파일부터 (pilot용)
    }

    try:
        response = requests.get(GDC_FILES_ENDPOINT, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.error(f"GDC API 쿼리 실패: {e}")
        raise

    hits = data.get("data", {}).get("hits", [])
    total_available = data.get("data", {}).get("pagination", {}).get("total", 0)

    logger.info(f"전체 사용 가능: {total_available}장, 선택: {len(hits)}장")

    # 메타데이터 정리
    slides = []
    for hit in hits:
        case_info = hit.get("cases", [{}])[0] if hit.get("cases") else {}
        diagnosis = case_info.get("diagnoses", [{}])[0] if case_info.get("diagnoses") else {}
        demographic = case_info.get("demographic", {}) or {}

        slide = {
            "file_id": hit["file_id"],
            "file_name": hit["file_name"],
            "file_size_bytes": hit["file_size"],
            "file_size_gb": round(hit["file_size"] / (1024**3), 2),
            "md5sum": hit.get("md5sum", ""),
            "case_id": case_info.get("case_id", ""),
            "submitter_id": case_info.get("submitter_id", ""),
            "tumor_stage": diagnosis.get("tumor_stage", ""),
            "primary_diagnosis": diagnosis.get("primary_diagnosis", ""),
            "gender": demographic.get("gender", ""),
            "race": demographic.get("race", ""),
        }
        slides.append(slide)

    # 총 용량 계산
    total_gb = sum(s["file_size_gb"] for s in slides)
    logger.info(f"선택된 {len(slides)}장 총 용량: {total_gb:.1f} GB")

    return slides


def verify_md5(filepath: Path, expected_md5: str) -> bool:
    """다운로드된 파일의 MD5 검증."""
    md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE * 16), b""):
            md5.update(chunk)
    return md5.hexdigest() == expected_md5


def download_single_slide(
    file_id: str,
    file_name: str,
    expected_md5: str,
    output_dir: Path,
    logger: logging.Logger,
) -> dict:
    """
    단일 WSI 파일 다운로드 (재시도 로직 포함).
    
    Returns:
        dict: 다운로드 결과 (status, path, duration 등)
    """
    output_path = output_dir / file_name
    result = {
        "file_id": file_id,
        "file_name": file_name,
        "output_path": str(output_path),
        "status": "failed",
        "md5_verified": False,
        "duration_sec": 0,
    }

    # 이미 다운로드된 파일 확인
    if output_path.exists():
        if expected_md5 and verify_md5(output_path, expected_md5):
            logger.info(f"  이미 존재 & MD5 일치: {file_name}")
            result["status"] = "skipped_existing"
            result["md5_verified"] = True
            return result
        else:
            logger.warning(f"  파일 존재하나 MD5 불일치, 재다운로드: {file_name}")
            output_path.unlink()

    url = f"{GDC_DATA_ENDPOINT}/{file_id}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            start_time = time.time()
            logger.info(f"  다운로드 시작 (시도 {attempt}/{MAX_RETRIES}): {file_name}")

            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            # Content-Length로 프로그레스 바 설정
            total_size = int(response.headers.get("content-length", 0))

            with open(output_path, "wb") as f:
                with tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    desc=f"  {file_name[:40]}",
                    leave=False,
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

            duration = time.time() - start_time
            result["duration_sec"] = round(duration, 1)

            # MD5 검증
            if expected_md5:
                if verify_md5(output_path, expected_md5):
                    result["md5_verified"] = True
                    result["status"] = "success"
                    logger.info(
                        f"  ✓ 완료: {file_name} "
                        f"({result['duration_sec']}초, MD5 일치)"
                    )
                    return result
                else:
                    logger.warning(f"  MD5 불일치: {file_name}, 재시도...")
                    output_path.unlink()
                    continue
            else:
                result["status"] = "success"
                result["md5_verified"] = False  # MD5 없으면 검증 불가
                logger.info(f"  ✓ 완료: {file_name} ({result['duration_sec']}초)")
                return result

        except (requests.RequestException, IOError) as e:
            logger.warning(f"  다운로드 실패 (시도 {attempt}): {e}")
            if output_path.exists():
                output_path.unlink()
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    logger.error(f"  ✗ 최종 실패: {file_name}")
    return result


def save_manifest(
    slides: list[dict],
    download_results: list[dict],
    output_dir: Path,
    logger: logging.Logger,
) -> Path:
    """다운로드 매니페스트 저장."""
    manifest_path = output_dir / f"manifest_{PIPELINE_TAG}.csv"

    # slides와 results를 merge
    results_map = {r["file_id"]: r for r in download_results}

    records = []
    for slide in slides:
        result = results_map.get(slide["file_id"], {})
        record = {**slide, **result}
        records.append(record)

    df = pd.DataFrame(records)
    df.to_csv(manifest_path, index=False)
    logger.info(f"매니페스트 저장: {manifest_path}")

    return manifest_path


def save_metadata(slides: list[dict], output_dir: Path, logger: logging.Logger) -> Path:
    """슬라이드 메타데이터 JSON 저장."""
    metadata_path = output_dir / f"metadata_{PIPELINE_TAG}.json"

    metadata = {
        "pipeline": f"brca_image_modal_{PIPELINE_TAG}",
        "step": "step1_wsi_download",
        "created_at": datetime.now().isoformat(),
        "n_slides": len(slides),
        "total_size_gb": round(sum(s["file_size_gb"] for s in slides), 2),
        "source": "GDC Data Portal (TCGA-BRCA)",
        "data_type": "Diagnostic Slide (H&E, SVS)",
        "slides": slides,
    }

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info(f"메타데이터 저장: {metadata_path}")
    return metadata_path


def main():
    parser = argparse.ArgumentParser(
        description=f"Step 1: TCGA-BRCA WSI 다운로드 ({PIPELINE_TAG})"
    )
    parser.add_argument(
        "--n-slides", type=int, default=DEFAULT_N_SLIDES,
        help=f"다운로드할 슬라이드 수 (기본: {DEFAULT_N_SLIDES})"
    )
    parser.add_argument(
        "--work-root", type=str, default=str(DEFAULT_WORK_ROOT),
        help="작업 디렉토리 루트"
    )
    parser.add_argument(
        "--query-only", action="store_true",
        help="쿼리만 수행하고 다운로드하지 않음 (매니페스트 확인용)"
    )
    args = parser.parse_args()

    work_root = Path(args.work_root)
    wsi_dir = work_root / "data" / "wsi_raw"
    log_dir = work_root / "logs"

    # 디렉토리 생성
    wsi_dir.mkdir(parents=True, exist_ok=True)

    # 로깅 설정
    logger = setup_logging(log_dir)
    logger.info("=" * 60)
    logger.info(f"Step 1: TCGA-BRCA WSI 다운로드 시작 ({PIPELINE_TAG})")
    logger.info(f"  요청 슬라이드 수: {args.n_slides}")
    logger.info(f"  출력 디렉토리: {wsi_dir}")
    logger.info("=" * 60)

    # ---- 1) GDC API 쿼리 ----
    slides = query_brca_diagnostic_slides(args.n_slides, logger)

    if not slides:
        logger.error("슬라이드를 찾을 수 없습니다.")
        sys.exit(1)

    # 메타데이터 저장
    save_metadata(slides, wsi_dir, logger)

    # 쿼리 전용 모드
    if args.query_only:
        logger.info("--query-only 모드: 다운로드 없이 매니페스트만 생성")
        df = pd.DataFrame(slides)
        manifest_path = wsi_dir / f"manifest_{PIPELINE_TAG}.csv"
        df.to_csv(manifest_path, index=False)
        logger.info(f"매니페스트 저장: {manifest_path}")
        logger.info("쿼리 완료.")
        return

    # ---- 2) 다운로드 ----
    logger.info(f"\n총 {len(slides)}장 다운로드 시작...")
    download_results = []

    for i, slide in enumerate(slides, 1):
        logger.info(f"\n[{i}/{len(slides)}] {slide['file_name']} "
                     f"({slide['file_size_gb']} GB)")
        result = download_single_slide(
            file_id=slide["file_id"],
            file_name=slide["file_name"],
            expected_md5=slide["md5sum"],
            output_dir=wsi_dir,
            logger=logger,
        )
        download_results.append(result)

    # ---- 3) 결과 정리 ----
    success = sum(1 for r in download_results if r["status"] in ("success", "skipped_existing"))
    failed = sum(1 for r in download_results if r["status"] == "failed")

    logger.info("\n" + "=" * 60)
    logger.info(f"다운로드 완료 요약 ({PIPELINE_TAG})")
    logger.info(f"  성공: {success}/{len(slides)}")
    logger.info(f"  실패: {failed}/{len(slides)}")
    logger.info("=" * 60)

    # 매니페스트 저장
    save_manifest(slides, download_results, wsi_dir, logger)

    if failed > 0:
        logger.warning(f"{failed}개 파일 다운로드 실패. 매니페스트에서 실패 목록 확인 가능.")
        sys.exit(1)

    logger.info("Step 1 완료.")


if __name__ == "__main__":
    main()
