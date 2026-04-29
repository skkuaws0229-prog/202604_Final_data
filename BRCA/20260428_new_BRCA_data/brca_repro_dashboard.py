#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except Exception:  # pragma: no cover
    px = None


BASE = Path(__file__).resolve().parent
STEP4_SUMMARY = BASE / "brca_model_performance_summary.csv"
STEP5_VALIDATION = BASE / "brca_directive_ensemble_validation_summary.csv"
STEP5_TOP30 = BASE / "brca_directive_top30_tiered_candidates.csv"
STEP6_TOP15 = BASE / "step6_metabric_validation" / "brca_top15_metabric_validated.csv"
STEP6_TOP30 = BASE / "step6_metabric_validation" / "brca_top30_metabric_scored.csv"
STEP7_TOP30 = BASE / "step7_admet_22assay" / "brca_admet_22assay_top30_detailed.csv"
STEP7_TOP15 = BASE / "step7_admet_22assay" / "brca_final15_after_admet.csv"

TIER_DEFINITIONS = {
    "유방암 치료제": "Positive control로 해석하는 실제 유방암 치료제",
    "유방암 적응증 확장 연구 치료제": "유방암 임상연구 또는 적응증 확장 시도가 확인된 치료제",
    "유방암 비사용 치료제": "치료제이지만 현재 기준 유방암 직접 사용 근거가 제한적인 약물",
    "화합물 또는 미지 약물": "보충제, 실험용 저분자, 개발 코드명 후보 등 discovery 성격 물질",
}


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def metric_card_row(items: list[tuple[str, str]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


def render_tier_definition_box() -> None:
    st.markdown("### Tier Definition")
    for tier_name, desc in TIER_DEFINITIONS.items():
        st.markdown(f"- `{tier_name}`: {desc}")


def render_overview() -> None:
    step5 = load_csv(STEP5_VALIDATION)
    top30 = load_csv(STEP5_TOP30)
    step6 = load_csv(STEP6_TOP30)
    step7 = load_csv(STEP7_TOP30)
    final15 = load_csv(STEP7_TOP15)

    st.subheader("Overview")
    if not step5.empty:
        winner = step5.sort_values(["eval_mode", "spearman"], ascending=[True, False])
        groupcv_a = step5[(step5["config"] == "A") & (step5["eval_mode"] == "groupcv")]
        scaffold_a = step5[(step5["config"] == "A") & (step5["eval_mode"] == "scaffoldcv")]
        metric_card_row(
            [
                ("Directive Winner", "A"),
                ("GroupCV Spearman", f"{groupcv_a['spearman'].iloc[0]:.4f}" if not groupcv_a.empty else "-"),
                ("ScaffoldCV Spearman", f"{scaffold_a['spearman'].iloc[0]:.4f}" if not scaffold_a.empty else "-"),
                ("Top30", str(len(load_csv(STEP5_TOP30)))),
                ("Final15", str(len(final15))),
            ]
        )

    if not step7.empty:
        counts = step7["verdict"].value_counts()
        metric_card_row(
            [
                ("Step7 PASS", str(int(counts.get("PASS", 0)))),
                ("Step7 WARNING", str(int(counts.get("WARNING", 0)))),
                ("Step7 FAIL", str(int(counts.get("FAIL", 0)))),
                ("Hard Fail", str(int(step7["hard_fail"].sum()))),
                ("Step6 Survival+", str(int(step6["survival_sig"].sum())) if not step6.empty else "-"),
            ]
        )

    render_tier_definition_box()

    st.markdown("### Interpretation")
    st.markdown("- Step6 METABRIC is the biological validation layer.")
    st.markdown("- Step7 ADMET 22-assay is the practical selection layer for the current Final15.")
    st.markdown("- The current Final15 mixes standard breast-cancer therapies, indication-expansion candidates, non-breast therapies, and Tier4 compounds.")
    st.markdown("- Tier4 compounds are useful discovery signals, but they should be interpreted more cautiously than approved therapies.")

    if not top30.empty:
        st.markdown("### Step5 Tier Mix")
        tier_dist = top30["tier_name"].value_counts().rename_axis("tier_name").reset_index(name="count")
        if px is not None:
            fig = px.bar(tier_dist, x="tier_name", y="count", color="tier_name", title="Step5 Top30 Tier Distribution")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(tier_dist, use_container_width=True, hide_index=True)

    st.markdown("### Final15 Snapshot")
    if not final15.empty:
        st.dataframe(
            final15[
                [
                    "final_admet_rank",
                    "drug_name",
                    "tier_name",
                    "verdict",
                    "safety_score",
                    "confidence_grade",
                    "n_total_matches",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


def render_step4() -> None:
    df = load_csv(STEP4_SUMMARY)
    st.subheader("Step4 Modeling Summary")
    if df.empty:
        st.info("Step4 summary file not found.")
        return

    metric = st.selectbox("Metric", ["groupcv_spearman", "scaffoldcv_spearman", "cv_spearman", "overfit_gap_groupcv"], index=0)
    filtered = df.sort_values(metric, ascending=(metric == "overfit_gap_groupcv"))
    st.dataframe(filtered, use_container_width=True, hide_index=True)

    if px is not None:
        fig = px.bar(
            filtered,
            x="model",
            y=metric,
            color="family",
            facet_col="phase",
            title=f"BRCA Step4 {metric}",
        )
        st.plotly_chart(fig, use_container_width=True)


def render_step5() -> None:
    validation = load_csv(STEP5_VALIDATION)
    top30 = load_csv(STEP5_TOP30)
    st.subheader("Step5 Ensemble + Tiered Top30")
    if not validation.empty:
        st.markdown("### Ensemble Validation")
        st.dataframe(validation, use_container_width=True, hide_index=True)
        if px is not None:
            fig = px.bar(
                validation,
                x="eval_mode",
                y="spearman",
                color="config",
                barmode="group",
                title="Directive A vs B by Evaluation Mode",
            )
            st.plotly_chart(fig, use_container_width=True)

    if not top30.empty:
        st.markdown("### Tiered Top30")
        render_tier_definition_box()
        tier_filter = st.multiselect(
            "Tier filter",
            sorted(top30["tier_name"].dropna().unique().tolist()),
            default=sorted(top30["tier_name"].dropna().unique().tolist()),
        )
        sub = top30[top30["tier_name"].isin(tier_filter)].copy()
        st.dataframe(sub, use_container_width=True, hide_index=True)
        if px is not None:
            tier_dist = sub["tier_name"].value_counts().rename_axis("tier_name").reset_index(name="count")
            fig = px.bar(tier_dist, x="tier_name", y="count", color="tier_name", title="Filtered Tier Distribution")
            st.plotly_chart(fig, use_container_width=True)


def render_step6() -> None:
    top15 = load_csv(STEP6_TOP15)
    top30 = load_csv(STEP6_TOP30)
    st.subheader("Step6 METABRIC A/B/C")
    if top30.empty:
        st.info("Step6 files not found.")
        return

    metric_card_row(
        [
            ("Target Expressed", str(int(top30["target_expressed"].sum()))),
            ("BRCA Pathway", str(int(top30["brca_pathway"].sum()))),
            ("Survival Significant", str(int(top30["survival_sig"].sum()))),
            ("Known BRCA", str(int(top30["known_brca"].sum()))),
        ]
    )

    st.markdown("### Step6 Top15")
    if not top15.empty:
        st.dataframe(
            top15[
                [
                    "final_rank",
                    "rank",
                    "drug_name",
                    "tier_name",
                    "validation_score",
                    "target_expressed",
                    "brca_pathway",
                    "survival_sig",
                    "known_brca",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

    if px is not None:
        fig = px.scatter(
            top30,
            x="rank",
            y="validation_score",
            color="tier_name",
            hover_name="drug_name",
            title="Step6 Validation Score vs Original Top30 Rank",
        )
        st.plotly_chart(fig, use_container_width=True)


def render_step7() -> None:
    top30 = load_csv(STEP7_TOP30)
    final15 = load_csv(STEP7_TOP15)
    st.subheader("Step7 ADMET 22-Assay")
    if top30.empty:
        st.info("Step7 files not found.")
        return

    counts = top30["verdict"].value_counts()
    metric_card_row(
        [
            ("PASS", str(int(counts.get("PASS", 0)))),
            ("WARNING", str(int(counts.get("WARNING", 0)))),
            ("FAIL", str(int(counts.get("FAIL", 0)))),
            ("Hard Fail", str(int(top30["hard_fail"].sum()))),
            ("Final15", str(len(final15))),
        ]
    )

    st.markdown("### Final15 After ADMET")
    if not final15.empty:
        st.dataframe(
            final15[
                [
                    "final_admet_rank",
                    "rank",
                    "drug_name",
                    "tier_name",
                    "verdict",
                    "safety_score",
                    "n_total_matches",
                    "soft_flags",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Step7 Reading Guide")
    st.markdown("- `PASS` means the current protocol did not trigger exclusion-level concerns.")
    st.markdown("- `WARNING` means the drug remains in scope but needs extra caution in interpretation.")
    st.markdown("- `FAIL` or `Hard Fail` should be treated conservatively even if upstream ranking was high.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Verdict Distribution")
        dist = top30["verdict"].value_counts().rename_axis("verdict").reset_index(name="count")
        if px is not None:
            fig = px.pie(dist, values="count", names="verdict", hole=0.45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(dist, use_container_width=True, hide_index=True)
    with col2:
        st.markdown("### Final15 Tier Distribution")
        tier_dist = final15["tier_name"].value_counts().rename_axis("tier_name").reset_index(name="count")
        if px is not None:
            fig = px.bar(tier_dist, x="tier_name", y="count", color="tier_name")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(tier_dist, use_container_width=True, hide_index=True)

    st.markdown("### Step7 Full Table")
    st.dataframe(top30, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="BRCA Reproduction Dashboard", layout="wide")
    st.title("BRCA Reproduction Dashboard")
    st.caption("Directive ensemble -> METABRIC Step6 -> ADMET 22-assay Step7")

    tabs = st.tabs(["Overview", "Step4", "Step5", "Step6", "Step7"])
    with tabs[0]:
        render_overview()
    with tabs[1]:
        render_step4()
    with tabs[2]:
        render_step5()
    with tabs[3]:
        render_step6()
    with tabs[4]:
        render_step7()


if __name__ == "__main__":
    main()
