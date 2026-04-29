#!/usr/bin/env bash
# STAD Step 8–9 (초안): Colon `20260420_colon_protocol.md` Step 8·9 와 동일 순서.
#
# Step 8:
#   1) 로컬 KG JSON (Neo4j 없이 뷰어용)
#   2) HTML 뷰어
#   3) Neo4j 적재 — NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD 없으면 스킵 요약만 기록
#
# Step 9:
#   4) Ollama LLM 근거 — ollama 없으면 ERROR 문자열이 들어간 JSON/MD 만 생성
#
# Usage:
#   ./scripts/run_step8_9_stad.sh
#   SKIP_NEO4J=1 ./scripts/run_step8_9_stad.sh   # 8-3 Neo4j 생략(기본과 동일: env 없으면 자동 스킵)
#   SKIP_LLM=1 ./scripts/run_step8_9_stad.sh   # Step 9 생략
#
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"

echo "== STAD Step 8a: export KG JSON =="
"$PY" scripts/step8_export_kg_json_stad.py --project-root "$ROOT"

echo "== STAD Step 8b: KG HTML viewer =="
"$PY" scripts/step8_generate_kg_viewer_stad.py

if [[ "${SKIP_NEO4J:-0}" != "1" ]]; then
  echo "== STAD Step 8c: Neo4j load (needs NEO4J_* env) =="
  "$PY" scripts/step8_neo4j_load_stad.py --project-root "$ROOT"
else
  echo "== SKIP Neo4j (SKIP_NEO4J=1) =="
fi

if [[ "${SKIP_LLM:-0}" != "1" ]]; then
  echo "== STAD Step 9: LLM explanations =="
  LLM_ARGS=(--project-root "$ROOT")
  if [[ "${STAD_LLM_DRY_RUN:-0}" == "1" ]]; then
    LLM_ARGS+=(--dry-run)
  fi
  "$PY" scripts/step9_llm_explanation_stad.py "${LLM_ARGS[@]}"
else
  echo "== SKIP Step 9 (SKIP_LLM=1) =="
fi

echo "== STAD Step 8–9 스크립트 완료 =="
