#!/usr/bin/env python3
"""
Step 8 (STAD): Knowledge Graph 인터랙티브 뷰어 생성 — Colon `step8_generate_kg_viewer.py` 이식.

입력:
  - results/stad_knowledge_graph_data.json (`step8_export_kg_json_stad.py` 로 생성)

출력:
  - results/stad_knowledge_graph_viewer.html
"""

import json
from pathlib import Path


def generate_kg_viewer(data_path, output_path=None):
    """순수 Canvas JS 기반 Knowledge Graph 뷰어 (CDN 불필요).

    Returns the HTML string. If ``output_path`` is set, writes that file (UTF-8).
    """
    data_path = Path(data_path)
    with data_path.open(encoding="utf-8") as f:
        graph = json.load(f)

    nodes = graph["nodes"]
    edges = graph["edges"]

    # 통계
    stats = {}
    for t in ["disease", "drug", "target", "pathway"]:
        stats[t] = len([n for n in nodes if n["type"] == t])
    stats["edges"] = len(edges)

    # 공유 약물
    disease_drugs = {}
    for e in edges:
        if e["type"] in ["treats", "predicted_for"]:
            disease_name = next((n["label"] for n in nodes if n["id"] == e["target"]), "?")
            drug_name = next((n["label"] for n in nodes if n["id"] == e["source"]), "?")
            if disease_name not in disease_drugs:
                disease_drugs[disease_name] = []
            disease_drugs[disease_name].append(drug_name)

    all_drug_names = set()
    for drugs in disease_drugs.values():
        all_drug_names.update(drugs)
    shared = []
    for drug in all_drug_names:
        in_diseases = [d for d, drugs in disease_drugs.items() if drug in drugs]
        if len(in_diseases) > 1:
            shared.append({"drug": drug, "diseases": in_diseases})

    shared_rows = ""
    for s in sorted(shared, key=lambda x: len(x["diseases"]), reverse=True):
        shared_rows += f'<tr><td>{s["drug"]}</td><td>{", ".join(s["diseases"])}</td></tr>\n'

    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Knowledge Graph — STAD / Gastric Cancer</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI',Arial,sans-serif; background:#0a0a1a; color:#e0e0e0; overflow:hidden; }}
