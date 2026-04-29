"""Step 8 (STAD): Neo4j 요약 + 질환별 KG 뷰어 (위암 실데이터 + 타암종 참조/형제 프로젝트)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import streamlit as st


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _assets_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "kg_reference"


def _workspace_parent() -> Path:
    return _root().parent


def _load_kg_generator():
    script = _root() / "scripts" / "step8_generate_kg_viewer_stad.py"
    spec = importlib.util.spec_from_file_location("stad_step8_kg_viewer_gen", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load KG viewer generator")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.generate_kg_viewer


@st.cache_data(show_spinner=False)
def _cached_kg_html(json_path_str: str, mtime: float) -> str:
    del mtime  # cache key only — file 갱신 시 재생성
    gen = _load_kg_generator()
    return gen(Path(json_path_str), None)


def _resolve_kg_json(disease_key: str) -> tuple[Path | None, str]:
    """Return (path, provenance note)."""
    rd = _root() / "results"
    assets = _assets_dir()
    sib_colon = _workspace_parent() / "20260420_new_pre_project_biso_Colon" / "results" / "knowledge_graph_data.json"

    if disease_key == "gastric":
        p = rd / "stad_knowledge_graph_data.json"
        if p.exists():
            return p, "STAD 파이프라인 산출물 (`step8_export_kg_json_stad.py`)."
        return None, "위암: `results/stad_knowledge_graph_data.json` 없음 — Step 8a 스크립트 실행."

    if disease_key == "colorectal":
        if sib_colon.exists():
            return sib_colon, "형제 저장소 Colon `results/knowledge_graph_data.json` (로컬에 있을 때만)."
        p = assets / "colorectal.json"
        return p, "참조 데모 그래프 (`stad_dashboard/assets/kg_reference/colorectal.json`). 전체 CRC 파이프라인은 Colon 프로젝트 실행."

    if disease_key == "lung":
        p = assets / "lung.json"
        return p, "참조 데모 그래프 (`stad_dashboard/assets/kg_reference/lung.json`)."

    if disease_key == "breast":
        p = assets / "breast.json"
        return p, "참조 데모 그래프 (`stad_dashboard/assets/kg_reference/breast.json`)."

    return None, ""


def render() -> None:
    rd = _root() / "results"

    st.header("🕸️ Step 8: Knowledge Graph")

    neo_path = rd / "stad_neo4j_load_summary.json"
    if neo_path.exists():
        neo = json.loads(neo_path.read_text(encoding="utf-8"))
        st.subheader("Neo4j load summary (STAD)")
        st.json(neo)
        status = neo.get("status", "")
        if status == "skipped":
            st.warning(
                "자격 증명은 저장소에 넣지 마세요. 로컬 환경에만 `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` 를 설정한 뒤 "
                "`python3 scripts/step8_neo4j_load_stad.py` 를 실행하면 적재됩니다."
            )
        elif status == "applied":
            st.success("Neo4j 적재 요약이 기록되었습니다. Aura 콘솔에서 노드·관계를 확인하세요.")
    else:
        st.info("`results/stad_neo4j_load_summary.json` 없음 — `./scripts/run_step8_9_stad.sh` 또는 Neo4j 스크립트 실행.")

    st.markdown("---")
    st.subheader("질환별 네트워크 (로컬 뷰어)")

    disease_labels = {
        "gastric": "위암 (STAD, TCGA-STAD 파이프라인)",
        "colorectal": "대장암 (Colon 결과 우선, 없으면 참조 데모)",
        "lung": "폐암 (참조 데모 — Lung 파이프라인 KG JSON 연동 시 교체 가능)",
        "breast": "유방암 (참조 데모)",
    }
    choice = st.radio(
        "질환 선택",
        list(disease_labels.keys()),
        format_func=lambda k: disease_labels[k],
        horizontal=True,
    )

    data_path, note = _resolve_kg_json(choice)
    st.caption(note)

    if data_path is None or not data_path.exists():
        st.warning("선택한 질환용 KG JSON을 찾을 수 없습니다.")
        return

    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
        nn, ne = len(data.get("nodes", [])), len(data.get("edges", []))
        c1, c2, c3 = st.columns(3)
        c1.metric("Nodes", nn)
        c2.metric("Edges", ne)
        c3.metric("Source file", data_path.name)
    except Exception as exc:
        st.error(f"JSON 읽기 실패: {exc}")
        return

    try:
        mtime = data_path.stat().st_mtime
        html = _cached_kg_html(str(data_path.resolve()), mtime)
        st.markdown("#### Interactive network")
        st.components.v1.html(html, height=780, scrolling=True)
    except Exception as exc:
        st.error(f"뷰어 생성 실패: {exc}")
