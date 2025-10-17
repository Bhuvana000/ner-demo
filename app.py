"""
app.py — Single-file NER website (Flask backend + embedded frontend)

How to run (Windows):
  py -3 -m pip install -r requirements.txt
  py -3 app.py

Or (if python works):
  python -m pip install -r requirements.txt
  python app.py

requirements.txt (if you want a file):
  Flask
  spacy
  flask-cors

This script will attempt to download the spaCy model automatically if it's missing.
"""
import os
import sys
import subprocess
from flask import Flask, request, jsonify, render_template_string
from html import escape

# Try to import optional CORS package; if absent we will not fail (same-origin is fine).
try:
    from flask_cors import CORS
    _have_cors = True
except Exception:
    _have_cors = False

# Ensure required packages are installed: Flask and spaCy
missing = []
try:
    import flask  # noqa: F401
except Exception:
    missing.append("Flask")
try:
    import spacy  # noqa: F401
except Exception:
    missing.append("spacy")

if missing:
    print("Installing missing packages:", ", ".join(missing))
    subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])

# Now import them
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
if _have_cors:
    CORS(app)

# Attempt to load spaCy model; if missing, download it using the same interpreter
MODEL = "en_core_web_sm"
try:
    import spacy
    nlp = spacy.load(MODEL)
except Exception as e:
    print(f"spaCy model '{MODEL}' not found. Attempting to download it now... (this may take a minute)")
    try:
        subprocess.check_call([sys.executable, "-m", "spacy", "download", MODEL])
        import importlib
        importlib.invalidate_caches()
        nlp = spacy.load(MODEL)
        print(f"Successfully downloaded and loaded '{MODEL}'.")
    except Exception as e2:
        print("Automatic model download failed.", e2, file=sys.stderr)
        print("Please run manually:\n    python -m spacy download en_core_web_sm\nand then re-run this script.", file=sys.stderr)
        raise

