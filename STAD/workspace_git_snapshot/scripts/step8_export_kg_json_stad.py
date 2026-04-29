#!/usr/bin/env python3
"""
Step 8 (STAD) 보조: Neo4j 없이 로컬 JSON만 만들어 `step8_generate_kg_viewer_stad.py` 입력으로 사용.

Colon 저장소의 `knowledge_graph_data.json` 과 호환되는 최소 스키마:
  - nodes: id, label, type in {disease, drug, target}, category(약물), uniprot/plddt(선택)
  - edges: source, target, type in {treats, predicted_for, targets, associated_with}

입력:
  - results/stad_comprehensive_drug_scores.csv
  - results/stad_final_top15.csv (usage_category·ADMET·3단계 병합)
  - results/stad_alphafold_validation/stad_alphafold_validation_results.json (선택)

출력:
  - results/stad_knowledge_graph_data.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


DISEASE_ID = "disease_Gastric Cancer"
DISEASE_LABEL = "Gastric Cancer"


def _slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", str(s)).strip("_").lower()[:80]


_SKIP = {"DNA", "RNA", "BROAD", "KINASE", "INHIBITOR", "MICROTUBULE", "DESTABILISER", "SPECTRUM"}


def _genes_from_target(s: str) -> list[str]:
    out: list[str] = []
    for t in re.split(r"[,;/]", str(s).replace(" /// ", ",")):
        t = t.strip().upper()
        if len(t) < 2 or " " in t or t in _SKIP:
            continue
        if re.match(r"^[A-Z0-9][A-Z0-9_-]{0,14}$", t):
            out.append(t)
    return list(dict.fromkeys(out))[:24]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    root = args.project_root.resolve()
    rd = root / "results"

    comp_path = rd / "stad_comprehensive_drug_scores.csv"
    top_path = rd / "stad_final_top15.csv"
    if not comp_path.exists():
        print(f"ERROR: missing {comp_path}")
        return 1

    comp = pd.read_csv(comp_path)
    top = pd.read_csv(top_path) if top_path.exists() else None

    cat_by_drug: dict[str, str] = {}
    stage_by_drug: dict[str, int] = {}
    safety_by_drug: dict[str, float] = {}
    if top is not None:
        nc = "drug_name" if "drug_name" in top.columns else "DRUG_NAME"
        for _, r in top.iterrows():
            dn = str(r[nc])
            cat_by_drug[dn] = str(r.get("usage_category", ""))
            if "recommendation_stage" in top.columns:
                try:
                    stage_by_drug[dn] = int(r["recommendation_stage"])
                except Exception:
                    pass
            if "safety_score" in top.columns:
                try:
                    safety_by_drug[dn] = float(r["safety_score"])
                except Exception:
                    pass

    af_map: dict[str, dict] = {}
    af_path = rd / "stad_alphafold_validation" / "stad_alphafold_validation_results.json"
    if af_path.exists():
        data = json.loads(af_path.read_text(encoding="utf-8"))
        for s in data.get("structures", []):
            g = str(s.get("gene", ""))
            if g:
                af_map[g] = s

    nodes: list[dict] = []
    edges: list[dict] = []

    nodes.append(
        {
            "id": DISEASE_ID,
            "label": DISEASE_LABEL,
            "type": "disease",
        }
    )

    drug_ids: dict[str, str] = {}
    for _, row in comp.iterrows():
        name = str(row["drug_name"])
        did = f"drug_{_slug(name)}"
        drug_ids[name] = did
        cat = cat_by_drug.get(name, "REPURPOSING_CANDIDATE")
        nodes.append(
            {
                "id": did,
                "label": name,
                "type": "drug",
                "category": cat,
                "safety_score": safety_by_drug.get(name, ""),
                "stage": stage_by_drug.get(name, ""),
            }
        )
        edges.append({"source": did, "target": DISEASE_ID, "type": "predicted_for"})

        tgt = str(row.get("target", "") or "")
        for gene in _genes_from_target(tgt):
            tid = f"target_{_slug(gene)}"
            if not any(n["id"] == tid for n in nodes):
                extra: dict = {"id": tid, "label": gene, "type": "target"}
                if gene in af_map:
                    st = af_map[gene]
                    extra["uniprot"] = st.get("uniprot_id", "")
                    plddt = st.get("plddt") or {}
                    extra["plddt"] = plddt.get("mean", "")
                    pk = st.get("pocket") or {}
                    extra["pocket"] = pk.get("n_residues", "")
                nodes.append(extra)
            edges.append({"source": did, "target": tid, "type": "targets"})

    out_path = rd / "stad_knowledge_graph_data.json"
    out_path.write_text(json.dumps({"nodes": nodes, "edges": edges}, indent=2), encoding="utf-8")
    print(f"✅ Wrote {out_path} ({len(nodes)} nodes, {len(edges)} edges)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