.header {{ background:linear-gradient(135deg,#1a1a2e,#16213e); padding:15px 25px; border-bottom:2px solid #e74c3c; display:flex; justify-content:space-between; align-items:center; }}
.header h1 {{ color:#fff; font-size:20px; }}
.header-stats {{ display:flex; gap:15px; }}
.header-stat {{ text-align:center; }}
.header-stat .val {{ font-size:18px; font-weight:bold; }}
.header-stat .lbl {{ font-size:10px; color:#7f8c8d; }}
.main {{ display:flex; height:calc(100vh - 60px); }}
.sidebar {{ width:280px; background:#1a1a2e; padding:15px; overflow-y:auto; border-right:1px solid #2c3e50; }}
.canvas-wrap {{ flex:1; position:relative; }}
canvas {{ display:block; }}
.section {{ margin-bottom:15px; padding:12px; background:#16213e; border-radius:6px; border:1px solid #2c3e50; }}
.section h3 {{ color:#3498db; font-size:12px; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px; }}
select,input {{ width:100%; padding:6px; margin:3px 0; background:#0a0a1a; color:#e0e0e0; border:1px solid #2c3e50; border-radius:3px; font-size:12px; }}
button {{ padding:6px 12px; margin:2px; background:#3498db; color:white; border:none; border-radius:3px; cursor:pointer; font-size:11px; }}
button:hover {{ background:#2980b9; }}
.legend-item {{ display:flex; align-items:center; gap:6px; margin:3px 0; font-size:11px; }}
.dot {{ width:12px; height:12px; border-radius:50%; }}
.diamond {{ width:10px; height:10px; transform:rotate(45deg); }}
.tri {{ width:0; height:0; border-left:6px solid transparent; border-right:6px solid transparent; border-bottom:12px solid; }}
table {{ width:100%; border-collapse:collapse; font-size:11px; margin-top:5px; }}
th {{ background:#2c3e50; padding:4px; text-align:left; }}
td {{ padding:4px; border-bottom:1px solid #2c3e50; }}
#detail {{ margin-top:10px; padding:10px; background:#16213e; border-radius:6px; border:1px solid #f39c12; display:none; }}
#detail h4 {{ color:#f39c12; margin-bottom:5px; font-size:13px; }}
#detail p {{ font-size:11px; margin:2px 0; }}
.edge-line {{ display:inline-block; width:16px; height:3px; vertical-align:middle; margin-right:5px; }}
</style>
</head>
<body>
<div class="header">
  <h1>🔬 STAD Drug Repurposing Knowledge Graph</h1>
  <div class="header-stats">
    <div class="header-stat"><div class="val" style="color:#e74c3c">{stats.get('disease',0)}</div><div class="lbl">Diseases</div></div>
    <div class="header-stat"><div class="val" style="color:#3498db">{stats.get('drug',0)}</div><div class="lbl">Drugs</div></div>
    <div class="header-stat"><div class="val" style="color:#2ecc71">{stats.get('target',0)}</div><div class="lbl">Targets</div></div>
    <div class="header-stat"><div class="val" style="color:#fff">{stats.get('edges',0)}</div><div class="lbl">Edges</div></div>
  </div>
</div>
<div class="main">
  <div class="sidebar">
    <div class="section">
      <h3>Controls</h3>
      <select id="diseaseFilter" onchange="filterDisease()">
        <option value="all">All Diseases</option>
        <option value="Gastric Cancer">Gastric Cancer (TCGA-STAD)</option>
        <option value="Breast Cancer">Breast Cancer</option>
        <option value="Lung Cancer">Lung Cancer</option>
        <option value="Colorectal Cancer">Colorectal Cancer</option>
      </select>
      <input id="search" placeholder="Search node..." oninput="searchNode()">
      <button onclick="resetView()">Reset</button>
      <button onclick="toggleLabels()">Labels</button>
    </div>
    <div class="section">
      <h3>Node Types</h3>
      <div class="legend-item"><div class="diamond" style="background:#e74c3c"></div> Disease</div>
      <div class="legend-item"><div class="dot" style="background:#f39c12"></div> Drug (Repurposing)</div>
      <div class="legend-item"><div class="dot" style="background:#e74c3c"></div> Drug (FDA Approved)</div>
      <div class="legend-item"><div class="dot" style="background:#1abc9c"></div> Drug (Clinical Trial)</div>
      <div class="legend-item"><div class="dot" style="background:#3498db"></div> Drug (Research)</div>
      <div class="legend-item"><div class="tri" style="border-bottom-color:#2ecc71"></div> Target</div>
    </div>
    <div class="section">
      <h3>Edge Types</h3>
      <div class="legend-item"><span class="edge-line" style="background:#e74c3c"></span> TREATS</div>
      <div class="legend-item"><span class="edge-line" style="background:#f39c12"></span> PREDICTED_FOR</div>
      <div class="legend-item"><span class="edge-line" style="background:#2ecc71"></span> TARGETS</div>
      <div class="legend-item"><span class="edge-line" style="background:#95a5a6"></span> ASSOCIATED_WITH</div>
    </div>
    <div class="section">
      <h3>Cross-Disease Drugs ({len(shared)})</h3>
      <table><tr><th>Drug</th><th>Diseases</th></tr>{shared_rows}</table>
    </div>
    <div id="detail">
      <h4 id="detailTitle"></h4>
      <div id="detailContent"></div>
    </div>
  </div>
  <div class="canvas-wrap">
    <canvas id="canvas"></canvas>
  </div>
</div>
<script>
var rawNodes = {nodes_json};
var rawEdges = {edges_json};

var typeColors = {{
  disease: '#e74c3c',
  drug: '#3498db',
  target: '#2ecc71',
  pathway: '#9b59b6'
}};
var drugColors = {{
  'FDA_APPROVED_CRC': '#e74c3c',
  'FDA_APPROVED_GASTRIC': '#e74c3c',
  'REPURPOSING_CANDIDATE': '#f39c12',
  'CLINICAL_TRIAL': '#1abc9c',
  'RESEARCH_PHASE': '#3498db',
  'RESEARCH_PHASE_GASTRIC': '#3498db'
}};
var edgeColors = {{
  treats: '#e74c3c',
  predicted_for: '#f39c12',
  targets: '#2ecc71',
  associated_with: '#556677',
  in_pathway: '#9b59b6'
}};
var typeSizes = {{ disease:22, drug:10, target:8, pathway:6 }};

var canvas, ctx, W, H;
var graphNodes = [], graphEdges = [];
var showLabels = true;
var dragging = null, dragOff = {{x:0,y:0}};
var panX = 0, panY = 0, zoom = 1;
var lastMouse = null;
var selectedNode = null;
var filterDiseaseName = 'all';
var searchQuery = '';

function init() {{
  canvas = document.getElementById('canvas');
  ctx = canvas.getContext('2d');
  resize();
  window.addEventListener('resize', resize);
  canvas.addEventListener('mousedown', onDown);
  canvas.addEventListener('mousemove', onMove);
  canvas.addEventListener('mouseup', onUp);
  canvas.addEventListener('wheel', onWheel);
  canvas.addEventListener('dblclick', onDblClick);
  buildGraph();
  simulate();
}}

function resize() {{
  var wrap = canvas.parentElement;
  W = wrap.clientWidth; H = wrap.clientHeight;
  canvas.width = W; canvas.height = H;
}}

function buildGraph() {{
  graphNodes = [];
  graphEdges = [];
  var nodeMap = {{}};

  rawNodes.forEach(function(n) {{
    var color = typeColors[n.type] || '#888';
    if (n.type === 'drug' && n.category) color = drugColors[n.category] || color;
    var gn = {{
      id: n.id, label: n.label, type: n.type,
      x: W/2 + (Math.random()-0.5)*W*0.6,
      y: H/2 + (Math.random()-0.5)*H*0.6,
      vx: 0, vy: 0,
      r: typeSizes[n.type] || 8,
      color: color,
      category: n.category || '',
      uniprot: n.uniprot || '',
      plddt: n.plddt || '',
      pocket: n.pocket || '',
      safety_score: n.safety_score || '',
      visible: true, highlight: false
    }};
    graphNodes.push(gn);
    nodeMap[n.id] = gn;
  }});

  rawEdges.forEach(function(e) {{
    var src = nodeMap[e.source], tgt = nodeMap[e.target];
    if (src && tgt) {{
      graphEdges.push({{
        source: src, target: tgt,
        type: e.type,
        color: edgeColors[e.type] || '#444'
      }});
    }}
  }});

  applyFilter();
}}

function applyFilter() {{
  if (filterDiseaseName === 'all' && !searchQuery) {{
    graphNodes.forEach(function(n) {{ n.visible = true; n.highlight = false; }});
    return;
  }}

  if (searchQuery) {{
    graphNodes.forEach(function(n) {{
      n.visible = true;
      n.highlight = n.label.toLowerCase().includes(searchQuery);
    }});
    return;
  }}

  var diseaseId = 'disease_' + filterDiseaseName;
  var visible = new Set();
  visible.add(diseaseId);

  graphEdges.forEach(function(e) {{
    if (e.source.id === diseaseId || e.target.id === diseaseId) {{
      visible.add(e.source.id);
      visible.add(e.target.id);
    }}
  }});
  graphEdges.forEach(function(e) {{
    if (visible.has(e.source.id) && e.type === 'targets') {{
      visible.add(e.target.id);
    }}
  }});

  graphNodes.forEach(function(n) {{
    n.visible = visible.has(n.id);
    n.highlight = false;
  }});
}}

function simulate() {{
  for (var iter = 0; iter < 2; iter++) {{
    // repulsion
    for (var i = 0; i < graphNodes.length; i++) {{
      if (!graphNodes[i].visible) continue;
      for (var j = i+1; j < graphNodes.length; j++) {{
        if (!graphNodes[j].visible) continue;
        var dx = graphNodes[j].x - graphNodes[i].x;
        var dy = graphNodes[j].y - graphNodes[i].y;
        var d = Math.sqrt(dx*dx + dy*dy) || 1;
        var f = 800 / (d * d);
        graphNodes[i].vx -= dx/d * f;
        graphNodes[i].vy -= dy/d * f;
        graphNodes[j].vx += dx/d * f;
        graphNodes[j].vy += dy/d * f;
      }}
    }}
    // attraction (edges)
    graphEdges.forEach(function(e) {{
      if (!e.source.visible || !e.target.visible) return;
      var dx = e.target.x - e.source.x;
      var dy = e.target.y - e.source.y;
      var d = Math.sqrt(dx*dx + dy*dy) || 1;
      var f = (d - 100) * 0.005;
      e.source.vx += dx/d * f;
      e.source.vy += dy/d * f;
      e.target.vx -= dx/d * f;
      e.target.vy -= dy/d * f;
    }});
    // center gravity
    graphNodes.forEach(function(n) {{
      if (!n.visible) return;
      n.vx += (W/2 - n.x) * 0.001;
      n.vy += (H/2 - n.y) * 0.001;
      n.vx *= 0.9; n.vy *= 0.9;
      if (n !== dragging) {{
        n.x += n.vx;
        n.y += n.vy;
      }}
    }});
  }}
  draw();
  requestAnimationFrame(simulate);
}}

function draw() {{
  ctx.clearRect(0,0,W,H);
  ctx.save();
  ctx.translate(panX, panY);
  ctx.scale(zoom, zoom);

  // edges
  graphEdges.forEach(function(e) {{
    if (!e.source.visible || !e.target.visible) return;
    ctx.beginPath();
    ctx.moveTo(e.source.x, e.source.y);
    ctx.lineTo(e.target.x, e.target.y);
    ctx.strokeStyle = e.color;
    ctx.globalAlpha = 0.4;
    ctx.lineWidth = e.type === 'treats' ? 2 : 1;
    if (e.type === 'predicted_for') ctx.setLineDash([4,4]); else ctx.setLineDash([]);
    ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.setLineDash([]);
  }});

  // nodes
  graphNodes.forEach(function(n) {{
    if (!n.visible) return;
    var alpha = (searchQuery && !n.highlight) ? 0.15 : 1;
    ctx.globalAlpha = alpha;

    ctx.beginPath();
    if (n.type === 'disease') {{
      // diamond
      ctx.save();
      ctx.translate(n.x, n.y);
      ctx.rotate(Math.PI/4);
      ctx.fillStyle = n.color;
      ctx.fillRect(-n.r/1.4, -n.r/1.4, n.r*1.4, n.r*1.4);
      ctx.restore();
    }} else if (n.type === 'target') {{
      // triangle
      ctx.beginPath();
      ctx.moveTo(n.x, n.y - n.r);
      ctx.lineTo(n.x - n.r, n.y + n.r);
      ctx.lineTo(n.x + n.r, n.y + n.r);
      ctx.closePath();
      ctx.fillStyle = n.color;
      ctx.fill();
    }} else {{
      ctx.arc(n.x, n.y, n.r, 0, Math.PI*2);
      ctx.fillStyle = n.color;
      ctx.fill();
    }}

    // selected ring
    if (n === selectedNode) {{
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r + 4, 0, Math.PI*2);
      ctx.strokeStyle = '#f1c40f';
      ctx.lineWidth = 3;
      ctx.stroke();
    }}

    // label
    if (showLabels || n.type === 'disease' || n === selectedNode) {{
      ctx.fillStyle = '#ccc';
      ctx.font = (n.type === 'disease' ? 'bold 14px' : '10px') + ' Arial';
      ctx.textAlign = 'center';
      ctx.fillText(n.label, n.x, n.y + n.r + 14);
    }}
    ctx.globalAlpha = 1;
  }});
  ctx.restore();
}}

function getNodeAt(mx, my) {{
  var x = (mx - panX) / zoom, y = (my - panY) / zoom;
  for (var i = graphNodes.length-1; i >= 0; i--) {{
    var n = graphNodes[i];
    if (!n.visible) continue;
    var d = Math.sqrt((x-n.x)*(x-n.x) + (y-n.y)*(y-n.y));
    if (d < n.r + 5) return n;
  }}
  return null;
}}

function onDown(e) {{
  var n = getNodeAt(e.offsetX, e.offsetY);
  if (n) {{
    dragging = n;
    dragOff.x = (e.offsetX - panX)/zoom - n.x;
    dragOff.y = (e.offsetY - panY)/zoom - n.y;
    selectedNode = n;
    showDetail(n);
  }} else {{
    lastMouse = {{x: e.offsetX, y: e.offsetY}};
    selectedNode = null;
    document.getElementById('detail').style.display = 'none';
  }}
}}

function onMove(e) {{
  if (dragging) {{
    dragging.x = (e.offsetX - panX)/zoom - dragOff.x;
    dragging.y = (e.offsetY - panY)/zoom - dragOff.y;
    dragging.vx = 0; dragging.vy = 0;
  }} else if (lastMouse) {{
    panX += e.offsetX - lastMouse.x;
    panY += e.offsetY - lastMouse.y;
    lastMouse = {{x: e.offsetX, y: e.offsetY}};
  }}
}}

function onUp() {{ dragging = null; lastMouse = null; }}

function onWheel(e) {{
  e.preventDefault();
  var factor = e.deltaY > 0 ? 0.9 : 1.1;
  zoom *= factor;
  zoom = Math.max(0.2, Math.min(5, zoom));
}}

function onDblClick(e) {{
  var n = getNodeAt(e.offsetX, e.offsetY);
  if (n && n.type === 'disease') {{
    document.getElementById('diseaseFilter').value = n.label;
    filterDisease();
  }}
}}

function showDetail(n) {{
  var d = document.getElementById('detail');
  d.style.display = 'block';
  document.getElementById('detailTitle').textContent = n.label;
  var html = '<p><b>Type:</b> ' + n.type + '</p>';
  if (n.category) html += '<p><b>Category:</b> ' + n.category + '</p>';
  if (n.safety_score) html += '<p><b>Safety:</b> ' + n.safety_score + '</p>';
  if (n.uniprot) html += '<p><b>UniProt:</b> ' + n.uniprot + '</p>';
  if (n.plddt) html += '<p><b>pLDDT:</b> ' + n.plddt + '</p>';
  if (n.pocket) html += '<p><b>Pocket:</b> ' + n.pocket + ' res</p>';
  // connections
  var conns = graphEdges.filter(function(e) {{ return e.source === n || e.target === n; }});
  html += '<p><b>Connections:</b> ' + conns.length + '</p>';
  document.getElementById('detailContent').innerHTML = html;
}}

function filterDisease() {{
  filterDiseaseName = document.getElementById('diseaseFilter').value;
  applyFilter();
}}

function searchNode() {{
  searchQuery = document.getElementById('search').value.toLowerCase();
  applyFilter();
}}

function resetView() {{
  filterDiseaseName = 'all';
  searchQuery = '';
  document.getElementById('diseaseFilter').value = 'all';
  document.getElementById('search').value = '';
  panX = 0; panY = 0; zoom = 1;
  applyFilter();
}}

function toggleLabels() {{ showLabels = !showLabels; }}

window.onload = init;
</script>
</body>
</html>"""

    if output_path is not None:
        outp = Path(output_path)
        outp.write_text(html, encoding="utf-8")
        print(f"✅ {outp} ({len(html)} chars)")
    return html


def main():
    import argparse

    base_dir = Path(__file__).parent.parent
    results_dir = base_dir / "results"

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-json", type=Path, default=None, help="Input KG JSON (default: STAD export path)")
    ap.add_argument("--output-html", type=Path, default=None, help="Output HTML (default: STAD viewer path)")
    args = ap.parse_args()

    print("=" * 80)
    print("STAD: Knowledge Graph Interactive Viewer Generation")
    print("=" * 80)

    data_path = args.data_json or (results_dir / "stad_knowledge_graph_data.json")
    output_path = args.output_html or (results_dir / "stad_knowledge_graph_viewer.html")

    if not data_path.exists():
        print(f"ERROR: {data_path} not found")
        return 1

    generate_kg_viewer(data_path, output_path)

    print(f"\n브라우저에서 열기: open {output_path}")
    print("\n✅ 완료!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main() or 0)
