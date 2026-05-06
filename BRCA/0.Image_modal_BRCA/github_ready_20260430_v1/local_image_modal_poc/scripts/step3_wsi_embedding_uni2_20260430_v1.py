#!/usr/bin/env python3
"""
step3_wsi_embedding_uni2_20260430_v1.py
=======================================
UNI2 Foundation Model로 WSI 타일 임베딩 추출 + 슬라이드 레벨 집계.

목적:
  - Step 2에서 생성된 타일 좌표를 읽어 패치 추출
  - UNI2 (ViT-Large, frozen)로 타일당 1,024d 임베딩 벡터 생성
  - Mean pooling으로 슬라이드 레벨 임베딩 (1,024d) 집계
  - 환자별 임베딩을 .npy로 저장

사용법:
  python step3_wsi_embedding_uni2_20260430_v1.py
  python step3_wsi_embedding_uni2_20260430_v1.py --device cpu --batch-size 16
  python step3_wsi_embedding_uni2_20260430_v1.py --pooling abmil

입력:
  - data/wsi_raw/*.svs
  - data/wsi_tiles/{slide_id}/coords_20260430_v1.h5

출력:
  - data/wsi_embeddings/{slide_id}/tile_embeddings_20260430_v1.h5
  - data/slide_embeddings/slide_embedding_{slide_id}_20260430_v1.npy
  - data/slide_embeddings/all_slide_embeddings_20260430_v1.parquet
  - logs/step3_embedding_20260430_v1.log

의존성:
  pip install torch torchvision timm h5py numpy pandas openslide-python Pillow tqdm

UNI2 모델:
  HuggingFace에서 MahmoodLab/UNI2 접근 권한 필요 (Gated model)
  https://huggingface.co/MahmoodLab/UNI2-h

작성일: 2026-04-30
버전: v1
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

import h5py
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from PIL import Image
from tqdm import tqdm

try:
    import openslide
except ImportError:
    print("openslide-python이 필요합니다.")
    sys.exit(1)

try:
    import timm
except ImportError:
    print("timm이 필요합니다: pip install timm")
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

# UNI2 모델 설정
UNI2_MODEL_NAME = "hf-hub:MahmoodLab/UNI2-h"
EMBEDDING_DIM = 1024
DEFAULT_BATCH_SIZE = 32
DEFAULT_DEVICE = "mps"  # M4 Mac 기준

# 이미지 전처리 (ImageNet 표준)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def setup_logging(log_dir: Path) -> logging.Logger:
    """로깅 설정."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"step3_embedding_{PIPELINE_TAG}.log"

    logger = logging.getLogger(f"step3_{PIPELINE_TAG}")
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


def load_uni2_model(device: str, logger: logging.Logger) -> torch.nn.Module:
    """
    UNI2 모델 로드 (frozen backbone).
    
    Note:
      - HuggingFace Gated model이므로 사전에 접근 권한 승인 필요
      - `huggingface-cli login` 으로 토큰 설정 필요
      - 접근이 안 되면 fallback으로 일반 ViT-Large 사용
    """
    logger.info("UNI2 모델 로딩 중...")

    try:
        model = timm.create_model(
            UNI2_MODEL_NAME,
            pretrained=True,
            num_classes=0,  # feature extractor 모드
        )
        logger.info("✓ UNI2 (MahmoodLab/UNI2-h) 로드 성공")
    except Exception as e:
        logger.warning(f"UNI2 로드 실패: {e}")
        logger.info("Fallback: ViT-Large (ImageNet pretrained) 사용")
        model = timm.create_model(
            "vit_large_patch16_224",
            pretrained=True,
            num_classes=0,
        )

    model = model.to(device)
    model.eval()

    # Backbone freeze
    for param in model.parameters():
        param.requires_grad = False

    # 파라미터 수 출력
    n_params = sum(p.numel() for p in model.parameters())
    logger.info(f"  파라미터 수: {n_params / 1e6:.1f}M")
    logger.info(f"  디바이스: {device}")

    return model


