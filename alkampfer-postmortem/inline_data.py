#!/usr/bin/env python3
"""
Inietta in modo SICURO il JSON dentro index.html (riga 733: `const D=...`).
Risolve i problemi ricorrenti di inlining JSON-in-HTML:
  1) ensure_ascii=True       -> nessun U+2028/U+2029 raw che spezza il parser JS
  2) </  ->  <\/             -> impedisce all'HTML parser di chiudere <script>
  3) <!-- e -->  ->  escapate  -> evita commenti HTML interni
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "alkampfer_data.json"
HTML = HERE / "index.html"

data = json.loads(SRC.read_text(encoding="utf-8"))
js_payload = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
js_payload = (js_payload
              .replace("</", "<\\/")
              .replace("<!--", "<\\!--")
              .replace("-->", "--\\>"))

lines = HTML.read_text(encoding="utf-8").splitlines(keepends=True)
DATA_LINE_INDEX = next((i for i, ln in enumerate(lines) if ln.lstrip().startswith("const D=")), None)
if DATA_LINE_INDEX is None:
    sys.exit("ERR: nessuna riga 'const D=' trovata in index.html")

lines[DATA_LINE_INDEX] = "const D=" + js_payload + ";\n"
HTML.write_text("".join(lines), encoding="utf-8")

# Sanity-check: re-parse
recovered = (lines[DATA_LINE_INDEX][len("const D="):].rstrip("\n").rstrip(";")
             .replace("<\\/", "</").replace("<\\!--", "<!--").replace("--\\>", "-->"))
parsed = json.loads(recovered)
print(f"OK · post={len(parsed.get('posts',[]))}  followers={parsed['profile']['followers']:,}  "
      f"line_len={len(lines[DATA_LINE_INDEX]):,}")
