#!/usr/bin/env python3
"""
Step 9 (STAD): LLM 기반 위암 재창출 근거 생성 — Colon `step9_llm_explanation.py` 초안 이식.

입력:
  - results/stad_final_top15.csv
  - results/stad_comprehensive_drug_scores.csv
  - results/stad_admet_summary.json
  - results/stad_alphafold_validation/stad_alphafold_validation_results.json
  - results/stad_subtype_expression_analysis.json (선택; Colon COAD/READ 대응)
  - results/stad_clinical_trials_validation_results.json (선택)

출력:
  - results/stad_drug_explanations.json
  - results/stad_drug_explanations_report.md

LLM: `ollama run <model>` (기본 모델 `OLLAMA_MODEL` 환경변수 또는 `llama3.1`).
Ollama 없으면 각 약물에 ERROR 문자열을 넣고 JSON/Markdown 은 저장 (파이프라인 연속성).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pandas as pd


def query_ollama(prompt: str, model: str | None = None) -> str:
    model = model or os.environ.get("OLLAMA_MODEL", "llama3.1").strip()
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=int(os.environ.get("OLLAMA_TIMEOUT_SEC", "120")),
        )
        if result.returncode == 0:
            return (result.stdout or "").strip()
        return f"ERROR: {result.stderr}"
    except FileNotFoundError:
        return "ERROR: ollama CLI not found (install Ollama or use manual review)"
    except subprocess.TimeoutExpired:
        return "ERROR: Timeout"
    except Exception as e:
        return f"ERROR: {e}"


def load_all_evidence(results_dir: Path) -> dict:
    evidence: dict = {}
    top15 = pd.read_csv(results_dir / "stad_final_top15.csv")
    evidence["top15"] = top15

    comp_path = results_dir / "stad_comprehensive_drug_scores.csv"
    if comp_path.exists():
        evidence["validation"] = pd.read_csv(comp_path)

    admet_path = results_dir / "stad_admet_summary.json"
    if admet_path.exists():
        evidence["admet"] = json.loads(admet_path.read_text(encoding="utf-8"))

    af_path = results_dir / "stad_alphafold_validation" / "stad_alphafold_validation_results.json"
    if af_path.exists():
        evidence["alphafold"] = json.loads(af_path.read_text(encoding="utf-8"))

    st_path = results_dir / "stad_subtype_expression_analysis.json"
    if st_path.exists():
        evidence["stad_subtype"] = json.loads(st_path.read_text(encoding="utf-8"))

    ct_path = results_dir / "stad_clinical_trials_validation_results.json"
    if ct_path.exists():
        evidence["clinical_trials"] = json.loads(ct_path.read_text(encoding="utf-8"))

    return evidence


def build_drug_context(drug_name: str, evidence: dict) -> dict | None:
    top15 = evidence["top15"]
    name_col = "drug_name" if "drug_name" in top15.columns else "DRUG_NAME"
    drug_row = top15[top15[name_col] == drug_name]
    if len(drug_row) == 0:
        return None
    row = drug_row.iloc[0]
    context: dict = {
        "rank": int(row.get("recommendation_rank", row.get("rank", 0))),
        "pred_ic50": round(float(row.get("pred_ic50_mean", 0)), 4),
        "target": str(row.get("target", "")),
        "target_pathway": str(row.get("target_pathway", row.get("TARGET_PATHWAY", ""))),
        "category": str(row.get("usage_category", "")),
        "safety_score": round(float(row.get("safety_score", 0)), 2),
        "verdict": str(row.get("verdict", "")),
        "mw": row.get("mw", "?"),
        "logp": row.get("logp", "?"),
        "tpsa": row.get("tpsa", "?"),
        "ct_max_phase": str(row.get("ct_max_phase", "")),
        "recommendation_stage": int(row["recommendation_stage"])
        if pd.notna(row.get("recommendation_stage"))
        else 0,
    }

    if "validation" in evidence:
        val_df = evidence["validation"]
        vr = val_df[val_df["drug_name"] == drug_name]
        if len(vr) > 0:
            v = vr.iloc[0]
            context["validation_count"] = int(v.get("validation_count", 0))
            context["confidence"] = str(v.get("confidence", ""))
            context["prism"] = bool(v.get("prism", 0))
            context["clinical_trials"] = bool(v.get("clinical_trials", 0))
            context["cosmic"] = bool(v.get("cosmic", 0))
            context["cptac"] = bool(v.get("cptac", 0))
            context["geo"] = bool(v.get("geo", 0))

    if "clinical_trials" in evidence:
        ct = evidence["clinical_trials"]
        for m in ct.get("matched_details", []) or []:
            if m.get("drug_name") == drug_name:
                context["ct_phases"] = m.get("phases", [])
                context["ct_n_trials"] = m.get("n_trials", 0)
                break

    if "alphafold" in evidence:
        af = evidence["alphafold"]
        for structure in af.get("structures", []):
            if drug_name in structure.get("drugs", []):
                context["alphafold_gene"] = structure["gene"]
                context["alphafold_uniprot"] = structure["uniprot_id"]
                plddt = structure.get("plddt", {})
                context["alphafold_plddt"] = plddt.get("mean", 0) if plddt else 0
                pocket = structure.get("pocket", {})
                context["pocket_size"] = pocket.get("n_residues", 0) if pocket else 0
                context["pocket_volume"] = pocket.get("volume", 0) if pocket else 0
                break

    if "stad_subtype" in evidence:
        for rec in evidence["stad_subtype"].get("drug_context", []) or []:
            if rec.get("drug") == drug_name:
                context["stad_subtype_ctx"] = rec.get("context_label", "")
                context["stad_subtype_detail"] = rec.get("detail", "")
                break

    return context


def build_prompt(drug_name: str, context: dict) -> str:
    category_desc = {
        "FDA_APPROVED_GASTRIC": "위암/소화기 계통에서 이미 승인·표준요법에 포함되거나 동의어 리스트에 있는 약물.",
        "REPURPOSING_CANDIDATE": "다른 적응증 위주이나 위암 재창출 후보로 모델이 제안.",
        "CLINICAL_TRIAL": "위암 관련 임상시험 매칭이 있는 약물.",
        "RESEARCH_PHASE_GASTRIC": "연구 단계 표적제/탐색 후보.",
    }
    cat = context.get("category", "Unknown")
    cat_desc = category_desc.get(cat, "분류 정보 없음")

    validations = []
    if context.get("prism"):
        validations.append("PRISM (위암 lineage 스크린)")
    if context.get("clinical_trials"):
        validations.append(
            f"ClinicalTrials.gov (n={context.get('ct_n_trials', 0)}, phase≤{context.get('ct_max_phase', '')})"
        )
    if context.get("cosmic"):
        validations.append("COSMIC (actionability/CGC 맥락)")
    if context.get("cptac"):
        validations.append("CPTAC / cBio STAD 발현")
    if context.get("geo"):
        validations.append("GEO (GSE62254 등 위암 코호트)")
    val_text = "\n".join(f"  - {v}" for v in validations) if validations else "  - 외부 검증 소스 매칭 없음 또는 제한적"

    af_text = ""
    if context.get("alphafold_gene"):
        af_text = f"""
