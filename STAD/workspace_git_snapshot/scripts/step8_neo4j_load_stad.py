#!/usr/bin/env python3
"""
Step 8 (STAD): Neo4j Knowledge Graph 적재 — Colon `step8_neo4j_load.py` 초안 이식.

- 질병 노드: Gastric Cancer (TCGA-STAD) — 이름은 환경변수 `STAD_NEO4J_DISEASE_NAME` 로 덮어쓸 수 있음 (기본 `Gastric Cancer`).
- CellLine: `data/labels.parquet` 의 sample_id, 위암 축 메타.
- Drug–Disease: `results/stad_comprehensive_drug_scores.csv` 기반 PREDICTED_FOR (+ Drug 노드 MERGE).
- ADMET / AlphaFold / 서브타입: STAD Step7 산출물 경로.

Neo4j 연결 (Colon과 동일하게 Aura 등 — **비밀번호는 코드에 넣지 말 것**):

  export NEO4J_URI="neo4j+s://....databases.neo4j.io"
  export NEO4J_USER="neo4j"
  export NEO4J_PASSWORD="...."

자격 증명이 없으면 **DB 쓰기 없이** `results/stad_neo4j_load_summary.json` 만 `status=skipped` 로 저장하고 종료.

출력:
  - results/stad_neo4j_load_summary.json
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd


def _neo4j_config() -> tuple[str, str, str] | None:
    uri = os.environ.get("NEO4J_URI", "").strip()
    user = os.environ.get("NEO4J_USER", "").strip()
    password = os.environ.get("NEO4J_PASSWORD", "").strip()
    if not (uri and user and password):
        return None
    return uri, user, password


def get_driver():
    from neo4j import GraphDatabase

    cfg = _neo4j_config()
    if not cfg:
        raise RuntimeError("Neo4j env missing")
    uri, user, password = cfg
    return GraphDatabase.driver(uri, auth=(user, password))


def create_disease_node(session, disease_name: str) -> None:
    session.run(
        """
        MERGE (d:Disease {name: $name})
        SET d.acronym = 'STAD',
            d.subtypes = ['TCGA-STAD'],
            d.description = 'Gastric cancer (TCGA-STAD repurposing pipeline)',
            d.tcga_code = 'STAD',
            d.pipeline_version = 'stad_v0',
            d.updated_at = datetime()
        RETURN d.name AS name
        """,
        name=disease_name,
    )
    print(f"  ✅ Disease: {disease_name}")


def create_cell_line_nodes(session, base_dir: Path, disease_name: str) -> int:
    labels_path = base_dir / "data" / "labels.parquet"
    if not labels_path.exists():
        print(f"  ⚠️ Skip CellLine: missing {labels_path}")
        return 0
    labels = pd.read_parquet(labels_path)
    col = "sample_id" if "sample_id" in labels.columns else labels.columns[0]
    cell_lines = sorted(labels[col].astype(str).unique())
    count = 0
    for cl in cell_lines:
        session.run(
            """
            MERGE (c:CellLine {name: $name})
            SET c.tissue = 'stomach',
                c.cancer_type = 'STAD'
            WITH c
            MATCH (d:Disease {name: $disease})
            MERGE (c)-[:CELL_LINE_OF]->(d)
            """,
            name=str(cl),
            disease=disease_name,
        )
        count += 1
    print(f"  ✅ CellLine: {count} nodes")
    return count


def create_drug_disease_relationships(session, results_dir: Path, disease_name: str) -> int:
    comp = pd.read_csv(results_dir / "stad_comprehensive_drug_scores.csv")
    count = 0
    for _, row in comp.iterrows():
        drug_name = str(row["drug_name"])
        session.run(
            """
            MERGE (drug:Drug {name: $drug_name})
            WITH drug
            MATCH (disease:Disease {name: $disease})
            MERGE (drug)-[r:PREDICTED_FOR]->(disease)
            SET r.rank = $rank,
                r.pred_ic50 = $pred_ic50,
                r.validation_count = $val_count,
                r.confidence = $confidence,
                r.prism = $prism,
                r.clinical_trials = $ct,
                r.cosmic = $cosmic,
                r.cptac = $cptac,
                r.geo = $geo,
                r.pipeline = 'stad_v0',
                r.updated_at = datetime()
            """,
            drug_name=drug_name,
            disease=disease_name,
            rank=int(row["rank"]),
            pred_ic50=float(row.get("pred_ic50_mean", 0)),
            val_count=int(row.get("validation_count", 0)),
            confidence=str(row.get("confidence", "")),
            prism=int(row.get("prism", 0)),
            ct=int(row.get("clinical_trials", 0)),
            cosmic=int(row.get("cosmic", 0)),
            cptac=int(row.get("cptac", 0)),
            geo=int(row.get("geo", 0)),
        )
        count += 1
    print(f"  ✅ PREDICTED_FOR: {count}")
    return count


def add_admet_top15(session, results_dir: Path, disease_name: str) -> int:
    p = results_dir / "stad_final_top15.csv"
    if not p.exists():
        print("  ⚠️ Skip ADMET: stad_final_top15.csv missing")
        return 0
    top15 = pd.read_csv(p)
    name_col = "drug_name" if "drug_name" in top15.columns else "DRUG_NAME"
    cat_col = "usage_category" if "usage_category" in top15.columns else "category"
    count = 0
    for _, row in top15.iterrows():
        drug_name = str(row[name_col])
        cat = str(row.get(cat_col, row.get("category", "")))
        session.run(
            """
            MATCH (drug:Drug {name: $drug_name})
            MATCH (drug)-[r:PREDICTED_FOR]->(d:Disease {name: $disease})
            SET r.admet_safety_score = $safety,
                r.admet_verdict = $verdict,
                r.category = $category,
                r.recommendation_rank = $rec_rank,
                r.recommendation_stage = $stage,
                r.is_top15 = true
            """,
            drug_name=drug_name,
            disease=disease_name,
            safety=float(row.get("safety_score", 0)),
            verdict=str(row.get("verdict", "")),
            category=cat,
            rec_rank=int(row.get("recommendation_rank", row.get("rank", 0))),
            stage=int(row.get("recommendation_stage", 0)) if pd.notna(row.get("recommendation_stage")) else 0,
        )
        count += 1
    print(f"  ✅ ADMET Top15: {count}")
    return count


def add_alphafold(session, results_dir: Path, disease_name: str) -> int:
    af_path = results_dir / "stad_alphafold_validation" / "stad_alphafold_validation_results.json"
    if not af_path.exists():
        print("  ⚠️ AlphaFold JSON missing")
        return 0
    data = json.loads(af_path.read_text(encoding="utf-8"))
    count = 0
    for structure in data.get("structures", []):
        gene = structure["gene"]
        uniprot = structure["uniprot_id"]
        plddt = structure.get("plddt", {})
        pocket = structure.get("pocket", {})
        drugs = structure.get("drugs", [])
        session.run(
            """
            MERGE (t:Target {name: $gene})
            SET t.uniprot_id = $uniprot,
                t.alphafold_plddt = $plddt_mean,
                t.alphafold_confidence = CASE WHEN $plddt_mean >= 70 THEN 'high' ELSE 'low' END,
                t.pocket_size = $pocket_size,
                t.pocket_volume = $pocket_volume,
                t.pocket_confidence = $pocket_conf
            """,
            gene=gene,
            uniprot=uniprot,
            plddt_mean=float(plddt.get("mean", 0)) if plddt else 0.0,
            pocket_size=int(pocket.get("n_residues", 0)) if pocket else 0,
            pocket_volume=float(pocket.get("volume", 0)) if pocket else 0.0,
            pocket_conf=float(pocket.get("confidence", 0)) if pocket else 0.0,
        )
        for drug_name in drugs:
            session.run(
                """
                MERGE (drug:Drug {name: $drug_name})
                WITH drug
                MATCH (t:Target {name: $gene})
                MERGE (drug)-[r:TARGETS]->(t)
                SET r.disease_axis = 'STAD',
                    r.alphafold_validated = true
                """,
                drug_name=drug_name,
                gene=gene,
            )
        count += 1
    print(f"  ✅ AlphaFold structures: {count}")
    return count


def add_subtype_context(session, results_dir: Path, disease_name: str) -> int:
    p = results_dir / "stad_subtype_drug_context.csv"
    if not p.exists():
        print("  ⚠️ stad_subtype_drug_context.csv missing")
        return 0
    recs = pd.read_csv(p)
    count = 0
    drug_col = "drug" if "drug" in recs.columns else recs.columns[0]
    ctx_col = "context_label" if "context_label" in recs.columns else "recommendation"
    det_col = "detail" if "detail" in recs.columns else recs.columns[-1]
    for _, row in recs.iterrows():
        drug_name = str(row[drug_col])
        ctx = str(row.get(ctx_col, ""))
        detail = str(row.get(det_col, ""))
        session.run(
            """
            MATCH (drug:Drug {name: $drug_name})
            MATCH (drug)-[r:PREDICTED_FOR]->(d:Disease {name: $disease})
            SET r.stad_subtype_context = $ctx,
                r.stad_subtype_detail = $detail
            """,
            drug_name=drug_name,
            disease=disease_name,
            ctx=ctx,
            detail=detail[:2000],
        )
        count += 1
    print(f"  ✅ Subtype context: {count}")
    return count


def write_skip_summary(results_dir: Path, disease_name: str, reason: str) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    p = results_dir / "stad_neo4j_load_summary.json"
    p.write_text(
        json.dumps(
            {
                "step": "Step 8 Neo4j (STAD)",
                "status": "skipped",
                "reason": reason,
                "disease": disease_name,
                "env_required": ["NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  ✅ {p} (skipped)")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    base_dir = args.project_root.resolve()
    results_dir = base_dir / "results"
    disease_name = os.environ.get("STAD_NEO4J_DISEASE_NAME", "Gastric Cancer").strip() or "Gastric Cancer"

    print("=" * 80)
    print("Step 8 (STAD): Neo4j Knowledge Graph load (draft)")
    print("=" * 80)

    cfg = _neo4j_config()
    if not cfg:
        print("\n⚠️ NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD not set — skipping remote load.")
        write_skip_summary(results_dir, disease_name, "missing_neo4j_credentials")
        return 0

    comp = results_dir / "stad_comprehensive_drug_scores.csv"
    if not comp.exists():
        print(f"ERROR: missing {comp}")
        return 1

    driver = get_driver()
    try:
        with driver.session() as session:
            print("\n[1] Disease")
            create_disease_node(session, disease_name)
            print("\n[2] CellLine")
            create_cell_line_nodes(session, base_dir, disease_name)
            print("\n[3] Drug–Disease")
            n_pf = create_drug_disease_relationships(session, results_dir, disease_name)
            print("\n[4] ADMET Top15")
            add_admet_top15(session, results_dir, disease_name)
            print("\n[5] AlphaFold")
            add_alphafold(session, results_dir, disease_name)
            print("\n[6] Subtype context")
            add_subtype_context(session, results_dir, disease_name)
    finally:
        driver.close()

    summary = {
        "step": "Step 8 Neo4j (STAD)",
        "status": "applied",
        "neo4j_uri_host": cfg[0].split("://")[-1].split("/")[0][:48],
        "disease": disease_name,
    }
    out = results_dir / "stad_neo4j_load_summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n  ✅ {out}")
    print("\n✅ Step 8 (STAD) Neo4j 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