# Minimal HTML UI embedded in this file
INDEX_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Named Entity Recognition — Demo</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
    body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial; background:#f4f6f8; margin:0; padding:20px; }
    .wrap { max-width:900px; margin:24px auto; background:#fff; padding:20px; border-radius:10px; box-shadow:0 6px 18px rgba(0,0,0,0.06); }
    textarea { width:100%; min-height:120px; font-size:15px; padding:12px; border-radius:8px; border:1px solid #ddd; box-sizing:border-box; }
    button { padding:10px 14px; border-radius:8px; border:none; cursor:pointer; margin-right:8px; }
    .btn-primary { background:#2563eb; color:#fff; }
    .btn-muted { background:#eef2ff; color:#101010; }
    .panel { border:1px solid #e6e9ee; padding:12px; border-radius:8px; background:#fff; margin-top:12px; }
    mark.entity { padding:0.08em 0.3em; border-radius:6px; margin-right:4px; display:inline-block; }
    .label { font-size:12px; opacity:0.8; margin-left:6px; }
    table { width:100%; border-collapse:collapse; margin-top:10px; }
    th, td { text-align:left; padding:8px; border-bottom:1px solid #f0f2f5; font-size:14px; }
    .muted { color:#6b7280; font-size:13px; }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Named Entity Recognition (NER)</h1>
    <p class="muted">Type text below and click <strong>Analyze</strong>.</p>

    <textarea id="inputText">Barack Obama was born in Hawaii. He was the 44th President of the United States. Apple is based in Cupertino, California.</textarea>

    <div style="margin-top:10px;">
      <button id="analyzeBtn" class="btn-primary">Analyze</button>
      <button id="clearBtn" class="btn-muted">Clear Entities</button>
    </div>

    <div id="error" style="color:crimson;margin-top:8px;"></div>

    <section style="margin-top:14px;">
      <h3>Highlighted output</h3>
      <div id="highlight" class="panel" style="min-height:70px; white-space:pre-wrap;"></div>
    </section>

    <section style="margin-top:14px;">
      <h3>Entities</h3>
      <div id="entities" class="panel muted">No entities yet.</div>
    </section>

    <footer style="margin-top:16px; font-size:13px; color:#6b7280;">
      Backend: spaCy — model: <strong>en_core_web_sm</strong>
    </footer>
  </div>

<script>
const analyzeBtn = document.getElementById('analyzeBtn');
const clearBtn = document.getElementById('clearBtn');
const inputText = document.getElementById('inputText');
const highlight = document.getElementById('highlight');
const entitiesDiv = document.getElementById('entities');
const errorDiv = document.getElementById('error');

const COLOR_MAP = {
  'PERSON':'#ffe8e6','ORG':'#e8fff0','GPE':'#fff6e6','LOC':'#eef2ff','DATE':'#fff0f5','TIME':'#f0fff5','MONEY':'#fff7e6','PERCENT':'#f3fff6'
};

function escapeHtml(str){
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function renderHighlighted(text, entities){
  if(!entities || entities.length===0){
    highlight.textContent = text;
    return;
  }
  entities.sort((a,b)=>a.start - b.start);
  let cursor = 0;
  let out = '';
  for(const e of entities){
    if(cursor < e.start){
      out += escapeHtml(text.slice(cursor, e.start));
    }
    const label = e.label;
    const span = escapeHtml(text.slice(e.start, e.end));
    const bg = COLOR_MAP[label] || '#f2f9ff';
    out += `<mark class="entity" style="background:${bg}">${span} <span class="label">[${label}]</span></mark>`;
    cursor = e.end;
  }
  if(cursor < text.length) out += escapeHtml(text.slice(cursor));
  highlight.innerHTML = '<div style="line-height:1.5;">' + out + '</div>';
}

function renderEntitiesTable(entities){
  if(!entities || entities.length===0){
    entitiesDiv.innerHTML = 'No entities detected.';
    return;
  }
  let html = '<table><thead><tr><th>Text</th><th>Label</th><th>Span</th></tr></thead><tbody>';
  for(const e of entities){
    html += `<tr><td>${escapeHtml(e.text)}</td><td>${escapeHtml(e.label)}</td><td>${e.start}–${e.end}</td></tr>`;
  }
  html += '</tbody></table>';
  entitiesDiv.innerHTML = html;
}

analyzeBtn.onclick = async ()=>{
  errorDiv.textContent = '';
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = 'Analyzing...';
  try{
    const resp = await fetch('/api/ner', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ text: inputText.value })
    });
    if(!resp.ok){
      const t = await resp.text();
      throw new Error(t || 'Server error');
    }
    const data = await resp.json();
    const ents = data.entities || [];
    renderHighlighted(inputText.value, ents);
    renderEntitiesTable(ents);
  }catch(err){
    errorDiv.textContent = err.message || String(err);
  }finally{
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = 'Analyze';
  }
};

clearBtn.onclick = ()=>{
  renderHighlighted(inputText.value, []);
  renderEntitiesTable([]);
};

// initial render
renderHighlighted(inputText.value, []);
renderEntitiesTable([]);
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(INDEX_HTML)

@app.route("/api/ner", methods=["POST"])
def api_ner():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not isinstance(text, str) or text.strip() == "":
        return jsonify({"error": "No text provided"}), 400

    doc = nlp(text)
    entities = []
    for ent in doc.ents:
        entities.append({
            "text": ent.text,
            "label": ent.label_,
            "start": ent.start_char,
            "end": ent.end_char
        })
    return jsonify({"entities": entities})

if __name__ == "__main__":
    # Use PORT env var if provided
    port = int(os.environ.get("PORT", 5000))
    host = "127.0.0.1"
    print(f"Starting NER website at http://{host}:{port}/")
    try:
        # debug True for auto-reload during development. Turn off in production.
        app.run(host=host, port=port, debug=True)
    except Exception as e:
        print("Failed to start server:", e, file=sys.stderr)
        raise
