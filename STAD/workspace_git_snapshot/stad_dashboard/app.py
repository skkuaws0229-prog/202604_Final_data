from __future__ import annotations

import importlib.util
import json
import math
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Latest completed Step4 bundle (local)
STEP4_RESULT_TAG = "20260422_stad_step4_v2"
STEP4_RUN_ID = "step4_stad_inputs_20260422_002"

# For stacking/blending, prefer the richest feature phase that actually has rows for a family.
ENSEMBLE_PHASE_PRIORITY = ("2C_context_smiles", "2B_numeric_smiles", "2A_numeric")


def file_status(path: Path) -> str:
    if path.exists():
        return "OK"
    return "MISSING"


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def fmt_ts(path: Path) -> str:
    if not path.exists():
        return "-"
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "-"


def parse_step4_phase_from_filename(fname: str) -> str:
    stem = Path(fname).stem
    parts = stem.split("_")
    idx = -1
    for anchor in ("ml", "dl", "graph"):
        try:
            idx = parts.index(anchor)
            break
        except ValueError:
            continue
    if idx == -1:
        return "unknown"
    phase_key = "_".join(parts[:idx])
    if phase_key.startswith("stad_numeric_context_smiles"):
        return "2C_context_smiles"
    if phase_key.startswith("stad_numeric_smiles"):
        return "2B_numeric_smiles"
    if phase_key.startswith("stad_numeric"):
        return "2A_numeric"
    return phase_key


