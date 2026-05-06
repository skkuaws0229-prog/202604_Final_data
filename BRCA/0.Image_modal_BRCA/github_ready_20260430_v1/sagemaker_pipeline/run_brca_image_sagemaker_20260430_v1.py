#!/usr/bin/env python3
"""Launch BRCA image-modal SageMaker Processing jobs for 20260430_v1."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import yaml

PIPELINE_TAG = "20260430_v1"
DEFAULT_CONFIG = Path(__file__).resolve().parent / "configs" / f"sagemaker_config_{PIPELINE_TAG}.yaml"


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def processing_env() -> dict:
    env = {}
    if os.environ.get("HUGGING_FACE_HUB_TOKEN"):
        env["HUGGING_FACE_HUB_TOKEN"] = os.environ["HUGGING_FACE_HUB_TOKEN"]
    elif os.environ.get("HUGGING_FACE_HUB_TOKEN_SECRET_ID"):
        import boto3

        secret_id = os.environ["HUGGING_FACE_HUB_TOKEN_SECRET_ID"]
        client = boto3.client("secretsmanager")
        secret_value = client.get_secret_value(SecretId=secret_id)["SecretString"]
        try:
            parsed = json.loads(secret_value)
            token = parsed.get("HUGGING_FACE_HUB_TOKEN") or parsed.get("HF_TOKEN") or parsed.get("token")
        except json.JSONDecodeError:
            token = secret_value
        if token:
            env["HUGGING_FACE_HUB_TOKEN"] = token.strip()
    else:
        try:
            from huggingface_hub import get_token

            token = get_token()
            if token:
                env["HUGGING_FACE_HUB_TOKEN"] = token
        except Exception:
            try:
                from huggingface_hub import HfFolder

                token = HfFolder.get_token()
                if token:
                    env["HUGGING_FACE_HUB_TOKEN"] = token
            except Exception:
                pass
    return env


def create_processor(cfg: dict, job_name: str):
    import sagemaker
    from sagemaker.processing import ScriptProcessor

    role = os.environ.get(cfg["aws"]["role_env"])
    if not role:
        raise RuntimeError(f"Set {cfg['aws']['role_env']} to your SageMaker execution role ARN")

    image_uri = sagemaker.image_uris.retrieve(
        framework="pytorch",
        region=cfg["aws"]["region"],
        version="2.3",
        py_version="py311",
        image_scope="training",
        instance_type=cfg["sagemaker"]["instance_type"],
    )
    return ScriptProcessor(
        image_uri=image_uri,
        command=["python3"],
        role=role,
        instance_count=cfg["sagemaker"]["instance_count"],
        instance_type=cfg["sagemaker"]["instance_type"],
        volume_size_in_gb=cfg["sagemaker"]["volume_size_gb"],
        max_runtime_in_seconds=cfg["sagemaker"]["max_runtime_seconds"],
        env=processing_env(),
        tags=[
            {"Key": "project", "Value": cfg["project"]},
            {"Key": "team", "Value": cfg["team"]},
            {"Key": "pipeline", "Value": "brca_image_modal"},
            {"Key": "pipeline_tag", "Value": PIPELINE_TAG},
        ],
        base_job_name=job_name,
    )


def run_step(processor, code: str, args: list[str], inputs, outputs, source_dir: Path):
    from sagemaker.processing import ProcessingInput

    package_input = ProcessingInput(
        source=str(source_dir),
        destination="/opt/ml/processing/input/package",
        input_name="pipeline_package",
    )
    processor.run(
        code=str(source_dir / "scripts" / f"processing_bootstrap_{PIPELINE_TAG}.py"),
        arguments=["--target", f"scripts/{code}", "--"] + args,
        inputs=[package_input] + list(inputs),
        outputs=outputs,
        wait=True,
        logs=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--mode", choices=["full", "preprocessing", "embedding", "reranking"], default="full")
    parser.add_argument("--n-slides", type=int, default=0, help="0 means all slides")
    parser.add_argument("--existing-s3-uri", default=None, help="S3 prefix containing existing BRCA pipeline CSVs")
    parser.add_argument("--image-model-label", default="UNI2")
    parser.add_argument("--instance-type", default=None, help="Override SageMaker Processing instance type")
    parser.add_argument("--batch-size", type=int, default=None, help="Override embedding batch size")
    parser.add_argument("--volume-size-gb", type=int, default=None, help="Override Processing volume size")
    args = parser.parse_args()

    from sagemaker.processing import ProcessingInput, ProcessingOutput

    cfg = load_config(args.config)
    if args.instance_type:
        cfg["sagemaker"]["instance_type"] = args.instance_type
    if args.volume_size_gb:
        cfg["sagemaker"]["volume_size_gb"] = args.volume_size_gb
    embedding_batch_size = args.batch_size or cfg["model"]["batch_size"]
    root = Path(__file__).resolve().parent
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    processor = create_processor(cfg, f"brca-image-modal-{PIPELINE_TAG.replace('_', '-')}-{stamp}")

    s3 = cfg["s3"]
    out = cfg["paths"]["processing_output"]

    step1_outputs = [
        ProcessingOutput(source=f"{out}/wsi_raw", destination=s3["wsi_uri"], output_name="wsi_raw"),
        ProcessingOutput(source=f"{out}/logs", destination=s3["output_uri"] + "logs/step1/", output_name="logs_step1"),
    ]
    step2_outputs = [
        ProcessingOutput(source=f"{out}/wsi_tiles", destination=s3["output_uri"] + "wsi_tiles/", output_name="wsi_tiles"),
        ProcessingOutput(source=f"{out}/logs", destination=s3["output_uri"] + "logs/step2/", output_name="logs_step2"),
    ]
    step3_outputs = [
        ProcessingOutput(source=f"{out}/embeddings", destination=s3["output_uri"] + "embeddings/", output_name="embeddings"),
        ProcessingOutput(source=f"{out}/logs", destination=s3["output_uri"] + "logs/step3/", output_name="logs_step3"),
    ]
    step4_outputs = [
        ProcessingOutput(source=f"{out}/results", destination=s3["output_uri"] + "results/", output_name="results"),
        ProcessingOutput(source=f"{out}/logs", destination=s3["output_uri"] + "logs/step4/", output_name="logs_step4"),
    ]
    step5_outputs = [
        ProcessingOutput(source=f"{out}/results", destination=s3["output_uri"] + "results/", output_name="results"),
        ProcessingOutput(source=f"{out}/logs", destination=s3["output_uri"] + "logs/step5/", output_name="logs_step5"),
    ]

    if args.mode == "full":
        run_step(
            processor,
            f"step1_wsi_download_sagemaker_{PIPELINE_TAG}.py",
            ["--n-slides", str(args.n_slides), "--output-dir", f"{out}/wsi_raw"],
            inputs=[],
            outputs=step1_outputs,
            source_dir=root,
        )

    if args.mode in {"full", "preprocessing"}:
        step2_inputs = [ProcessingInput(source=s3["wsi_uri"], destination="/opt/ml/processing/input/wsi_raw", input_name="wsi_raw")]
        run_step(processor, f"step2_wsi_preprocessing_sagemaker_{PIPELINE_TAG}.py", [], step2_inputs, step2_outputs, root)
        step3_inputs = step2_inputs + [
            ProcessingInput(source=s3["output_uri"] + "wsi_tiles/", destination="/opt/ml/processing/input/wsi_tiles", input_name="wsi_tiles")
        ]
        run_step(
            processor,
            f"step3_wsi_embedding_sagemaker_{PIPELINE_TAG}.py",
            ["--device", "cuda", "--batch-size", str(embedding_batch_size), "--model-label", args.image_model_label],
            step3_inputs,
            step3_outputs,
            root,
        )

    if args.mode == "embedding":
        inputs = [
            ProcessingInput(source=s3["wsi_uri"], destination="/opt/ml/processing/input/wsi_raw", input_name="wsi_raw"),
            ProcessingInput(source=s3["output_uri"] + "wsi_tiles/", destination="/opt/ml/processing/input/wsi_tiles", input_name="wsi_tiles"),
        ]
        run_step(
            processor,
            f"step3_wsi_embedding_sagemaker_{PIPELINE_TAG}.py",
            ["--device", "cuda", "--batch-size", str(embedding_batch_size), "--model-label", args.image_model_label],
            inputs,
            step3_outputs,
            root,
        )

    if args.mode in {"full", "preprocessing", "reranking"}:
        inputs = [
            ProcessingInput(source=s3["output_uri"] + "embeddings/", destination="/opt/ml/processing/input/embeddings", input_name="embeddings"),
        ]
        inputs.append(
            ProcessingInput(
                source=args.existing_s3_uri or s3["input_uri"],
                destination="/opt/ml/processing/input/existing",
                input_name="existing",
            )
        )
        run_step(processor, f"step4_reranking_sagemaker_{PIPELINE_TAG}.py", [], inputs, step4_outputs, root)
        run_step(processor, f"step5_ablation_sagemaker_{PIPELINE_TAG}.py", [], inputs, step5_outputs, root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
