#!/usr/bin/env bash
# Rebuild analysis/technical_report_polar_geometry.pdf from the markdown source.
#
#   bash analysis/_build/make.sh
#
# Pipeline: markdown-it + markdown-it-texmath/KaTeX -> print HTML
#           -> headless Chrome --print-to-pdf -> pypdf/reportlab page numbers.
# Requires: node (with node_modules in this dir), Chrome, and the project Python
#           (E:/zuo/Program Files/Python311/python.exe with pypdf + reportlab).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Git Bash reports /e/... while Chrome needs E:/... ; pwd -W gives the Windows
# form, and the fallback keeps the script usable under a POSIX shell.
HERE_WIN="$(cd "$HERE" && pwd -W 2>/dev/null || printf '%s' "$HERE")"
ANALYSIS="$(dirname "$HERE")"
PY="${PY:-E:/zuo/Program Files/Python311/python.exe}"
CHROME="${CHROME:-/c/Program Files/Google/Chrome/Application/chrome.exe}"

cd "$HERE"
[ -d node_modules ] || npm install --silent

node build_pdf.js

"$CHROME" --headless=new --disable-gpu --no-sandbox \
  --no-pdf-header-footer --run-all-compositor-stages-before-draw \
  --virtual-time-budget=60000 \
  --print-to-pdf="$HERE_WIN/report_raw.pdf" \
  "file:///$HERE_WIN/report.html" 2>&1 | tail -1

"$PY" stamp.py report_raw.pdf report_stamped.pdf

PAGES="$("$PY" -c "import pypdf,sys;print(len(pypdf.PdfReader('report_stamped.pdf').pages))")"
cp report_stamped.pdf "$ANALYSIS/technical_report_polar_geometry.pdf"
echo "done: ${PAGES} pages -> analysis/technical_report_polar_geometry.pdf"