AlphaFold:
  - 타겟: {context['alphafold_gene']} (UniProt {context['alphafold_uniprot']})
  - pLDDT: {context.get('alphafold_plddt', 0):.1f}
  - Pocket: {context.get('pocket_size', 0)} residues, volume {context.get('pocket_volume', 0):.0f}"""

    st_text = ""
    if context.get("stad_subtype_ctx"):
        st_text = f"""
TCGA-STAD 서브타입 맥락:
  - 라벨: {context['stad_subtype_ctx']}
  - 요약: {context.get('stad_subtype_detail', '')}"""

    stage = context.get("recommendation_stage", 0)
    prompt = f"""You are a pharmaceutical research expert for gastric cancer (TCGA-STAD) drug repurposing.

Write in Korean (한국어), concise (≤500 Korean chars), citing only the evidence below.

=== Drug ===
Name: {drug_name}
Rank: #{context['rank']}
3-stage (1=primary): {stage}
Category: {cat} — {cat_desc}
Pred IC50 (lower better): {context['pred_ic50']}
Target: {context.get('target', 'N/A')}
Pathway: {context.get('target_pathway', 'N/A')}

=== ADMET ===
Safety: {context['safety_score']}, Verdict: {context['verdict']}
MW/LogP/TPSA: {context.get('mw')}/{context.get('logp')}/{context.get('tpsa')}

