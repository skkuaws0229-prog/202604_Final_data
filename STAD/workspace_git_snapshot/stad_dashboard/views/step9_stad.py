"""Step 9 (STAD): LLM 설명 — Colon `dashboard/views/step9_llm.py` 대응."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _normalize_explanations(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        for key in ("explanations", "drugs", "items", "results"):
            inner = raw.get(key)
            if isinstance(inner, list):
                return [x for x in inner if isinstance(x, dict)]
    return []


def render() -> None:
    rd = _root() / "results"

    st.header("📝 Step 9: LLM drug explanations (STAD)")

    exp_path = rd / "stad_drug_explanations.json"
    if not exp_path.exists():
        st.warning(
            "`results/stad_drug_explanations.json` 없음 — 프로젝트 루트에서 "
            "`STAD_LLM_DRY_RUN=1 python3 scripts/step9_llm_explanation_stad.py` 또는 `./scripts/run_step8_9_stad.sh` 실행"
        )
        return

    raw = json.loads(exp_path.read_text(encoding="utf-8"))
    explanations = _normalize_explanations(raw)
    if not explanations:
        st.error("JSON 형식이 예상(객체 리스트)과 다릅니다. `step9_llm_explanation_stad.py` 출력을 확인하세요.")
        st.json(raw if isinstance(raw, (dict, list)) else {"raw": str(raw)})
        return

    st.info(f"총 **{len(explanations)}**개 약물 설명 (Ollama 또는 `--dry-run` placeholder)")

    md_path = rd / "stad_drug_explanations_report.md"
    if md_path.exists():
        with st.expander("Markdown report (`stad_drug_explanations_report.md`)", expanded=False):
            st.markdown(md_path.read_text(encoding="utf-8", errors="replace"))

    drug_names = [str(e["drug_name"]) for e in explanations]
    selected = st.selectbox("약물 선택", drug_names)

    icons = {
        "FDA_APPROVED_GASTRIC": "✅",
        "FDA_APPROVED_CRC": "✅",
        "REPURPOSING_CANDIDATE": "🎯",
        "CLINICAL_TRIAL": "🔬",
        "RESEARCH_PHASE_GASTRIC": "📝",
        "RESEARCH_PHASE": "📝",
    }

    for exp in explanations:
        if str(exp["drug_name"]) != selected:
            continue
        cat = str(exp.get("category", ""))
        icon = icons.get(cat, "")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Category", f"{icon} {cat}")
        col2.metric("Safety", exp.get("safety_score", "—"))
        col3.metric("Validation", f"{exp.get('validation_count', 0)}/5")
        stg = exp.get("recommendation_stage", exp.get("context", {}).get("recommendation_stage"))
        col4.metric("3-stage", stg if stg is not None else "—")

        st.markdown(f"**Target**: {exp.get('target', 'N/A')}")
        st.markdown(f"**Subtype context**: {exp.get('stad_subtype', 'N/A')}")

        st.markdown("---")
        st.markdown("### Explanation")
        st.markdown(str(exp.get("explanation", "")))
        break
