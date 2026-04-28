#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RESULT_TAG = "20260427_hnsc_step4_v1"
RES = ROOT / "results" / RESULT_TAG
EXT = ROOT / "external_validation" / RESULT_TAG


def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


st.set_page_config(page_title="HNSC Pipeline Dashboard", layout="wide")
st.title("HNSC Pipeline Dashboard")
st.caption(f"Root: {ROOT}")

top15 = safe_read_csv(RES / "step7_top15_hnsc_provisional.csv")
top15_fixed = safe_read_csv(RES / "step7_top15_hnsc_provisional_with_fixed_tier.csv")
top30_fixed = safe_read_csv(RES / "top30_tier1234_fixed_hnsc.csv")
ext = safe_read_csv(EXT / "top30_external_validation_independent.csv")
summary = read_json(EXT / "external_validation_independent_summary.json")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Step6 Any-match (Top30)", "28 / 30")
c2.metric("Unmatched", "2")
c3.metric("Step7 Provisional Top15", str(len(top15_fixed)) if not top15_fixed.empty else str(len(top15)))
c4.metric(
    "Step7 REVIEW",
    str(int((top15_fixed["step7_decision"] == "REVIEW").sum())) if not top15_fixed.empty else (str(int((top15["step7_decision"] == "REVIEW").sum())) if not top15.empty else "0"),
)

st.subheader("Step6 Source Coverage")
if summary:
    st.json(summary.get("support_counts", {}))
else:
    st.info("Step6 summary json not found.")

st.subheader("Step4 모델학습/앙상블 요약")
st.markdown(
    "- 학습 범위: ML/DL/Graph 실행 후 대표 앙상블로 Top30 산출\n"
    "- 대표 결과 태그: `20260427_hnsc_step4_v1`\n"
    "- 대표 Top30 파일: `results/20260427_hnsc_step4_v1/top30_tier1234_fixed_hnsc.csv`\n"
    "- 단계 원칙: Step4(모델학습) -> 대표 앙상블 Top30 -> Step6 외부검증 -> Step7 ADMET/Top15"
)
step4_gate = safe_read_csv(RES / "step5_gate_eval_spearman_table.csv")
if step4_gate.empty:
    st.info("Step4 전체 모델 게이트 표(`step5_gate_eval_spearman_table.csv`)가 현재 브랜치에는 없어, 운영 요약/대표 산출물 중심으로 표시합니다.")
else:
    st.dataframe(step4_gate, width="stretch", height=320)

st.subheader("Step6 External Validation Snapshot")
if ext.empty:
    st.warning("Step6 external CSV not found.")
else:
    cols = [
        c
        for c in [
            "rank",
            "DRUG_NAME",
            "prism_status",
            "clinical_trial_has_evidence",
            "patient_context_has_evidence",
            "opentargets_has_evidence",
            "cosmic_has_evidence",
        ]
        if c in ext.columns
    ]
    st.dataframe(ext[cols], width="stretch", height=360)

st.subheader("Step7 Top15 (Provisional)")
if top15_fixed.empty and top15.empty:
    st.warning("Step7 provisional file not found.")
else:
    show_df = top15_fixed if not top15_fixed.empty else top15
    st.dataframe(show_df, width="stretch", height=420)
    if "fixed_tier" in show_df.columns:
        st.caption(
            "Top15 Tier 분포: "
            + ", ".join(
                f"{k}={v}" for k, v in show_df["fixed_tier"].value_counts().sort_index().to_dict().items()
            )
        )

st.subheader("Top30 Fixed Tier1/2/3/4")
if top30_fixed.empty:
    st.info("Top30 fixed tier file not found.")
else:
    st.dataframe(top30_fixed, width="stretch", height=360)
    st.caption(
        "Top30 Tier 분포: "
        + ", ".join(f"{k}={v}" for k, v in top30_fixed["tier"].value_counts().sort_index().to_dict().items())
    )

st.subheader("Linked Reports")
st.markdown("- `reports/HNSC_step6_external_validation_preflight_20260428.md`")
st.markdown("- `reports/HNSC_step6_final_and_step7_progress_20260428.md`")
st.markdown("- `reports/HNSC_dashboard_snapshot_20260428.md`")
st.markdown("- `reports/HNSC_pipeline_full_summary_20260428.md`")

