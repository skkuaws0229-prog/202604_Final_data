# BRCA Image Modal Integration — 20260430_v1

## 목적
기존 BRCA 약물 재창출 파이프라인(Step 1~7 완료)에 H&E WSI 이미지 모달을 추가하여,
기존 앙상블 IC50 예측값을 이미지 기반으로 Re-ranking하는 PoC 파이프라인.

## 전략
- **Architecture 1 (Single-modality embedding)** → 검증 후 → **Architecture 5 (Foundation + KG reasoning)** 통합
- **Strategy A (2-Stage)**: 기존 파이프라인 결과를 건드리지 않고, 위에 이미지 보정 레이어를 얹는 구조
- **Phase 1**: 로컬 M4 Mac에서 Pilot 50장으로 관통 테스트

## 파일명 컨벤션
모든 스크립트/산출물에 `20260430`(날짜)과 `v1`(버전)이 포함됨.
`{step번호}_{작업내용}_20260430_v1.py`

## 실행 순서

| 순서 | 스크립트 | 설명 |
|------|---------|------|
| 1 | `step1_wsi_download_tcga_brca_20260430_v1.py` | TCGA-BRCA H&E WSI 50장 다운로드 |
| 2 | `step2_wsi_preprocessing_clam_20260430_v1.py` | CLAM 조직검출 + 타일링 (256×256) |
| 3 | `step3_wsi_embedding_uni2_20260430_v1.py` | UNI2 임베딩 추출 + Mean Pool → 슬라이드 임베딩 |
| 4 | `step4_reranking_model_20260430_v1.py` | 기존 IC50 + 이미지 임베딩 → Re-ranking |
| 5 | `step5_ablation_evaluation_20260430_v1.py` | Ablation 실험 (이미지 유무 비교) |

## 기존 파이프라인 연결점
- 입력: `brca_directive_top30_tiered_candidates.csv` (drug_level_score)
- 입력: `brca_directive_ensemble_B_holdout_predictions.csv` (sample별 예측값)
- 타겟 변수: ln(IC50) — GDSC 기본 스케일
- 랭킹 방향: ln(IC50) 높을수록 score 높음 (drug_level_score 기준)

## 환경 요구사항
- Python 3.10+
- PyTorch (MPS backend for M4 Mac)
- timm, CLAM, openslide-python, h5py
- 저장 공간: ~150GB (WSI 50장 + 타일 + 임베딩)

## 디렉토리 구조
```
brca_image_modal_20260430_v1/
├── README_brca_image_modal_20260430_v1.md
├── scripts/
│   ├── step1_wsi_download_tcga_brca_20260430_v1.py
│   ├── step2_wsi_preprocessing_clam_20260430_v1.py
│   ├── step3_wsi_embedding_uni2_20260430_v1.py
│   ├── step4_reranking_model_20260430_v1.py
│   └── step5_ablation_evaluation_20260430_v1.py
├── data/
│   ├── wsi_raw/          ← TCGA WSI 원본 (.svs)
│   ├── wsi_tiles/        ← 타일링 결과 (256×256 patches)
│   ├── wsi_embeddings/   ← UNI2 임베딩 (.h5)
│   └── slide_embeddings/ ← 슬라이드 레벨 임베딩 (.npy)
├── results/
│   ├── reranking/        ← Re-ranking 모델 결과
│   └── ablation/         ← Ablation 실험 결과
└── configs/
    └── pipeline_config_20260430_v1.yaml
```