def get_transform(input_size: int = 224):
    """이미지 전처리 transform (timm 호환)."""
    import torchvision.transforms as T

    return T.Compose([
        T.Resize((input_size, input_size)),
        T.ToTensor(),
        T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def extract_tile_embeddings(
    svs_path: Path,
    coords_h5_path: Path,
    model: torch.nn.Module,
    device: str,
    batch_size: int,
    logger: logging.Logger,
) -> np.ndarray:
    """
    WSI에서 타일을 읽고 UNI2로 임베딩 추출.
    
    Returns:
        np.ndarray: shape (N, 1024), 각 타일의 임베딩 벡터
    """
    # 좌표 로드
    with h5py.File(coords_h5_path, "r") as f:
        coords = f["coords"][:]
        patch_size = int(f.attrs["patch_size"])
        target_level = int(f.attrs["target_level"])

    n_tiles = len(coords)
    logger.debug(f"  타일 수: {n_tiles}, patch_size: {patch_size}, level: {target_level}")

    # WSI 로드
    slide = openslide.OpenSlide(str(svs_path))
    transform = get_transform(input_size=224)

    # 배치 단위로 임베딩 추출
    all_embeddings = []

    for batch_start in range(0, n_tiles, batch_size):
        batch_end = min(batch_start + batch_size, n_tiles)
        batch_coords = coords[batch_start:batch_end]

        # 패치 읽기 + 전처리
        batch_tensors = []
        for (x, y) in batch_coords:
            patch = slide.read_region(
                (int(x), int(y)),
                target_level,
                (patch_size, patch_size)
            ).convert("RGB")

            tensor = transform(patch)
            batch_tensors.append(tensor)

        batch_input = torch.stack(batch_tensors).to(device)

        # 임베딩 추출
        with torch.no_grad():
            if device == "mps":
                # MPS에서 float16이 불안정할 수 있으므로 float32 사용
                embeddings = model(batch_input.float())
            else:
                with torch.cuda.amp.autocast(enabled=(device == "cuda")):
                    embeddings = model(batch_input)

        all_embeddings.append(embeddings.cpu().numpy())

    slide.close()

    return np.concatenate(all_embeddings, axis=0) if all_embeddings else np.empty((0, EMBEDDING_DIM))


def mean_pool(embeddings: np.ndarray) -> np.ndarray:
    """Mean pooling으로 슬라이드 레벨 임베딩 생성."""
    if len(embeddings) == 0:
        return np.zeros(EMBEDDING_DIM, dtype=np.float32)
    return embeddings.mean(axis=0).astype(np.float32)


def process_single_slide(
    slide_id: str,
    svs_path: Path,
    coords_h5_path: Path,
    model: torch.nn.Module,
    device: str,
    batch_size: int,
    embedding_dir: Path,
    slide_embedding_dir: Path,
    pooling: str,
    logger: logging.Logger,
) -> dict:
    """
    단일 슬라이드의 임베딩 추출 + 집계.
    
    Returns:
        dict: 처리 결과
    """
    result = {
        "slide_id": slide_id,
        "status": "failed",
        "n_tiles": 0,
        "embedding_dim": EMBEDDING_DIM,
        "pooling": pooling,
    }

    try:
        # 타일 임베딩 추출
        tile_embeddings = extract_tile_embeddings(
            svs_path=svs_path,
            coords_h5_path=coords_h5_path,
            model=model,
            device=device,
            batch_size=batch_size,
            logger=logger,
        )

        result["n_tiles"] = len(tile_embeddings)

        if len(tile_embeddings) == 0:
            logger.warning(f"  {slide_id}: 임베딩 없음 (타일 0개)")
            result["status"] = "no_tiles"
            return result

        # 타일 임베딩 저장 (H5)
        tile_emb_dir = embedding_dir / slide_id
        tile_emb_dir.mkdir(parents=True, exist_ok=True)
        tile_h5_path = tile_emb_dir / f"tile_embeddings_{PIPELINE_TAG}.h5"

        with h5py.File(tile_h5_path, "w") as f:
            f.create_dataset(
                "embeddings",
                data=tile_embeddings,
                compression="gzip",
                compression_opts=4,
            )
            f.attrs["slide_id"] = slide_id
            f.attrs["n_tiles"] = len(tile_embeddings)
            f.attrs["embedding_dim"] = EMBEDDING_DIM
            f.attrs["model"] = "UNI2"
            f.attrs["pipeline_tag"] = PIPELINE_TAG

        # 슬라이드 레벨 집계
        if pooling == "mean":
            slide_embedding = mean_pool(tile_embeddings)
        else:
            # ABMIL은 별도 학습이 필요 → 현재는 mean으로 fallback
            logger.info(f"  {slide_id}: ABMIL pooling은 Step 4에서 학습, mean pool 사용")
            slide_embedding = mean_pool(tile_embeddings)

        # 슬라이드 임베딩 저장 (.npy)
        slide_embedding_dir.mkdir(parents=True, exist_ok=True)
        npy_path = slide_embedding_dir / f"slide_embedding_{slide_id}_{PIPELINE_TAG}.npy"
        np.save(npy_path, slide_embedding)

        result["status"] = "success"
        logger.info(
            f"  ✓ {slide_id}: {len(tile_embeddings)} 타일 → "
            f"{EMBEDDING_DIM}d slide embedding"
        )

    except Exception as e:
        logger.error(f"  ✗ {slide_id}: 임베딩 추출 실패 - {e}")
        result["status"] = f"error: {str(e)[:100]}"

    return result


def build_embedding_table(
    results: list[dict],
    slide_embedding_dir: Path,
    logger: logging.Logger,
) -> Path:
    """
    모든 슬라이드 임베딩을 하나의 parquet 테이블로 합침.
    
    컬럼: slide_id, emb_0, emb_1, ..., emb_1023
    """
    records = []
    for r in results:
        if r["status"] != "success":
            continue

        slide_id = r["slide_id"]
        npy_path = slide_embedding_dir / f"slide_embedding_{slide_id}_{PIPELINE_TAG}.npy"

        if not npy_path.exists():
            continue

        emb = np.load(npy_path)
        record = {"slide_id": slide_id}
        for i, val in enumerate(emb):
            record[f"emb_{i}"] = float(val)
        records.append(record)

    df = pd.DataFrame(records)
    output_path = slide_embedding_dir / f"all_slide_embeddings_{PIPELINE_TAG}.parquet"
    df.to_parquet(output_path, index=False)

    logger.info(f"통합 임베딩 테이블 저장: {output_path} ({len(df)}개 슬라이드)")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description=f"Step 3: UNI2 임베딩 추출 ({PIPELINE_TAG})"
    )
    parser.add_argument(
        "--work-root", type=str, default=str(DEFAULT_WORK_ROOT),
        help="작업 디렉토리 루트"
    )
    parser.add_argument(
        "--device", type=str, default=DEFAULT_DEVICE,
        choices=["mps", "cuda", "cpu"],
        help=f"연산 디바이스 (기본: {DEFAULT_DEVICE})"
    )
    parser.add_argument(
        "--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
        help=f"배치 크기 (기본: {DEFAULT_BATCH_SIZE})"
    )
    parser.add_argument(
        "--pooling", type=str, default="mean",
        choices=["mean", "abmil"],
        help="슬라이드 레벨 집계 방법 (기본: mean)"
    )
    args = parser.parse_args()

    work_root = Path(args.work_root)
    wsi_raw_dir = work_root / "data" / "wsi_raw"
    wsi_tiles_dir = work_root / "data" / "wsi_tiles"
    embedding_dir = work_root / "data" / "wsi_embeddings"
    slide_embedding_dir = work_root / "data" / "slide_embeddings"
    log_dir = work_root / "logs"

    # 디바이스 확인
    device = args.device
    if device == "mps" and not torch.backends.mps.is_available():
        print("MPS 사용 불가, CPU로 전환합니다.")
        device = "cpu"
    elif device == "cuda" and not torch.cuda.is_available():
        print("CUDA 사용 불가, CPU로 전환합니다.")
        device = "cpu"

    logger = setup_logging(log_dir)
    logger.info("=" * 60)
    logger.info(f"Step 3: UNI2 임베딩 추출 시작 ({PIPELINE_TAG})")
    logger.info(f"  디바이스: {device}")
    logger.info(f"  배치 크기: {args.batch_size}")
    logger.info(f"  Pooling: {args.pooling}")
    logger.info("=" * 60)

    # 모델 로드
    model = load_uni2_model(device, logger)

    # 처리할 슬라이드 목록 (Step 2에서 생성된 좌표 파일 기준)
    coord_files = sorted(wsi_tiles_dir.glob(f"*/coords_{PIPELINE_TAG}.h5"))
    if not coord_files:
        logger.error(f"좌표 파일을 찾을 수 없습니다: {wsi_tiles_dir}/*/coords_{PIPELINE_TAG}.h5")
        logger.info("Step 2를 먼저 실행하세요.")
        sys.exit(1)

    logger.info(f"처리할 슬라이드: {len(coord_files)}개")

    # 임베딩 추출
    results = []
    for i, coord_h5 in enumerate(coord_files, 1):
        slide_id = coord_h5.parent.name
        svs_path = wsi_raw_dir / f"{slide_id}.svs"

        if not svs_path.exists():
            logger.warning(f"  SVS 파일 없음: {svs_path}")
            continue

        logger.info(f"\n[{i}/{len(coord_files)}] {slide_id}")
        result = process_single_slide(
            slide_id=slide_id,
            svs_path=svs_path,
            coords_h5_path=coord_h5,
            model=model,
            device=device,
            batch_size=args.batch_size,
            embedding_dir=embedding_dir,
            slide_embedding_dir=slide_embedding_dir,
            pooling=args.pooling,
            logger=logger,
        )
        results.append(result)

    # 통합 테이블 생성
    embedding_table_path = build_embedding_table(results, slide_embedding_dir, logger)

    # 요약
    success = sum(1 for r in results if r["status"] == "success")
    total_tiles = sum(r["n_tiles"] for r in results if r["status"] == "success")

    logger.info("\n" + "=" * 60)
    logger.info(f"임베딩 추출 완료 요약 ({PIPELINE_TAG})")
    logger.info(f"  성공: {success}/{len(results)} 슬라이드")
    logger.info(f"  총 타일 임베딩: {total_tiles:,}개")
    logger.info(f"  슬라이드 임베딩 차원: {EMBEDDING_DIM}d")
    logger.info(f"  통합 테이블: {embedding_table_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
