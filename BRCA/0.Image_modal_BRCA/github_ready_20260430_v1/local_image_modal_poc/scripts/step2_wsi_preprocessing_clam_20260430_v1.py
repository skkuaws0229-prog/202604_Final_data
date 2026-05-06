#!/usr/bin/env python3
"""
step2_wsi_preprocessing_clam_20260430_v1.py
===========================================
CLAM 기반 WSI 전처리: 조직 영역 검출 + 타일링 (256×256).

목적:
  - OpenSlide로 WSI 로드
  - Otsu thresholding으로 조직 영역 검출 (배경 제거)
  - 256×256 패치로 타일링
  - 좌표 + 메타데이터를 H5 파일로 저장

사용법:
  python step2_wsi_preprocessing_clam_20260430_v1.py
  python step2_wsi_preprocessing_clam_20260430_v1.py --patch-size 512

입력:
  - data/wsi_raw/*.svs (Step 1에서 다운로드한 WSI)

출력:
  - data/wsi_tiles/{slide_id}/patches/     : 타일 이미지 (선택적 저장)
  - data/wsi_tiles/{slide_id}/coords.h5    : 타일 좌표
  - data/wsi_tiles/tile_summary_20260430_v1.csv : 타일링 요약
  - logs/step2_preprocessing_20260430_v1.log

의존성:
  pip install openslide-python opencv-python-headless h5py numpy pandas Pillow tqdm

macOS 추가:
  brew install openslide

작성일: 2026-04-30
버전: v1
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

import cv2
import h5py
import numpy as np
import pandas as pd
from PIL import Image
from tqdm import tqdm

try:
    import openslide
except ImportError:
    print("openslide-python이 필요합니다.")
    print("  brew install openslide  (macOS)")
    print("  pip install openslide-python")
    sys.exit(1)

# ============================================================
# 설정
# ============================================================
PIPELINE_DATE = "20260430"
PIPELINE_VERSION = "v1"
PIPELINE_TAG = f"{PIPELINE_DATE}_{PIPELINE_VERSION}"

DEFAULT_WORK_ROOT = Path.home() / "20260415_preproject_choi_protocol_v1_bisotest" / \
    "20260415_preproject_choi_protocol_v1_bisotest" / \
    "20260430_multimodal_BRCA_v1" / f"image_modal_{PIPELINE_TAG}"

DEFAULT_PATCH_SIZE = 256
DEFAULT_MAGNIFICATION = 20
TISSUE_THRESHOLD = 0.5  # 최소 조직 비율
THUMBNAIL_DOWNSAMPLE = 64  # 썸네일 생성용 다운샘플 비율


def setup_logging(log_dir: Path) -> logging.Logger:
    """로깅 설정."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"step2_preprocessing_{PIPELINE_TAG}.log"

    logger = logging.getLogger(f"step2_{PIPELINE_TAG}")
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
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


def get_slide_id(svs_path: Path) -> str:
    """SVS 파일명에서 슬라이드 ID 추출."""
    # TCGA 파일명: TCGA-XX-XXXX-01Z-00-DX1.XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX.svs
    return svs_path.stem


def get_target_magnification_level(
    slide: openslide.OpenSlide,
    target_mag: int = 20,
) -> tuple[int, float]:
    """
    WSI에서 목표 배율에 해당하는 레벨과 다운샘플 팩터를 찾음.
    
    Returns:
        (level, downsample_factor)
    """
    # 슬라이드의 원본 배율 확인
    try:
        slide_mag = float(slide.properties.get(
            openslide.PROPERTY_NAME_OBJECTIVE_POWER, 40
        ))
    except (ValueError, KeyError):
        slide_mag = 40.0  # 기본값

    target_downsample = slide_mag / target_mag

    # 가장 가까운 레벨 찾기
    best_level = 0
    best_diff = float("inf")

    for level in range(slide.level_count):
        level_downsample = slide.level_downsamples[level]
        diff = abs(level_downsample - target_downsample)
        if diff < best_diff:
            best_diff = diff
            best_level = level

    actual_downsample = slide.level_downsamples[best_level]
    return best_level, actual_downsample


