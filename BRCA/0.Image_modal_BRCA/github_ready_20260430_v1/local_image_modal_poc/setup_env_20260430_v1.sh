#!/bin/bash
# setup_env_20260430_v1.sh
# ========================
# BRCA Image Modal 파이프라인 환경 설정 (M4 Mac)
#
# 사용법:
#   chmod +x setup_env_20260430_v1.sh
#   ./setup_env_20260430_v1.sh
#
# 작성일: 2026-04-30
# 버전: v1

set -e

echo "============================================"
echo "BRCA Image Modal Pipeline — 환경 설정"
echo "Date: 20260430 / Version: v1"
echo "============================================"

# ---- 1) Python 가상환경 생성 ----
VENV_NAME="brca_image_modal_20260430_v1"
VENV_PATH="$HOME/.venvs/$VENV_NAME"

echo ""
echo "[1/5] Python 가상환경 생성: $VENV_PATH"

if [ -d "$VENV_PATH" ]; then
    echo "  이미 존재합니다. 스킵."
else
    python3 -m venv "$VENV_PATH"
    echo "  ✓ 생성 완료"
fi

source "$VENV_PATH/bin/activate"
echo "  ✓ 활성화: $(python3 --version)"

# ---- 2) 기본 의존성 설치 ----
echo ""
echo "[2/5] 기본 의존성 설치"

pip install --upgrade pip wheel setuptools

pip install \
    requests \
    tqdm \
    pandas \
    numpy \
    scipy \
    scikit-learn \
    lightgbm \
    matplotlib \
    h5py \
    pyarrow \
    pyyaml

echo "  ✓ 기본 패키지 설치 완료"

# ---- 3) PyTorch (M4 Mac MPS) ----
echo ""
echo "[3/5] PyTorch 설치 (MPS backend)"

pip install torch torchvision

python3 -c "
import torch
print(f'  PyTorch: {torch.__version__}')
print(f'  MPS 사용 가능: {torch.backends.mps.is_available()}')
print(f'  MPS 빌드: {torch.backends.mps.is_built()}')
"

# ---- 4) OpenSlide + CLAM 의존성 ----
echo ""
echo "[4/5] OpenSlide 설치"

# macOS: Homebrew로 OpenSlide 설치
if command -v brew &> /dev/null; then
    brew list openslide &> /dev/null || brew install openslide
    echo "  ✓ openslide (brew) 설치 완료"
else
    echo "  ⚠ Homebrew가 없습니다. openslide를 수동 설치하세요."
    echo "    https://openslide.org/download/"
fi

pip install openslide-python
pip install opencv-python-headless
pip install Pillow

echo "  ✓ OpenSlide Python 바인딩 설치 완료"

# ---- 5) timm (UNI2 모델용) ----
echo ""
echo "[5/5] timm + HuggingFace Hub 설치"

pip install timm huggingface_hub

echo "  ✓ timm 설치 완료"
echo ""
echo "============================================"
echo "환경 설정 완료!"
echo ""
echo "사용법:"
echo "  source $VENV_PATH/bin/activate"
echo ""
echo "UNI2 모델 접근 (최초 1회):"
echo "  1. https://huggingface.co/MahmoodLab/uni2-h 에서 접근 권한 신청"
echo "  2. huggingface-cli login 으로 토큰 설정"
echo ""
echo "파이프라인 실행:"
echo "  cd scripts/"
echo "  python step1_wsi_download_tcga_brca_20260430_v1.py --query-only"
echo "  python step1_wsi_download_tcga_brca_20260430_v1.py --n-slides 50"
echo "  python step2_wsi_preprocessing_clam_20260430_v1.py"
echo "  python step3_wsi_embedding_uni2_20260430_v1.py --device mps"
echo "  python step4_reranking_model_20260430_v1.py"
echo "  python step5_ablation_evaluation_20260430_v1.py"
echo "============================================"
