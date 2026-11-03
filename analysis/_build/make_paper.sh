#!/usr/bin/env bash
# Rebuild a manuscript PDF from its markdown source.
#
#   bash analysis/_build/make_paper.sh                 # Measurement draft
#   bash analysis/_build/make_paper.sh tim_manuscript  # IEEE TIM draft
#
# Same pipeline as make.sh: markdown-it + KaTeX -> print HTML -> headless Chrome
# -> pypdf/reportlab page numbers. Chrome needs the Windows form of the path.
set -euo pipefail

STEM="${1:-pairwise_sufficiency}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERE_WIN="$(cd "$HERE" && pwd -W 2>/dev/null || printf '%s' "$HERE")"
ANALYSIS="$(dirname "$HERE")"
PY="${PY:-E:/zuo/Program Files/Python311/python.exe}"
CHROME="${CHROME:-/c/Program Files/Google/Chrome/Application/chrome.exe}"

cd "$HERE"
[ -d node_modules ] || npm install --silent

PAPER_SRC="$STEM" node build_paper.js

"$CHROME" --headless=new --disable-gpu --no-sandbox \
  --no-pdf-header-footer --run-all-compositor-stages-before-draw \
  --virtual-time-budget=60000 \
  --print-to-pdf="$HERE_WIN/${STEM}_raw.pdf" \
  "file:///$HERE_WIN/${STEM}.html" 2>&1 | tail -1

TITLE="$("$PY" -c 'import pathlib,re,sys; s=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); print(re.search(r"^#\s+(.+)$",s,re.M).group(1))' "$ANALYSIS/paper/${STEM}.md")"
SUBJECT="${PDF_SUBJECT:-Manuscript draft}"
AUTHOR="${PDF_AUTHOR:-}"
"$PY" stamp.py "${STEM}_raw.pdf" "${STEM}_stamped.pdf" "$TITLE" "$SUBJECT" "$AUTHOR"
cp "${STEM}_stamped.pdf" "$ANALYSIS/paper/${STEM}.pdf"

PAGES="$("$PY" -c "import pypdf;print(len(pypdf.PdfReader('${STEM}_stamped.pdf').pages))")"
echo "done: ${PAGES} pages -> analysis/paper/${STEM}.pdf"
