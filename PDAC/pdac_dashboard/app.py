#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
TAG = "20260427_pdac_step4_v1_no_holdout"
RES = ROOT / "results" / TAG
EXT = ROOT / "external_validation" / TAG
ADM = ROOT / "admet" / TAG


def safe_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def safe_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


st.set_page_config(page_title="PDAC Dashboard", layout="wide")
st.title("PDAC Pipeline Dashboard")
st.caption(f"Root: {ROOT}")

top30 = safe_csv(RES / "top30_pdac_with_vt.csv")
top15 = safe_csv(RES / "step7_top15_pdac_admet_with_vt.csv")
s6 = safe_json(EXT / "external_validation_independent_summary.json")
s7 = safe_json(ADM / "admet_summary_independent.json")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Top30", str(len(top30)) if not top30.empty else "0")
c2.metric("Step6 PRISM", f"{s6.get('prism_evidence_rows', 'NA')}/30")
c3.metric("Step7 assay", str(s7.get("assay_count", "NA")))
c4.metric("Step7 Top15", str(len(top15)) if not top15.empty else "0")

st.subheader("Step6 External Validation Summary")
if s6:
    st.json(s6)
else:
    st.warning("Step6 summary json not found.")

st.subheader("Step7 ADMET Summary")
if s7:
    st.json(s7)
else:
    st.warning("Step7 summary json not found.")

st.subheader("Top30 (VT 포함)")
if top30.empty:
    st.warning("Top30 csv not found.")
else:
    st.dataframe(top30, width="stretch", height=420)

st.subheader("Top15 (VT + ADMET)")
if top15.empty:
    st.warning("Top15 csv not found.")
else:
    st.dataframe(top15, width="stretch", height=360)

st.subheader("Linked Docs")
st.markdown("- `PDAC_reproduction_protocol_20260428.md`")
st.markdown("- `reports/PDAC_pipeline_full_summary_20260428.md`")
