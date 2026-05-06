#!/usr/bin/env bash
set -euo pipefail

echo "[sagemaker_setup_20260430_v1] Installing system dependencies"
if command -v apt-get >/dev/null 2>&1; then
  apt-get update
  apt-get install -y --no-install-recommends openslide-tools libopenslide0 libgl1 libglib2.0-0
fi

echo "[sagemaker_setup_20260430_v1] Installing Python dependencies"
python -m pip install --upgrade pip
python -m pip install \
  boto3 sagemaker requests tqdm pyyaml \
  torch torchvision timm huggingface_hub \
  openslide-python openslide-bin h5py numpy pandas pyarrow \
  lightgbm scikit-learn scipy rdkit-pypi matplotlib Pillow opencv-python-headless

if [[ -z "${HUGGING_FACE_HUB_TOKEN:-}" ]]; then
  echo "[WARN] HUGGING_FACE_HUB_TOKEN is not set. UNI2 may fall back to ViT-Large."
else
  echo "[OK] HUGGING_FACE_HUB_TOKEN is set."
fi

echo "[OK] SageMaker image-modal environment ready."