def iter_step4_groupcv_rows(result_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in ("ml", "dl", "graph"):
        d = result_root / family
        if not d.exists():
            continue
        for p in sorted(d.glob("*_groupcv.json")):
            phase = parse_step4_phase_from_filename(p.name)
            data = read_json(p)
            if not isinstance(data, dict):
                continue
            for model_name, payload in data.items():
                if not isinstance(payload, dict):
                    continue
                summ = payload.get("summary") or {}
                of = payload.get("overfitting_check") or {}
                val_sp = summ.get("val_spearman_mean")
                mean_gap = of.get("mean_gap")
                max_gap = of.get("max_gap")
                n_bad = of.get("n_overfitting_folds")
                warn = bool(of.get("warning"))
                if val_sp is None or mean_gap is None or max_gap is None:
                    continue
                rows.append(
                    {
                        "family": family,
                        "phase": phase,
                        "model": str(model_name),
                        "val_spearman_mean": float(val_sp),
                        "mean_gap": float(mean_gap),
                        "max_gap": float(max_gap),
                        "n_bad_folds": int(n_bad) if n_bad is not None else None,
                        "warning": warn,
                        "file": p.name,
                    }
                )
    return rows


def _ensemble_score_row(r: dict[str, Any]) -> float:
    val = r["val_spearman_mean"]
    if val <= 0:
        return float("-inf")
    gap_pen = 1.2 * r["mean_gap"] + 0.8 * r["max_gap"]
    warn_pen = 0.08 if r["warning"] else 0.0
    return val - gap_pen - warn_pen


def _ensemble_best_ranked(rows_subset: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows_subset:
        return None
    ranked = sorted(rows_subset, key=_ensemble_score_row, reverse=True)
    top = ranked[0]
    if _ensemble_score_row(top) == float("-inf"):
        return None
    return top


def _ensemble_best_by_phase_priority(candidate_rows: list[dict[str, Any]]) -> dict[str, Any]:
    for phase in ENSEMBLE_PHASE_PRIORITY:
        subset = [r for r in candidate_rows if r["phase"] == phase]
        picked = _ensemble_best_ranked(subset)
        if picked:
            return picked
    return {}


def ensemble_pick_catboost_dl_graph(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """CatBoost (ML) + DL + Graph — same heuristic, CatBoost-only ML slot."""
    cat_rows = [
        r
        for r in rows
        if r["family"] == "ml" and r["model"] in ("CatBoost", "CatBoost_Fallback_GBR2")
    ]
    return {
        "catboost": _ensemble_best_by_phase_priority(cat_rows),
        "dl": _ensemble_best_by_phase_priority([r for r in rows if r["family"] == "dl"]),
        "graph": _ensemble_best_by_phase_priority([r for r in rows if r["family"] == "graph"]),
    }


def _phase_short(phase_key: str) -> str:
    if phase_key == "2C_context_smiles":
        return "2C"
    if phase_key == "2B_numeric_smiles":
        return "2B"
    if phase_key == "2A_numeric":
        return "2A"
    return phase_key[:6]


def _fmt_num(x: Any, nd: int = 4) -> str:
    if x is None:
        return "—"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(v):
        return "—"
    return f"{v:.{nd}f}"


def _ensemble_payload_to_tables(ens: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Summary, per-phase components, melted bars for Streamlit charts."""
    summary_rows: list[dict[str, Any]] = []
    comp_rows: list[dict[str, Any]] = []
    melt_rows: list[dict[str, Any]] = []

    for block in ens.get("phases") or []:
        if not isinstance(block, dict):
            continue
        ph = str(block.get("phase", "?"))
        if not block.get("ok"):
            summary_rows.append({"phase": ph, "status": "skipped", "reason": block.get("reason", "")})
            continue

        oof = block.get("oof_spearman_vs_y") or {}
        jsn = block.get("groupcv_json_val_spearman_mean") or {}
        ensd = block.get("ensemble") or {}
        aux = block.get("lung_style_aux") or {}
        models = block.get("models") or {}
        wj = ensd.get("weighted_json_weights")

        rho_pair = aux.get("mean_pairwise_oof_prediction_spearman")
        if rho_pair is None:
            rho_pair = aux.get("diversity_mean_pairwise_spearman")
        comp = aux.get("complementarity_1_minus_pairwise_pred_rho")
        if comp is None and isinstance(rho_pair, (int, float)) and math.isfinite(float(rho_pair)):
            comp = 1.0 - float(rho_pair)

        summary_rows.append(
            {
                "phase": ph,
                "status": "ok",
                "CatBoost_OOF_ρ": oof.get("catboost"),
                "DL_OOF_ρ": oof.get("dl"),
                "Graph_OOF_ρ": oof.get("graph"),
                "best_single_OOF_ρ": oof.get("best_single"),
                "ensemble_Simple_ρ": ensd.get("simple_spearman"),
                "ensemble_Weighted_ρ": ensd.get("weighted_json_spearman"),
                "ensemble_GridOpt_ρ": ensd.get("optimal_grid_spearman"),
                "gain_Simple": aux.get("gain_simple_vs_best_single"),
                "gain_Weighted": aux.get("gain_weighted_vs_best_single"),
                "gain_GridOpt": aux.get("gain_optimal_vs_best_single"),
                "pred_pairwise_rho_mean": rho_pair,
                "complementarity_1_minus_rho": comp,
                "consensus_std": aux.get("consensus_mean_std_across_models"),
                "w_CatBoost": wj[0] if isinstance(wj, list) and len(wj) > 0 else None,
                "w_DL": wj[1] if isinstance(wj, list) and len(wj) > 1 else None,
                "w_Graph": wj[2] if isinstance(wj, list) and len(wj) > 2 else None,
                "grid_w1": (ensd.get("optimal_grid_weights") or [None, None, None])[0],
                "grid_w2": (ensd.get("optimal_grid_weights") or [None, None, None])[1],
                "grid_w3": (ensd.get("optimal_grid_weights") or [None, None, None])[2],
            }
        )

        comp_rows.append(
            {
                "phase": ph,
                "CatBoost_model": models.get("catboost_ml"),
                "DL_model": models.get("dl"),
                "Graph_model": models.get("graph"),
                "JSON_valρ_CatBoost": jsn.get("catboost"),
                "JSON_valρ_DL": jsn.get("dl"),
                "JSON_valρ_Graph": jsn.get("graph"),
            }
        )

        melt_rows.append({"phase": ph, "method": "Simple", "ρ": ensd.get("simple_spearman")})
        melt_rows.append({"phase": ph, "method": "Weighted", "ρ": ensd.get("weighted_json_spearman")})
        melt_rows.append({"phase": ph, "method": "GridOpt", "ρ": ensd.get("optimal_grid_spearman")})

    return (
        pd.DataFrame(summary_rows),
        pd.DataFrame(comp_rows),
        pd.DataFrame(melt_rows),
    )


def _markdown_ensemble_table(df: pd.DataFrame) -> str:
    if df.empty or "phase" not in df.columns:
        return "_앙상블 요약 행이 없습니다._"
    cols = [
        "phase",
        "CatBoost_OOF_ρ",
        "DL_OOF_ρ",
        "Graph_OOF_ρ",
        "best_single_OOF_ρ",
        "ensemble_Simple_ρ",
        "ensemble_Weighted_ρ",
        "ensemble_GridOpt_ρ",
        "gain_Simple",
        "gain_Weighted",
        "gain_GridOpt",
        "pred_pairwise_rho_mean",
        "complementarity_1_minus_rho",
    ]
    if not any(c in df.columns for c in ("pred_pairwise_rho_mean", "complementarity_1_minus_rho")):
        cols = [c for c in cols if c not in ("pred_pairwise_rho_mean", "complementarity_1_minus_rho")]
        if "diversity" in df.columns:
            cols.append("diversity")
    use = [c for c in cols if c in df.columns]
    header = "| " + " | ".join(use) + " |"
    sep = "| " + " | ".join(["---"] * len(use)) + " |"
    lines = [header, sep]
    for _, row in df.iterrows():
        cells = [_fmt_num(row.get(c)) if c != "phase" else str(row.get(c, "")) for c in use]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def summarize_ensemble_headline(ens: dict[str, Any]) -> dict[str, Any]:
    """Single-row KPIs for Step4 banner (best / mean GridOpt, etc.)."""
    grids: list[tuple[str, float]] = []
    wtd: list[float] = []
    smp: list[float] = []
    for b in ens.get("phases") or []:
        if not isinstance(b, dict) or not b.get("ok"):
            continue
        ed = b.get("ensemble") or {}
        ph = str(b.get("phase", "?"))
        g = ed.get("optimal_grid_spearman")
        w = ed.get("weighted_json_spearman")
        s = ed.get("simple_spearman")
        if isinstance(g, (int, float)) and math.isfinite(float(g)):
            grids.append((ph, float(g)))
        if isinstance(w, (int, float)) and math.isfinite(float(w)):
            wtd.append(float(w))
        if isinstance(s, (int, float)) and math.isfinite(float(s)):
            smp.append(float(s))
    if not grids:
        return {
            "y_n": ens.get("y_n"),
            "best_phase": None,
            "best_grid": float("nan"),
            "mean_grid": float("nan"),
            "mean_weighted": float("nan"),
            "mean_simple": float("nan"),
        }
    best_ph, best_g = max(grids, key=lambda x: x[1])
    return {
        "y_n": ens.get("y_n"),
        "best_phase": best_ph,
        "best_grid": best_g,
        "mean_grid": float(statistics.mean([x[1] for x in grids])),
        "mean_weighted": float(statistics.mean(wtd)) if wtd else float("nan"),
        "mean_simple": float(statistics.mean(smp)) if smp else float("nan"),
    }


def _plotly_ensemble_grouped_bar(melt_df: pd.DataFrame) -> Any | None:
    if melt_df.empty or "ρ" not in melt_df.columns:
        return None
    try:
        import plotly.express as px
    except ImportError:
        return None
    dd = melt_df.dropna(subset=["ρ"]).copy()
    if dd.empty:
        return None
    fig = px.bar(
        dd,
        x="phase",
        y="ρ",
        color="method",
        barmode="group",
        title="CatBoost + DL + Graph — ensemble vs method (OOF Spearman)",
        height=420,
    )
    fig.update_layout(yaxis_title="Spearman ρ", legend_title="Blend")
    return fig


def render_header() -> None:
    st.markdown(
        """
        <style>
        .stad-hero {
            background: linear-gradient(120deg, #7f1d1d 0%, #991b1b 35%, #b91c1c 100%);
            border-radius: 16px;
            padding: 24px 28px;
            margin-bottom: 16px;
            color: #fff;
            box-shadow: 0 6px 16px rgba(127, 29, 29, 0.25);
        }
        .stad-hero h1 {
            margin: 0 0 6px 0;
            font-size: 2rem;
        }
        .stad-hero p {
            margin: 0;
            opacity: 0.92;
            font-size: 1rem;
        }
        </style>
        <div class="stad-hero">
            <h1>STAD Drug Repurposing Pipeline</h1>
            <p>Stomach adenocarcinoma (TCGA-STAD) · 전 단계(0-1 … 9) + Overview — 왼쪽 사이드바에서 이동</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _exec_stad_view(filename: str) -> None:
    """Load `stad_dashboard/views/<filename>` without package path issues."""
    mod_path = Path(__file__).resolve().parent / "views" / filename
    if not mod_path.is_file():
        st.error(f"View module missing: `{mod_path}`")
        return
    spec = importlib.util.spec_from_file_location(f"stad_view_{filename.replace('.', '_')}", mod_path)
    if spec is None or spec.loader is None:
        st.error("Failed to create module spec for view")
        return
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.render()


def _nav_pages() -> list[str]:
    return [
        "Overview",
        "Step 0-1",
        "Step 2",
        "Step 3",
        "Step 3.5",
        "Step 4",
        "Step 5",
        "Step 6",
        "Step 7",
        "Step 8",
        "Step 9",
        "Protocol",
    ]


def render_sidebar_nav() -> str:
    """왼쪽 고정 사이드바 — 상단 11열 버튼(좁은 화면에서 잘림) 문제를 피함."""
    pages = _nav_pages()
    with st.sidebar:
        st.markdown("### STAD 단계")
        st.caption("Step 0-1부터 Step 9까지 동일 앱에서 전환합니다.")
        page = st.radio(
            "현재 페이지",
            pages,
            index=0,
            label_visibility="collapsed",
        )
    st.markdown(f"#### 현재: **{page}**")
    st.markdown("---")
    return page


def render_overview() -> None:
    """전 단계 요약 — 각 Step 탭으로 이동하기 전 상태 점검."""
    st.subheader("Overview: 파이프라인 단계별 산출물")
    st.caption("`STAD_reproduction_protocol.md` 순서와 대응. `results/`·`curated_data/`는 로컬 실행 후에만 OK로 표시됩니다.")

    rows: list[dict[str, Any]] = [
        {
            "Step": "0-1",
            "설명": "Raw 동기화, LINCS 링크, 코호트 tar",
            "대표 경로": "scripts/parallel_download_stad.sh, curated_data/",
            "OK?": all(
                (PROJECT_ROOT / p).exists()
                for p in (
                    "scripts/parallel_download_stad.sh",
                    "curated_data",
                )
            ),
        },
        {
            "Step": "2",
            "설명": "전처리·라벨·QC",
            "대표 경로": "data/labels.parquet, reports/step2_integrated_qc_report.json",
            "OK?": (PROJECT_ROOT / "reports/step2_integrated_qc_report.json").exists(),
        },
        {
            "Step": "3",
            "설명": "FE (Nextflow / Batch)",
            "대표 경로": "fe_qc/20260421_stad_fe_v1/features/features.parquet",
            "OK?": (PROJECT_ROOT / "fe_qc/20260421_stad_fe_v1/features/features.parquet").exists(),
        },
        {
            "Step": "3.5",
            "설명": "Feature selection",
            "대표 경로": "fe_qc/20260421_stad_fe_v1/features_slim.parquet",
            "OK?": (PROJECT_ROOT / "fe_qc/20260421_stad_fe_v1/features_slim.parquet").exists(),
        },
        {
            "Step": "4",
            "설명": "ML / DL / Graph GroupCV",
            "대표 경로": f"results/{STEP4_RESULT_TAG}/ml/",
            "OK?": (PROJECT_ROOT / "results" / STEP4_RESULT_TAG / "ml").exists(),
        },
        {
            "Step": "5",
            "설명": "CatBoost+DL+Graph 앙상블",
            "대표 경로": f"results/{STEP4_RESULT_TAG}/ensemble_catboost_dl_graph_groupcv.json",
            "OK?": (PROJECT_ROOT / "results" / STEP4_RESULT_TAG / "ensemble_catboost_dl_graph_groupcv.json").exists(),
        },
        {
            "Step": "6",
            "설명": "외부 5소스 + 종합",
            "대표 경로": "results/stad_comprehensive_validation_results.json",
            "OK?": (PROJECT_ROOT / "results/stad_comprehensive_validation_results.json").exists(),
        },
        {
            "Step": "7",
            "설명": "ADMET · Top15 · AlphaFold · 서브타입",
            "대표 경로": "results/stad_final_top15.csv",
            "OK?": (PROJECT_ROOT / "results/stad_final_top15.csv").exists(),
        },
        {
            "Step": "8",
            "설명": "KG JSON / 뷰어 / Neo4j(선택) · 질환별 네트워크",
            "대표 경로": "results/stad_knowledge_graph_data.json (+ 대시보드 참조 KG)",
            "OK?": (PROJECT_ROOT / "results/stad_knowledge_graph_data.json").exists(),
        },
        {
            "Step": "9",
            "설명": "LLM 근거 (Ollama 또는 dry-run)",
            "대표 경로": "results/stad_drug_explanations.json",
            "OK?": (PROJECT_ROOT / "results/stad_drug_explanations.json").exists(),
        },
    ]
    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )
    st.info(
        "Step 8에서 **위암**은 STAD `results/` 산출물을, **대장·폐·유방**은 저장소에 포함된 참조 KG 또는 "
        "형제 폴더 Colon `knowledge_graph_data.json`(로컬 생성 시)을 사용합니다."
    )


def render_step_0_1() -> None:
    st.subheader("Step 0-1: Raw Sync")
    st.caption(
        "README·`STAD_reproduction_protocol.md` §1: Stad_raw 동기화, LINCS GSE92742 정렬, "
        "TCGA-STAD 코호트 tar 등. (Colon 파이프라인의 Step 0–1에 해당; STAD는 단일 탭으로 묶음)"
    )

    checks = [
        PROJECT_ROOT / "scripts/parallel_download_stad.sh",
        PROJECT_ROOT / "scripts/download_stad_cohort_data.sh",
        PROJECT_ROOT / "scripts/link_lincs_gse92742_from_colon.sh",
        PROJECT_ROOT / "curated_data",
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "curated_data/cbioportal/stad_tcga_pan_can_atlas_2018",
        PROJECT_ROOT / "curated_data/geo/GSE62254",
    ]
    for p in checks:
        st.write(f"- `{p.relative_to(PROJECT_ROOT)}`: **{file_status(p)}**")
    st.info("`SYNC_S3=1 ./scripts/parallel_download_stad.sh` — `configs/CONTEXT.md` 의 Stad_raw 규약 참고.")


def render_step_2() -> None:
    st.subheader("Step 2: Preprocessing")
    st.caption("Step 2 outputs and key reports")

    checks = [
        PROJECT_ROOT / "data/labels.parquet",
        PROJECT_ROOT / "data/drug_features.parquet",
        PROJECT_ROOT / "data/depmap/depmap_crispr_long_stad.parquet",
        PROJECT_ROOT / "reports/step2_integrated_qc_report.json",
        PROJECT_ROOT / "reports/step2_stad_depmap_refilter.json",
    ]
    for p in checks:
        st.write(f"- `{p.relative_to(PROJECT_ROOT)}`: **{file_status(p)}**")


def render_step_3() -> None:
    st.subheader("Step 3: Feature Engineering")
    st.caption("FE output and manifest checks")

    checks = [
        PROJECT_ROOT / "fe_qc/20260421_stad_fe_v1/features/features.parquet",
        PROJECT_ROOT / "fe_qc/20260421_stad_fe_v1/pair_features/pair_features_newfe_v2.parquet",
        PROJECT_ROOT / "reports/step3_fe_manifest_qc.json",
    ]
    for p in checks:
        st.write(f"- `{p.relative_to(PROJECT_ROOT)}`: **{file_status(p)}**")


def render_step_3_5() -> None:
    st.subheader("Step 3.5: Feature Selection")
    st.caption("Feature Selection status and summary")

    fs_log_path = PROJECT_ROOT / "fe_qc/20260421_stad_fe_v1/feature_selection_log.json"
    fs_log = read_json(fs_log_path)

    checks = [
        PROJECT_ROOT / "scripts/feature_selection.py",
        PROJECT_ROOT / "fe_qc/20260421_stad_fe_v1/features_slim.parquet",
        PROJECT_ROOT / "fe_qc/20260421_stad_fe_v1/feature_selection_log.json",
        PROJECT_ROOT / "fe_qc/20260421_stad_fe_v1/feature_categories.json",
        PROJECT_ROOT / "fe_qc/20260421_stad_fe_v1/final_columns.json",
        PROJECT_ROOT / "fe_qc/20260421_stad_fe_v1/selection_log_init.json",
    ]

    for p in checks:
        st.write(f"- `{p.relative_to(PROJECT_ROOT)}`: **{file_status(p)}**")

    st.markdown("---")

    if fs_log is None:
        st.warning("Feature Selection log not found or not readable.")
        return

    initial_shape = fs_log.get("initial_shape", ["?", "?"])
    final_features = fs_log.get("final_counts", {}).get("total_features", "?")
    initial_cols = initial_shape[1] if len(initial_shape) > 1 else "?"

    c1, c2 = st.columns(2)
    c1.metric("Initial columns", str(initial_cols))
    c2.metric("Final selected features", str(final_features))

    steps = fs_log.get("steps", [])
    st.write("### Selection Steps")
    for s in steps:
        step = s.get("step", "?")
        before = s.get("before", "?")
        after = s.get("after", "?")
        removed = s.get("removed", "?")
        st.write(f"- `{step}`: {before} -> {after} (removed {removed})")

    chart_rows: list[dict[str, Any]] = []
    for s in steps:
        b, a = s.get("before"), s.get("after")
        if isinstance(b, (int, float)) and isinstance(a, (int, float)):
            chart_rows.append(
                {
                    "step": str(s.get("step", "?"))[:48],
                    "before": float(b),
                    "after": float(a),
                }
            )
    if chart_rows:
        st.markdown("---")
        st.write("### Step size chart (Lung-style bar overview)")
        cdf = pd.DataFrame(chart_rows).set_index("step")
        st.bar_chart(cdf)


def render_step_4() -> None:
    st.subheader("Step 4: Modeling (STAD)")
    st.caption("Step 4는 ML/DL/Graph 단일 모델 학습·평가 전용입니다. (앙상블은 Step 5)")

    result_root = PROJECT_ROOT / "results" / STEP4_RESULT_TAG
    data_run_dir = PROJECT_ROOT / "data" / STEP4_RUN_ID

    if not result_root.exists():
        st.error(
            "Step4 result bundle not found on disk for this workspace copy. "
            f"Expected: `{result_root}`"
        )
        st.info(
            "If you ran Step4 elsewhere, copy the folder into this repo path (or rerun locally) "
            "so `*_groupcv.json` files exist under `results/<tag>/{ml,dl,graph}/`."
        )

    meta_ml = result_root / "ml" / "run_meta_ml_stad.json"
    meta_dl = result_root / "dl" / "run_meta_dl_stad.json"
    meta_gr = result_root / "graph" / "run_meta_graph_stad.json"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Result tag", STEP4_RESULT_TAG)
    c2.metric("Run ID", STEP4_RUN_ID)
    c3.metric(
        "ML JSON count",
        str(len(list((result_root / "ml").glob("*.json")))) if (result_root / "ml").exists() else "0",
    )
    c4.metric(
        "Graph JSON count",
        str(len(list((result_root / "graph").glob("*.json")))) if (result_root / "graph").exists() else "0",
    )

    st.markdown("---")

    st.write("### Key paths")
    st.code(
        "\n".join(
            [
                f"results: {result_root}",
                f"inputs:  {data_run_dir}",
                f"meta:    {meta_ml}",
                f"meta:    {meta_dl}",
                f"meta:    {meta_gr}",
            ]
        ),
        language="text",
    )

    checks = [
        PROJECT_ROOT / "scripts/run_step4_stad.sh",
        PROJECT_ROOT / "scripts/run_ml_all_stad.py",
        PROJECT_ROOT / "scripts/run_dl_all_stad.py",
        PROJECT_ROOT / "scripts/run_graph_all_stad.py",
        result_root / "ml",
        result_root / "dl",
        result_root / "graph",
        data_run_dir / "X_numeric.npy",
        data_run_dir / "X_numeric_smiles.npy",
        data_run_dir / "X_numeric_context_smiles.npy",
        data_run_dir / "y_train.npy",
    ]
    st.write("### File checks")
    for p in checks:
        st.write(f"- `{p.relative_to(PROJECT_ROOT)}`: **{file_status(p)}** (mtime `{fmt_ts(p)}`)")

    st.markdown("---")

    st.write("### Meta (run parameters)")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.write("**ML meta**")
        st.json(read_json(meta_ml) or {})
    with m2:
        st.write("**DL meta**")
        st.json(read_json(meta_dl) or {})
    with m3:
        st.write("**Graph meta**")
        st.json(read_json(meta_gr) or {})

    st.markdown("---")

    st.caption(
        "시각화 레이아웃은 Lung `lung_pipeline_dashboard.html`(메트릭·표·강조 행) 및 "
        "`phase3_ensemble_analysis.py`(표·차트 스타일) 흐름을 참고했습니다."
    )

    rows = iter_step4_groupcv_rows(result_root)
    if not rows:
        st.warning("No groupcv JSON rows found (unexpected).")
    else:
        df_gc = pd.DataFrame(rows)
        df_gc["phase_short"] = df_gc["phase"].map(_phase_short)

        st.write("### GroupCV charts (Lung-style overview)")
        g1, g2 = st.columns(2)
        with g1:
            st.caption("Phase × family — max val Spearman ρ (GroupCV JSON)")
            agg = df_gc.groupby(["phase_short", "family"], as_index=False)["val_spearman_mean"].max()
            pivot_rho = agg.pivot(index="phase_short", columns="family", values="val_spearman_mean")
            order_idx = [x for x in ("2A", "2B", "2C") if x in pivot_rho.index]
            pivot_rho = pivot_rho.reindex(order_idx)
            st.bar_chart(pivot_rho)
        with g2:
            st.caption("Top-15 runs — val Spearman ρ (all families)")
            df_gc["label"] = (
                df_gc["family"].str.upper()
                + " · "
                + df_gc["phase_short"]
                + " · "
                + df_gc["model"].str.slice(0, 32)
            )
            top15 = df_gc.nlargest(15, "val_spearman_mean").sort_values("val_spearman_mean")
            st.bar_chart(top15.set_index("label")["val_spearman_mean"])

        st.markdown("---")
        st.write("### 최고 성능 요약 (Step 4 단일 모델)")
        best_overall = max(rows, key=lambda r: r["val_spearman_mean"])
        best_ml = max((r for r in rows if r["family"] == "ml"), key=lambda r: r["val_spearman_mean"])
        best_dl = max((r for r in rows if r["family"] == "dl"), key=lambda r: r["val_spearman_mean"])
        best_gr = max((r for r in rows if r["family"] == "graph"), key=lambda r: r["val_spearman_mean"])
        s1, s2, s3, s4 = st.columns(4)
        s1.metric(
            "Overall best",
            f"{best_overall['family'].upper()} · {best_overall['model']}",
            f"ρ={best_overall['val_spearman_mean']:.4f} ({_phase_short(best_overall['phase'])})",
        )
        s2.metric("Best ML", best_ml["model"], f"ρ={best_ml['val_spearman_mean']:.4f}")
        s3.metric("Best DL", best_dl["model"], f"ρ={best_dl['val_spearman_mean']:.4f}")
        s4.metric("Best Graph", best_gr["model"], f"ρ={best_gr['val_spearman_mean']:.4f}")

        st.info(
            "Step 5(앙상블) 최적화 설정: ML은 CatBoost 고정, Graph는 GraphSAGE 고정으로 두고 "
            "DL 후보를 상위 성능 기준으로 선택해 조합을 평가합니다. "
            "앙상블 블렌딩/가중치/결과표는 Step 5 탭에서 확인하세요."
        )

        st.markdown("---")
        st.write("### GroupCV tables (top runs per family)")

        def topn(family: str, n: int = 8) -> list[dict[str, Any]]:
            sub = [r for r in rows if r["family"] == family]
            return sorted(sub, key=lambda r: r["val_spearman_mean"], reverse=True)[:n]

        t_ml, t_dl, t_gr = st.tabs(["ML", "DL", "Graph"])
        with t_ml:
            st.dataframe(topn("ml"), use_container_width=True, hide_index=True)
        with t_dl:
            st.dataframe(topn("dl"), use_container_width=True, hide_index=True)
        with t_gr:
            st.dataframe(topn("graph"), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.write("### Overfitting (GroupCV)")
        warn_ct = sum(1 for r in rows if r["warning"])
        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("Rows with overfitting warning", f"{warn_ct} / {len(rows)}")
        worst = sorted(rows, key=lambda r: r["max_gap"], reverse=True)[:12]
        with c2:
            st.caption("Max train–val Spearman gap (higher = more fold-level overfit risk).")
            wdf = pd.DataFrame(worst)
            wdf["_lbl"] = wdf["family"].str.upper() + " · " + wdf["model"].str.slice(0, 22)
            st.bar_chart(wdf.set_index("_lbl")["max_gap"])
        st.dataframe(worst, use_container_width=True, hide_index=True)

def render_step_5() -> None:
    st.subheader("Step 5: Ensemble (STAD)")
    st.caption("Step 5는 CatBoost + DL + Graph OOF 블렌딩 결과를 독립적으로 보여줍니다.")

    result_root = PROJECT_ROOT / "results" / STEP4_RESULT_TAG
    ens_json = result_root / "ensemble_catboost_dl_graph_groupcv.json"
    _ens_raw = read_json(ens_json) if ens_json.exists() else None
    ens_data: dict[str, Any] | None = _ens_raw if isinstance(_ens_raw, dict) else None

    st.write("### Ensemble policy")
    st.markdown(
        "- **고정 슬롯:** ML=`CatBoost`, Graph=`GraphSAGE`\n"
        "- **탐색 슬롯:** DL은 Step 4 상위 성능 기준 후보(phase별 best) 사용\n"
        "- **블렌드 방식:** Simple / JSON Spearman 가중 / GridOpt"
    )

    if ens_data and ens_data.get("phases"):
        h = summarize_ensemble_headline(ens_data)
        e1, e2, e3, e4 = st.columns(4)
        e1.metric(
            "best GridOpt ρ",
            _fmt_num(h.get("best_grid")),
            f"phase {h.get('best_phase')}" if h.get("best_phase") else "",
        )
        e2.metric("mean GridOpt ρ (2A–2C)", _fmt_num(h.get("mean_grid")))
        e3.metric("mean Weighted ρ", _fmt_num(h.get("mean_weighted")))
        e4.metric("y rows (ensemble)", str(h.get("y_n") or "—"))
        try:
            st.download_button(
                label="앙상블 JSON 다운로드",
                data=ens_json.read_bytes(),
                file_name=ens_json.name,
                mime="application/json",
                key="stad_download_ensemble_groupcv",
            )
        except Exception:
            pass

    st.markdown("---")
    st.write("### OOF 앙상블 수치 (CatBoost + best DL + GraphSAGE)")
    st.code(
        "python scripts/run_ensemble_catboost_dl_graph_stad.py "
        f"--run-id {STEP4_RUN_ID} --result-tag {STEP4_RESULT_TAG} --eval-mode groupcv",
        language="bash",
    )
    ens = ens_data
    if ens is None:
        if ens_json.exists():
            st.error(f"앙상블 JSON은 있으나 읽기 실패: `{ens_json.relative_to(PROJECT_ROOT)}`")
        else:
            st.warning(f"아직 없음: `{ens_json.relative_to(PROJECT_ROOT)}` — 위 명령으로 생성.")
    else:
        st.caption(f"Source: `{ens_json.relative_to(PROJECT_ROOT)}`")
        mn = ens.get("metric_notes") or {}
        if isinstance(mn, dict) and mn.get("diversity_field"):
            with st.expander("‘diversity’ 지표가 무엇인지 (Lung 코드와 동일 정의)", expanded=False):
                st.markdown(str(mn.get("diversity_field")))
        st.caption(
            "**pred_pairwise_rho_mean**: 세 구성원 OOF *예측값* 쌍마다 Spearman ρ를 구한 뒤 평균. "
            "값이 **크면**(예: 0.65~0.73) 랭킹이 서로 **비슷**해서 보완적 다양성은 **낮음**. "
            "**complementarity_1_minus_rho** = 1−위 값으로, **클수록** 예측 패턴이 **덜 겹침**."
        )
        sum_df, comp_df, melt_df = _ensemble_payload_to_tables(ens)
        if "status" in sum_df.columns:
            ok_sum = sum_df[sum_df["status"] == "ok"].copy()
        else:
            ok_sum = sum_df.copy()

        st.write("#### 표 1 — 앙상블 요약 (phase × OOF·블렌드·gain·예측 유사도)")
        if not ok_sum.empty:
            hide_cols = {
                "status",
                "w_CatBoost",
                "w_DL",
                "w_Graph",
                "grid_w1",
                "grid_w2",
                "grid_w3",
            }
            display_cols = [c for c in ok_sum.columns if c not in hide_cols]
            st.dataframe(
                ok_sum[display_cols],
                use_container_width=True,
                hide_index=True,
            )
            st.markdown(_markdown_ensemble_table(ok_sum))
        else:
            st.dataframe(sum_df, use_container_width=True, hide_index=True)

        st.write("#### 표 2 — 선택된 모델·JSON GroupCV val ρ (가중치 산출 근거)")
        if not comp_df.empty:
            st.dataframe(comp_df, use_container_width=True, hide_index=True)

        st.write("#### 표 3 — 가중치 (JSON Spearman 가중 + 그리드 최적)")
        wt_rows: list[dict[str, Any]] = []
        for block in ens.get("phases") or []:
            if not isinstance(block, dict) or not block.get("ok"):
                continue
            ph = block.get("phase", "?")
            ensd = block.get("ensemble") or {}
            wj = ensd.get("weighted_json_weights")
            og = ensd.get("optimal_grid_weights") or [None, None, None]
            wt_rows.append(
                {
                    "phase": ph,
                    "json_w_CatBoost": wj[0] if isinstance(wj, list) and len(wj) > 0 else None,
                    "json_w_DL": wj[1] if isinstance(wj, list) and len(wj) > 1 else None,
                    "json_w_Graph": wj[2] if isinstance(wj, list) and len(wj) > 2 else None,
                    "grid_w1": og[0],
                    "grid_w2": og[1],
                    "grid_w3": og[2],
                }
            )
        if wt_rows:
            st.dataframe(pd.DataFrame(wt_rows), use_container_width=True, hide_index=True)

        st.write("#### 그래프 — phase별 Simple / Weighted / GridOpt Spearman")
        fig = _plotly_ensemble_grouped_bar(melt_df)
        if fig is not None:
            try:
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pv = melt_df.pivot(index="phase", columns="method", values="ρ")
                order_idx = [x for x in ("2A", "2B", "2C") if x in pv.index]
                st.bar_chart(pv.reindex(order_idx))
        else:
            pv = melt_df.pivot(index="phase", columns="method", values="ρ")
            order_idx = [x for x in ("2A", "2B", "2C") if x in pv.index]
            st.bar_chart(pv.reindex(order_idx))

        with st.expander("Raw ensemble JSON", expanded=False):
            st.json(ens)

    st.info(
        "OOF는 동일 `groupcv` 폴드에서 나온 예측만 혼합하세요. "
        "Lung `phase3_ensemble_analysis.py`와 같이 Simple·Weighted·gain·diversity를 함께 봅니다. "
        "Plotly가 설치되어 있으면 앙상블 막대 그래프가 `st.plotly_chart`로 표시됩니다 (`pip install plotly`). "
        "Graph는 transductive KNN edge 설정이므로 프로토콜 상 해석에 주의."
    )


def render_step_6() -> None:
    st.subheader("Step 6: External Validation")
    st.caption(
        "`STAD_reproduction_protocol.md` §4 · `run_step6_stad.sh`: PRISM, ClinicalTrials, COSMIC, CPTAC, GEO + 종합 스코어."
    )

    checks = [
        PROJECT_ROOT / "scripts/run_step6_stad.sh",
        PROJECT_ROOT / "results/stad_top30_phase2b_catboost_with_names.csv",
        PROJECT_ROOT / "results/stad_top30_phase2c_catboost_with_names.csv",
        PROJECT_ROOT / "results/stad_top30_unified_2b_and_2c_with_names.csv",
        PROJECT_ROOT / "results/stad_top30_drugs_ensemble.csv",
        PROJECT_ROOT / "results/stad_prism_validation_results.json",
        PROJECT_ROOT / "results/stad_clinical_trials_validation_results.json",
        PROJECT_ROOT / "results/stad_cosmic_validation_results.json",
        PROJECT_ROOT / "results/stad_cptac_validation_results.json",
        PROJECT_ROOT / "results/stad_geo_validation_results.json",
        PROJECT_ROOT / "results/stad_comprehensive_drug_scores.csv",
        PROJECT_ROOT / "results/stad_comprehensive_validation_results.json",
    ]
    for p in checks:
        st.write(f"- `{p.relative_to(PROJECT_ROOT)}`: **{file_status(p)}**")

    comp = PROJECT_ROOT / "results" / "stad_comprehensive_drug_scores.csv"
    if comp.exists():
        st.markdown("---")
        st.write("### 종합 스코어 미리보기 (상위 10)")
        try:
            cdf = pd.read_csv(comp)
            st.dataframe(cdf.head(10), use_container_width=True, hide_index=True)
        except Exception as exc:
            st.warning(f"CSV read failed: {exc}")


def render_step_7() -> None:
    _exec_stad_view("step7_stad.py")


def render_step_8() -> None:
    _exec_stad_view("step8_stad.py")


def render_step_9() -> None:
    _exec_stad_view("step9_stad.py")


def render_protocol() -> None:
    st.subheader("Protocol Viewer")
    st.caption("Quick links to STAD protocol documents")

    docs = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "STAD_reproduction_protocol.md",
        PROJECT_ROOT / "configs/CONTEXT.md",
    ]
    for d in docs:
        st.write(f"- `{d.relative_to(PROJECT_ROOT)}`: **{file_status(d)}**")

    protocol_path = PROJECT_ROOT / "STAD_reproduction_protocol.md"
    if protocol_path.exists():
        content = protocol_path.read_text(encoding="utf-8", errors="replace")
        with st.expander("Preview: STAD_reproduction_protocol.md", expanded=False):
            st.text(content[:5000])


def main() -> None:
    st.set_page_config(
        page_title="STAD Dashboard",
        page_icon="🍽️",
        layout="wide",
    )

    render_header()

    page = render_sidebar_nav()

    if page == "Overview":
        render_overview()
    elif page == "Step 0-1":
        render_step_0_1()
    elif page == "Step 2":
        render_step_2()
    elif page == "Step 3":
        render_step_3()
    elif page == "Step 3.5":
        render_step_3_5()
    elif page == "Step 4":
        render_step_4()
    elif page == "Step 5":
        render_step_5()
    elif page == "Step 6":
        render_step_6()
    elif page == "Step 7":
        render_step_7()
    elif page == "Step 8":
        render_step_8()
    elif page == "Step 9":
        render_step_9()
    elif page == "Protocol":
        render_protocol()
    else:
        st.warning(f"알 수 없는 페이지: {page!r} — Overview로 돌아가 사이드바를 확인하세요.")
        render_overview()


if __name__ == "__main__":
    main()
