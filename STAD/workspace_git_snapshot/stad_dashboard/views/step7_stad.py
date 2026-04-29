"""
Step 7 (STAD): Colon dashboard/views/step7_admet.py 와 동일 레이아웃.

- Tab1: ADMET 요약 + Final Top 15 + 3단계(recommendation_stage)
- Tab2: AlphaFold (stad_alphafold_validation/)
- Tab3: TCGA-STAD 서브타입 / MSI 맥락 (stad_subtype_expression_analysis.json)
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


def _project_root() -> Path:
    # .../stad_dashboard/views/step7_stad.py -> parents[2] = repo STAD root
    return Path(__file__).resolve().parents[2]


def render() -> None:
    results_dir = _project_root() / "results"

    st.header("💊 Step 7: ADMET + AlphaFold + STAD subtype (Colon Step 7 대응)")

    tab1, tab2, tab3 = st.tabs(["ADMET & Top 15", "AlphaFold 3D", "STAD subtype / MSI"])

    # ─── Tab 1: ADMET + Top 15 + 3-stage ───
    with tab1:
        st.subheader("ADMET Gate (Choi Protocol — 22 Assays)")

        admet_path = results_dir / "stad_admet_summary.json"
        if admet_path.exists():
            admet = json.loads(admet_path.read_text(encoding="utf-8"))
            col1, col2, col3, col4 = st.columns(4)
            vc = admet.get("verdict_counts", {})
            col1.metric("PASS", vc.get("PASS", 0))
            col2.metric("WARNING", vc.get("WARNING", 0))
            col3.metric("FAIL", vc.get("FAIL", 0))
            col4.metric("Avg Safety", f"{float(admet.get('avg_safety_score', 0) or 0):.2f}")
            st.caption(admet.get("method") or "22 ADMET assays + Tanimoto (STAD)")
        else:
            st.warning("`results/stad_admet_summary.json` 없음 — `scripts/step7_1_admet_filtering_stad.py` 실행")

        st.markdown("---")
        st.subheader("🏆 Final Top 15 + 3단계 구분")

        stage_path = results_dir / "stad_step7_three_stage_summary.json"
        if stage_path.exists():
            stg = json.loads(stage_path.read_text(encoding="utf-8"))
            counts = stg.get("counts_by_stage", {})
            c1, c2, c3 = st.columns(3)
            c1.metric("1단계 (전환·표준)", counts.get("1", 0))
            c2.metric("2단계 (근거·검토)", counts.get("2", 0))
            c3.metric("3단계 (탐색·보조)", counts.get("3", 0))
            with st.expander("3단계 규칙 정의", expanded=False):
                st.json(stg.get("definitions", {}))

        top15_path = results_dir / "stad_final_top15.csv"
        if top15_path.exists():
            top15 = pd.read_csv(top15_path)
            name_col = "drug_name" if "drug_name" in top15.columns else "DRUG_NAME"
            cat_col = "usage_category" if "usage_category" in top15.columns else None

            if cat_col and cat_col in top15.columns:
                st.write("**usage_category**")
                cat_counts = top15[cat_col].value_counts()
                icons = {
                    "FDA_APPROVED_GASTRIC": "✅",
                    "REPURPOSING_CANDIDATE": "🎯",
                    "CLINICAL_TRIAL": "🔬",
                    "RESEARCH_PHASE_GASTRIC": "📝",
                }
                for cat, cnt in cat_counts.items():
                    icon = icons.get(str(cat), "")
                    st.write(f"{icon} **{cat}**: {cnt}")

            base_cols = [
                "recommendation_stage",
                "recommendation_stage_label_ko",
                "recommendation_rank",
                "usage_priority_rank",
                name_col,
                "usage_category",
                "target",
                "safety_score",
                "verdict",
                "n_clinical_trials",
            ]
            display_cols = [c for c in base_cols if c in top15.columns]
            st.dataframe(top15[display_cols], use_container_width=True, hide_index=True)
        else:
            st.warning("`results/stad_final_top15.csv` 없음 — `scripts/step7_2_select_top15_stad.py` 실행")

    # ─── Tab 2: AlphaFold ───
    with tab2:
        st.subheader("AlphaFold Structure Validation (STAD)")

        af_path = results_dir / "stad_alphafold_validation" / "stad_alphafold_validation_results.json"
        if af_path.exists():
            af = json.loads(af_path.read_text(encoding="utf-8"))
            summary = af.get("summary", {})
            col1, col2, col3 = st.columns(3)
            col1.metric("Structures", af.get("structures_downloaded", 0))
            col2.metric("Avg pLDDT", summary.get("avg_plddt", 0))
            col3.metric("Pockets", summary.get("targets_with_pocket", 0))

            structures = af.get("structures", [])
            if structures:
                rows = []
                for s in structures:
                    plddt = s.get("plddt") or {}
                    pocket = s.get("pocket") or {}
                    rows.append(
                        {
                            "Gene": s.get("gene", ""),
                            "UniProt": s.get("uniprot_id", ""),
                            "Drug(s)": ", ".join(s.get("drugs", [])[:2]),
                            "pLDDT": plddt.get("mean", 0) if plddt else 0,
                            "Pocket": pocket.get("n_residues", 0) if pocket else 0,
                            "Volume": pocket.get("volume", 0) if pocket else 0,
                        }
                    )
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            viewer_path = results_dir / "stad_alphafold_validation" / "stad_alphafold_3d_viewer.html"
            if viewer_path.exists():
                st.markdown("#### 🔬 3D Protein Viewer")
                html_content = viewer_path.read_text(encoding="utf-8", errors="replace")
                st.components.v1.html(html_content, height=700, scrolling=True)
        else:
            st.info("`results/stad_alphafold_validation/` 없음 — `scripts/step7_5_alphafold_validation_stad.py` 실행 (네트워크 필요)")

    # ─── Tab 3: STAD subtype (Colon COAD/READ 대응) ───
    with tab3:
        st.subheader("TCGA-STAD subtype / MSI context (Step 7.6)")

        cr_path = results_dir / "stad_subtype_expression_analysis.json"
        if cr_path.exists():
            cr = json.loads(cr_path.read_text(encoding="utf-8"))

            st.caption(f"비교 모드: **{cr.get('comparison', 'N/A')}**  |  축: `{cr.get('disease', '')}`")

            gl = cr.get("group_labels") or []
            ns = cr.get("n_samples") or {}
            if len(gl) >= 2 and isinstance(ns, dict):
                col1, col2 = st.columns(2)
                col1.metric(f"{gl[0]} samples", ns.get(gl[0], 0))
                col2.metric(f"{gl[1]} samples", ns.get(gl[1], 0))

            expr = cr.get("expression_results") or []
            if expr:
                st.write("**Target gene differential (요약)**")
                st.dataframe(pd.DataFrame(expr), use_container_width=True, hide_index=True)

            ctx_csv = results_dir / "stad_subtype_drug_context.csv"
            if ctx_csv.exists():
                st.write("**약물별 맥락 (drug context)**")
                st.dataframe(pd.read_csv(ctx_csv), use_container_width=True, hide_index=True)
        else:
            st.info("`results/stad_subtype_expression_analysis.json` 없음 — `scripts/step7_6_stad_subtype_analysis.py` 실행")