def create_tissue_mask(
    slide: openslide.OpenSlide,
    downsample: int = 64,
) -> np.ndarray:
    """
    Otsu thresholding으로 조직 마스크 생성.
    
    Returns:
        binary mask (0: 배경, 255: 조직) at downsampled resolution
    """
    # 썸네일 크기 계산
    dims = slide.dimensions  # (width, height) at level 0
    thumb_size = (dims[0] // downsample, dims[1] // downsample)

    # 썸네일 추출
    thumbnail = slide.get_thumbnail(thumb_size)
    thumbnail_np = np.array(thumbnail)

    # RGB → HSV → Saturation 채널 사용 (조직은 saturation이 높음)
    hsv = cv2.cvtColor(thumbnail_np, cv2.COLOR_RGB2HSV)
    saturation = hsv[:, :, 1]

    # Otsu thresholding
    _, mask = cv2.threshold(saturation, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 모폴로지 연산으로 노이즈 제거
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    return mask


def extract_tile_coordinates(
    slide: openslide.OpenSlide,
    tissue_mask: np.ndarray,
    patch_size: int,
    target_level: int,
    downsample_for_mask: int,
    tissue_threshold: float = 0.5,
    max_patches: int = 10000,
) -> np.ndarray:
    """
    조직 마스크 기반으로 타일 좌표 추출.
    
    Returns:
        np.ndarray: shape (N, 2), 각 행은 (x, y) 좌표 (level 0 기준)
    """
    level_dims = slide.level_dimensions[target_level]
    level_downsample = slide.level_downsamples[target_level]

    # level 0 기준 패치 크기
    patch_size_level0 = int(patch_size * level_downsample)

    # 마스크에서의 패치 크기
    mask_patch_w = max(1, int(patch_size_level0 / downsample_for_mask))
    mask_patch_h = max(1, int(patch_size_level0 / downsample_for_mask))

    coords = []
    slide_w, slide_h = slide.dimensions  # level 0 크기

    # 그리드 순회
    for y in range(0, slide_h - patch_size_level0 + 1, patch_size_level0):
        for x in range(0, slide_w - patch_size_level0 + 1, patch_size_level0):
            # 마스크 좌표
            mask_x = int(x / downsample_for_mask)
            mask_y = int(y / downsample_for_mask)

            # 마스크 영역 추출
            mask_region = tissue_mask[
                mask_y : mask_y + mask_patch_h,
                mask_x : mask_x + mask_patch_w
            ]

            if mask_region.size == 0:
                continue

            # 조직 비율 계산
            tissue_ratio = np.mean(mask_region > 0)

            if tissue_ratio >= tissue_threshold:
                coords.append([x, y])

                if len(coords) >= max_patches:
                    break

        if len(coords) >= max_patches:
            break

    return np.array(coords, dtype=np.int64) if coords else np.empty((0, 2), dtype=np.int64)


def process_single_slide(
    svs_path: Path,
    output_dir: Path,
    patch_size: int,
    target_mag: int,
    tissue_threshold: float,
    max_patches: int,
    save_patches: bool,
    logger: logging.Logger,
) -> dict:
    """
    단일 WSI 전처리: 조직 검출 → 타일 좌표 추출 → 저장.
    
    Returns:
        dict: 처리 결과 요약
    """
    slide_id = get_slide_id(svs_path)
    slide_output_dir = output_dir / slide_id
    slide_output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "slide_id": slide_id,
        "svs_path": str(svs_path),
        "status": "failed",
        "n_tiles": 0,
        "slide_width": 0,
        "slide_height": 0,
        "tissue_ratio": 0.0,
        "target_level": 0,
        "patch_size": patch_size,
    }

    try:
        # WSI 로드
        slide = openslide.OpenSlide(str(svs_path))
        result["slide_width"] = slide.dimensions[0]
        result["slide_height"] = slide.dimensions[1]

        # 목표 배율 레벨 찾기
        target_level, actual_downsample = get_target_magnification_level(
            slide, target_mag
        )
        result["target_level"] = target_level
        logger.debug(
            f"  {slide_id}: dims={slide.dimensions}, "
            f"target_level={target_level} (downsample={actual_downsample:.1f})"
        )

        # 조직 마스크 생성
        tissue_mask = create_tissue_mask(slide, downsample=THUMBNAIL_DOWNSAMPLE)
        tissue_ratio = np.mean(tissue_mask > 0)
        result["tissue_ratio"] = round(tissue_ratio, 4)

        # 조직 마스크 저장 (디버깅용)
        mask_path = slide_output_dir / f"tissue_mask_{PIPELINE_TAG}.png"
        cv2.imwrite(str(mask_path), tissue_mask)

        # 타일 좌표 추출
        coords = extract_tile_coordinates(
            slide=slide,
            tissue_mask=tissue_mask,
            patch_size=patch_size,
            target_level=target_level,
            downsample_for_mask=THUMBNAIL_DOWNSAMPLE,
            tissue_threshold=tissue_threshold,
            max_patches=max_patches,
        )

        result["n_tiles"] = len(coords)
        logger.info(
            f"  {slide_id}: 조직비율={tissue_ratio:.2%}, "
            f"타일={len(coords)}개"
        )

        if len(coords) == 0:
            logger.warning(f"  {slide_id}: 조직 타일이 없습니다!")
            result["status"] = "no_tissue"
            slide.close()
            return result

        # 좌표를 H5 파일로 저장
        h5_path = slide_output_dir / f"coords_{PIPELINE_TAG}.h5"
        with h5py.File(h5_path, "w") as f:
            f.create_dataset("coords", data=coords)
            f.attrs["slide_id"] = slide_id
            f.attrs["patch_size"] = patch_size
            f.attrs["target_level"] = target_level
            f.attrs["target_magnification"] = target_mag
            f.attrs["actual_downsample"] = actual_downsample
            f.attrs["n_tiles"] = len(coords)
            f.attrs["slide_width"] = slide.dimensions[0]
            f.attrs["slide_height"] = slide.dimensions[1]
            f.attrs["pipeline_tag"] = PIPELINE_TAG

        # 패치 이미지 저장 (선택적)
        if save_patches:
            patches_dir = slide_output_dir / "patches"
            patches_dir.mkdir(exist_ok=True)

            for idx, (x, y) in enumerate(coords):
                patch = slide.read_region(
                    (int(x), int(y)),
                    target_level,
                    (patch_size, patch_size)
                ).convert("RGB")

                patch_path = patches_dir / f"patch_{idx:05d}_{x}_{y}.png"
                patch.save(patch_path)

        slide.close()
        result["status"] = "success"

    except Exception as e:
        logger.error(f"  {slide_id}: 처리 실패 - {e}")
        result["status"] = f"error: {str(e)[:100]}"

    return result


def main():
    parser = argparse.ArgumentParser(
        description=f"Step 2: WSI 전처리 — CLAM 기반 타일링 ({PIPELINE_TAG})"
    )
    parser.add_argument(
        "--work-root", type=str, default=str(DEFAULT_WORK_ROOT),
        help="작업 디렉토리 루트"
    )
    parser.add_argument(
        "--patch-size", type=int, default=DEFAULT_PATCH_SIZE,
        help=f"패치 크기 (기본: {DEFAULT_PATCH_SIZE})"
    )
    parser.add_argument(
        "--magnification", type=int, default=DEFAULT_MAGNIFICATION,
        help=f"목표 배율 (기본: {DEFAULT_MAGNIFICATION}x)"
    )
    parser.add_argument(
        "--tissue-threshold", type=float, default=TISSUE_THRESHOLD,
        help=f"조직 비율 임계값 (기본: {TISSUE_THRESHOLD})"
    )
    parser.add_argument(
        "--max-patches", type=int, default=10000,
        help="슬라이드당 최대 패치 수 (기본: 10000)"
    )
    parser.add_argument(
        "--save-patches", action="store_true",
        help="패치 이미지를 PNG로 저장 (디버깅용, 디스크 사용량 증가)"
    )
    args = parser.parse_args()

    work_root = Path(args.work_root)
    wsi_raw_dir = work_root / "data" / "wsi_raw"
    wsi_tiles_dir = work_root / "data" / "wsi_tiles"
    log_dir = work_root / "logs"

    wsi_tiles_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(log_dir)
    logger.info("=" * 60)
    logger.info(f"Step 2: WSI 전처리 시작 ({PIPELINE_TAG})")
    logger.info(f"  패치 크기: {args.patch_size}×{args.patch_size}")
    logger.info(f"  목표 배율: {args.magnification}x")
    logger.info(f"  조직 임계값: {args.tissue_threshold}")
    logger.info(f"  입력: {wsi_raw_dir}")
    logger.info(f"  출력: {wsi_tiles_dir}")
    logger.info("=" * 60)

    # SVS 파일 목록
    svs_files = sorted(wsi_raw_dir.glob("*.svs"))
    if not svs_files:
        logger.error(f"SVS 파일을 찾을 수 없습니다: {wsi_raw_dir}")
        sys.exit(1)

    logger.info(f"발견된 SVS 파일: {len(svs_files)}개")

    # 전처리 실행
    results = []
    for i, svs_path in enumerate(svs_files, 1):
        logger.info(f"\n[{i}/{len(svs_files)}] {svs_path.name}")
        result = process_single_slide(
            svs_path=svs_path,
            output_dir=wsi_tiles_dir,
            patch_size=args.patch_size,
            target_mag=args.magnification,
            tissue_threshold=args.tissue_threshold,
            max_patches=args.max_patches,
            save_patches=args.save_patches,
            logger=logger,
        )
        results.append(result)

    # 요약 저장
    summary_path = wsi_tiles_dir / f"tile_summary_{PIPELINE_TAG}.csv"
    df = pd.DataFrame(results)
    df.to_csv(summary_path, index=False)

    # 통계
    success = df[df["status"] == "success"]
    total_tiles = success["n_tiles"].sum() if len(success) > 0 else 0

    logger.info("\n" + "=" * 60)
    logger.info(f"전처리 완료 요약 ({PIPELINE_TAG})")
    logger.info(f"  성공: {len(success)}/{len(svs_files)} 슬라이드")
    logger.info(f"  총 타일: {total_tiles:,}개")
    if len(success) > 0:
        logger.info(f"  슬라이드당 평균 타일: {total_tiles // len(success):,}개")
        logger.info(f"  평균 조직 비율: {success['tissue_ratio'].mean():.2%}")
    logger.info(f"  요약 파일: {summary_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
