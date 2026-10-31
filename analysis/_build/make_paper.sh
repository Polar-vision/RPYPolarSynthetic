#!/usr/bin/env bash
# Rebuild analysis/paper/pairwise_sufficiency.pdf from the manuscript markdown.
#
#   bash analysis/_build/make_paper.sh
#
# Same pipeline as make.sh: markdown-it + KaTeX -> print HTML -> headless Chrome
# -> pypdf/reportlab page numbers. Chrome needs the Windows form of the path.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERE_WIN="$(cd "$HERE" && pwd -W 2>/dev/null || printf '%s' "$HERE")"
ANALYSIS="$(dirname "$HERE")"
PY="${PY:-E:/zuo/Program Files/Python311/python.exe}"
CHROME="${CHROME:-/c/Program Files/Google/Chrome/Application/chrome.exe}"

cd "$HERE"
[ -d node_modules ] || npm install --silent

node build_paper.js

"$CHROME" --headless=new --disable-gpu --no-sandbox \
  --no-pdf-header-footer --run-all-compositor-stages-before-draw \
  --virtual-time-budget=60000 \
  --print-to-pdf="$HERE_WIN/paper_raw.pdf" \
  "file:///$HERE_WIN/paper.html" 2>&1 | tail -1

"$PY" stamp.py paper_raw.pdf paper_stamped.pdf
cp paper_stamped.pdf "$ANALYSIS/paper/pairwise_sufficiency.pdf"

PAGES="$("$PY" -c "import pypdf;print(len(pypdf.PdfReader('paper_stamped.pdf').pages))")"
echo "done: ${PAGES} pages -> analysis/paper/pairwise_sufficiency.pdf"