=== External validation ({context.get('validation_count', 0)}/5, {context.get('confidence', '?')}) ===
{val_text}
{af_text}
{st_text}

요구: (1) 위암에서의 타깃/경로 근거 (2) 외부검증이 주는 신호 (3) ADMET (4) AlphaFold·서브타입이 있으면 한 줄 (5) 남은 리스크.
"""
    return prompt


def main() -> int:
    import argparse
    from datetime import datetime

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument(
        "--max-drugs",
        type=int,
        default=int(os.environ.get("STAD_LLM_MAX_DRUGS", "15")),
        help="처리할 Top15 중 최대 개수 (스모크 테스트: --max-drugs 1)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Ollama 호출 없이 프롬프트 길이만 기록한 placeholder explanation 저장",
    )
    args = ap.parse_args()
    root = args.project_root.resolve()
    rd = root / "results"

    print("=" * 80)
    print("Step 9 (STAD): LLM explanations (Ollama)")
    print("=" * 80)

    top_path = rd / "stad_final_top15.csv"
    if not top_path.exists():
        print(f"ERROR: {top_path} missing")
        return 1

    evidence = load_all_evidence(rd)
    top15 = evidence["top15"]
    name_col = "drug_name" if "drug_name" in top15.columns else "DRUG_NAME"
    max_n = max(1, int(args.max_drugs))
    top15 = top15.head(max_n)

    explanations = []
    for idx, (_, row) in enumerate(top15.iterrows(), 1):
        drug_name = str(row[name_col])
        category = str(row.get("usage_category", "?"))
        print(f"\n  [{idx}/{len(top15)}] {drug_name}")
        context = build_drug_context(drug_name, evidence)
        if not context:
            continue
        prompt = build_prompt(drug_name, context)
        if args.dry_run:
            explanation = f"[DRY-RUN] prompt_chars={len(prompt)} — Ollama 미호출"
            print("    dry-run")
        else:
            print("    Ollama...", end=" ", flush=True)
            t0 = time.time()
            explanation = query_ollama(prompt)
            print(f"({time.time()-t0:.1f}s)")
        explanations.append(
            {
                "rank": context["rank"],
                "drug_name": drug_name,
                "category": category,
                "recommendation_stage": context.get("recommendation_stage", 0),
                "pred_ic50": context["pred_ic50"],
                "target": context.get("target", ""),
                "safety_score": context["safety_score"],
                "verdict": context["verdict"],
                "validation_count": context.get("validation_count", 0),
                "confidence": context.get("confidence", ""),
                "stad_subtype": context.get("stad_subtype_ctx", ""),
                "explanation": explanation,
                "context": context,
            }
        )

    json_path = rd / "stad_drug_explanations.json"
    json_path.write_text(json.dumps(explanations, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\n  ✅ {json_path}")

    lines = [
        "# STAD (gastric cancer) — Top 15 repurposing notes (LLM draft)\n",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        "---\n",
    ]
    for exp in explanations:
        lines.extend(
            [
                f"\n## #{exp['rank']} {exp['drug_name']}\n",
                f"- Category: {exp['category']} | Stage: {exp.get('recommendation_stage')} | ADMET: {exp['verdict']}\n",
                f"- Subtype context: {exp.get('stad_subtype') or 'N/A'}\n",
                f"\n{exp['explanation']}\n",
                "\n---\n",
            ]
        )
    md_path = rd / "stad_drug_explanations_report.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✅ {md_path}")
    print("\n✅ Step 9 (STAD) 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
