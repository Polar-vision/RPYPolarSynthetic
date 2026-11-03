#!/usr/bin/env python3
"""Build the Measurement submission package from submission_meta.json.

Generates, in this directory:
    Title_page.pdf / .md
    Cover_letter.pdf / .md
    Highlights.docx / .txt
    Figure_1.png, Figure_2.png, Figure_3.png   (RGB, 400 dpi, for separate upload)
    Manuscript_anonymized.pdf                  (copied from analysis/paper/)
    Supplementary_material.zip
    MANIFEST.txt                               (sizes + SHA-256)

Run:  "E:/zuo/Program Files/Python311/python.exe" build_frontmatter.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
ROOT = PAPER.parent.parent          # repository root
BUILD = ROOT / "analysis" / "_build"

CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
PY = Path(r"E:\zuo\Program Files\Python311\python.exe")

META = json.loads((HERE / "submission_meta.json").read_text(encoding="utf-8"))

# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

CSS = """
@page { size: A4; margin: 25mm 22mm 22mm 22mm; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "Times New Roman", Times, serif; font-size: 11pt;
       line-height: 1.5; color: #111; margin: 0; }
h1 { font-size: 15pt; line-height: 1.35; font-weight: 700; margin: 0 0 14pt;
     text-align: left; }
h2 { font-size: 10pt; font-weight: 700; margin: 16pt 0 5pt; text-align: left;
     letter-spacing: 0.3pt; text-transform: uppercase; border-bottom: 0.4pt solid #bbb;
     padding-bottom: 2pt; }
p { margin: 0 0 9pt; text-align: justify; }
.byline { text-align: center; font-size: 12pt; margin: 4pt 0 3pt; }
.affil { text-align: center; font-size: 10pt; color: #222; margin: 0 0 2pt; }
.meta-table { width: 100%; border-collapse: collapse; font-size: 10pt;
              margin: 4pt 0 10pt; }
.meta-table td { padding: 2.5pt 0; vertical-align: top; }
.meta-table td.k { width: 30mm; color: #444; }
.rule { border: 0; border-top: 1pt solid #1a1a1a; margin: 10pt 0 16pt; }
.small { font-size: 9.5pt; color: #333; }
ul { margin: 4pt 0 10pt 0; padding-left: 16pt; }
li { margin: 3pt 0; }
.sig { margin-top: 18pt; }
.sig p { margin: 0 0 2pt; text-align: left; }
.date { margin-bottom: 18pt; text-align: left; }
"""


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def html_doc(body: str, doc_title: str = "") -> str:
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{esc(doc_title)}</title>"
        f"<style>{CSS}</style></head><body>{body}</body></html>"
    )


def html_to_pdf(html_name: str, pdf_name: str, html: str) -> Path:
    hp = HERE / html_name
    hp.write_text(html, encoding="utf-8")
    out = HERE / pdf_name
    if out.exists():
        out.unlink()
    url = "file:///" + str(hp).replace("\\", "/")
    cmd = [
        str(CHROME), "--headless=new", "--disable-gpu", "--no-sandbox",
        "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=30000",
        f"--print-to-pdf={out}", url,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if not out.exists():
        sys.exit(f"Chrome failed for {html_name}:\n{res.stderr[-1500:]}")
    return out


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# 1. title page
# --------------------------------------------------------------------------- #

a = META["author"]
orc = a["orcid"].strip() or "to be inserted"
orc_line = f"ORCID: {orc}"

affil_full = f"{a['affiliation']}, {a['address']}"

title_html = f"""
<h1>{esc(META['title'])}</h1>
<p class="byline"><b>{esc(a['full_name'])}</b></p>
<p class="affil">{esc(a['affiliation'])}</p>
<p class="affil">{esc(a['address'])}</p>
<p class="affil">Corresponding author &mdash; {esc(a['email'])}{'' if not a['orcid'].strip() else ' &mdash; ORCID: ' + esc(a['orcid'])}</p>
<hr class="rule">

<h2>Keywords</h2>
<p>{esc('; '.join(META['keywords']))}</p>

<h2>Funding</h2>
<p>{esc(META['declarations']['funding_statement'])}</p>

<h2>Declaration of competing interest</h2>
<p>{esc(META['declarations']['competing_interest'])}</p>

<h2>CRediT author statement</h2>
<p>{esc(META['declarations']['credit'])}</p>

<h2>Ethics</h2>
<p>{esc(META['declarations']['ethics'])}</p>

<h2>Data availability</h2>
<p>{esc(META['declarations']['data_availability'])}</p>

<h2>Declaration of generative AI and AI-assisted technologies</h2>
<p>{esc(META['declarations']['ai_use'])}</p>
"""

title_md = f"""# Title page

**{META['title']}**

**Author:** {a['full_name']}

**Affiliation:** {a['affiliation']}, {a['address']}

**Corresponding author:** {a['email']}{'' if not a['orcid'].strip() else ' — ORCID: ' + a['orcid']}

## Keywords

{'; '.join(META['keywords'])}

## Funding

{META['declarations']['funding_statement']}

## Declaration of competing interest

{META['declarations']['competing_interest']}

## CRediT author statement

{META['declarations']['credit']}

## Ethics

{META['declarations']['ethics']}

## Data availability

{META['declarations']['data_availability']}

## Declaration of generative AI and AI-assisted technologies

{META['declarations']['ai_use']}
"""

(HERE / "Title_page.md").write_text(title_md, encoding="utf-8")
html_to_pdf("_title_page.html", "Title_page.pdf",
            html_doc(title_html, "Title page — " + META["running_title"]))

# --------------------------------------------------------------------------- #
# 2. cover letter
# --------------------------------------------------------------------------- #

cl = META["cover_letter"]
paras = "\n".join(f"<p>{p}</p>" for p in cl["paragraphs"])

cover_html = f"""
<p class="date">3 November 2026</p>
<p>To the Editor<br><i>{esc(META['journal'])}</i> — Elsevier</p>
<p style="margin-top:14pt">{esc(cl['salutation'])}</p>
{paras}
<div class="sig">
<p>{esc(cl['closing'])}</p>
<p style="margin-top:12pt"><b>{esc(a['full_name'])}</b></p>
<p>{esc(a['affiliation'])}</p>
<p>{esc(a['address'])}</p>
<p>{esc(a['email'])}{'' if not a['orcid'].strip() else ' &mdash; ORCID: ' + esc(a['orcid'])}</p>
</div>
"""
html_to_pdf("_cover_letter.html", "Cover_letter.pdf",
            html_doc(cover_html, "Cover letter — " + META["running_title"]))

cover_md = ["3 November 2026", "", f"To the Editor, *{META['journal']}* (Elsevier)", "",
            cl["salutation"], ""]
for p in cl["paragraphs"]:
    cover_md += [p.replace("<i>", "*").replace("</i>", "*"), ""]
cover_md += [cl["closing"], "", f"**{a['full_name']}**  ", a["affiliation"] + "  ",
             a["address"] + "  ", a["email"] + "  "]
if a["orcid"].strip():
    cover_md.append(f"ORCID: {a['orcid']}")
(HERE / "Cover_letter.md").write_text("\n".join(cover_md), encoding="utf-8")

# --------------------------------------------------------------------------- #
# 3. highlights
# --------------------------------------------------------------------------- #

bad = [(h, len(h)) for h in META["highlights"] if len(h) > 85]
if bad:
    sys.exit("Highlights over 85 characters: " + repr(bad))

(HERE / "Highlights.txt").write_text(
    "\n".join(f"- {h}" for h in META["highlights"]) + "\n", encoding="utf-8")

try:
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(11)

    doc.add_paragraph("Highlights")
    doc.add_paragraph(META["title"])
    doc.add_paragraph("")
    for h in META["highlights"]:
        doc.add_paragraph(h, style="List Bullet")
    doc.add_paragraph("")
    doc.add_paragraph(f"{a['full_name']}, {a['affiliation']}, {a['address']}, "
                      f"{a['email']}")
    doc.save(str(HERE / "Highlights.docx"))
except Exception as e:  # noqa: BLE001
    print("WARNING: docx generation failed:", e)


# --------------------------------------------------------------------------- #
# 3b. editable declarations required by the submission form
#     (Declaration of Interest, Title Page, Acknowledgments)
# --------------------------------------------------------------------------- #

def write_docx(path, heading, blocks):
    """blocks: list of (kind, text); kind in {p, b, small, gap}."""
    try:
        from docx import Document
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except Exception as e:  # noqa: BLE001
        print("WARNING: python-docx unavailable:", e)
        return

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    h = doc.add_paragraph()
    run = h.add_run(heading)
    run.bold = True
    run.font.size = Pt(13)

    for kind, text in blocks:
        if kind == "gap":
            doc.add_paragraph("")
        elif kind == "p":
            doc.add_paragraph(text)
        elif kind == "title":
            p = doc.add_paragraph()
            r = p.add_run(text)
            r.italic = True
        elif kind == "b":
            p = doc.add_paragraph()
            p.add_run(text).bold = True
        elif kind == "small":
            p = doc.add_paragraph()
            r = p.add_run(text)
            r.font.size = Pt(10)
        elif kind == "center":
            p = doc.add_paragraph(text)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.save(str(path))


today = "3 November 2026"

write_docx(
    HERE / "Declaration_of_Interest.docx",
    "Declaration of Interest",
    [
        ("title", META["title"]),
        ("gap", ""),
        ("p", META["declarations"]["competing_interest"]),
        ("p", "This statement covers all financial and non-financial interests that could be "
              "perceived to influence the work reported in the manuscript, including funding, "
              "employment, consultancies, patents and personal relationships."),
        ("gap", ""),
        ("b", a["full_name"]),
        ("small", f"{a['affiliation']}, {a['address']}"),
        ("small", f"E-mail: {a['email']}"),
        ("small", f"ORCID: {orc}"),
        ("gap", ""),
        ("small", f"Date: {today}"),
    ],
)

write_docx(
    HERE / "Title_page.docx",
    "Title Page with Author Information",
    [
        ("title", META["title"]),
        ("gap", ""),
        ("b", a["full_name"]),
        ("small", f"{a['affiliation']}"),
        ("small", a["address"]),
        ("small", f"E-mail: {a['email']}"),
        ("small", f"ORCID: {orc}"),
        ("gap", ""),
        ("small", "Corresponding author: " + a["full_name"]),
        ("small", f"Article type: {META['article_type']}"),
        ("small", f"Running title: {META['running_title']}"),
        ("gap", ""),
        ("b", "Keywords"),
        ("small", "; ".join(META["keywords"])),
        ("gap", ""),
        ("b", "Funding"),
        ("small", META["declarations"]["funding_statement"]),
        ("gap", ""),
        ("b", "Declaration of competing interest"),
        ("small", META["declarations"]["competing_interest"]),
        ("gap", ""),
        ("b", "CRediT author statement"),
        ("small", META["declarations"]["credit"]),
        ("gap", ""),
        ("b", "Ethics"),
        ("small", META["declarations"]["ethics"]),
        ("gap", ""),
        ("b", "Data availability"),
        ("small", META["declarations"]["data_availability"]),
        ("gap", ""),
        ("b", "Declaration of generative AI and AI-assisted technologies"),
        ("small", META["declarations"]["ai_use"]),
    ],
)

write_docx(
    HERE / "Acknowledgments.docx",
    "Acknowledgments",
    [
        ("title", META["title"]),
        ("gap", ""),
        ("b", "Funding"),
        ("p", META["declarations"]["funding_statement"]),
        ("gap", ""),
        ("b", "Acknowledgments"),
        ("p", "The author thanks the NASA Goddard Space Flight Center for making the LRO "
              "pointing and alignment specification 431-SPEC-000113 Rev A publicly available; "
              "the replay reported in Section 5 rests entirely on that document. The numerical "
              "work was carried out with the open-source Python scientific stack (NumPy and "
              "Matplotlib), and the author acknowledges its contributors."),
        ("p", "No third party was involved in the design of the study, in the analysis or "
              "interpretation of the results, or in the preparation of the manuscript."),
        ("gap", ""),
        ("small", "This file contains acknowledgments and funding information only. It is "
                  "supplied separately from the anonymised manuscript so that the manuscript "
                  "can be reviewed without author identification."),
    ],
)

print("built Declaration_of_Interest.docx, Title_page.docx, Acknowledgments.docx")

# --------------------------------------------------------------------------- #
# 4. figures (flatten to RGB, 400 dpi, journal-safe names)
# --------------------------------------------------------------------------- #

from PIL import Image  # noqa: E402

FIG_SRC = [
    ("paper_fig1.png", "Figure_1.png"),
    ("p3_replay.png", "Figure_2.png"),
    ("paper_fig3.png", "Figure_3.png"),
]
fig_dir = HERE / "figures"
fig_dir.mkdir(exist_ok=True)
for src_name, dst_name in FIG_SRC:
    src = ROOT / "analysis" / "figures" / src_name
    if not src.exists():
        sys.exit(f"missing figure: {src}")
    im = Image.open(src).convert("RGBA")
    flat = Image.new("RGB", im.size, "white")
    flat.paste(im, mask=im.split()[3])
    dst = fig_dir / dst_name
    flat.save(dst, "PNG", dpi=(400, 400), optimize=True)
    print(f"figure {dst_name}: {flat.size[0]}x{flat.size[1]} px, 400 dpi")

# --------------------------------------------------------------------------- #
# 5. manuscript
# --------------------------------------------------------------------------- #

ms_src = PAPER / "measurement_manuscript.pdf"
if not ms_src.exists():
    sys.exit("manuscript PDF not built yet; run analysis/_build/make_paper.sh first")
shutil.copy2(ms_src, HERE / "Manuscript_anonymized.pdf")

# Editorial Manager takes the abstract as plain text: LaTeX renders as garbage.
# Derive it from the manuscript so the two can never drift apart.
ms_md = (PAPER / "measurement_manuscript.md").read_text(encoding="utf-8")
abstract_md = ms_md.split("## Abstract", 1)[1].split("**Keywords**", 1)[0].strip()
plain = abstract_md
for old, new in [
    (r"$\sqrt{3}A$", "\u221a3\u00b7A"),
    ("$2A$", "2\u00b7A"),
    (r"$15.5\%$", "15.5%"),
    (r"$3\sigma$", "3\u03c3"),
    ("$1519''$", "1519-arc-second"),
    ("$A$", "A"),
    ("`431-SPEC-000113`", "431-SPEC-000113"),
    ("*pair*", "pair"),
]:
    plain = plain.replace(old, new)
if "$" in plain or "`" in plain:
    sys.exit("abstract still contains markup after conversion:\n" + plain)
(HERE / "Abstract.txt").write_text(plain + "\n", encoding="utf-8")
print(f"abstract: {len(plain.split())} words, plain text")

# --------------------------------------------------------------------------- #
# 6. supplementary package
# --------------------------------------------------------------------------- #

supp_root = HERE / "supplementary"
if supp_root.exists():
    shutil.rmtree(supp_root)
pkg = supp_root / "pairwise_sum_supplement"
# Mirror the repository layout exactly: p3_replay.load_allocations() resolves the
# CSV as parents[2]/analysis/data/, and the figure scripts write to
# <cwd>/analysis/figures/.  Any other layout runs into FileNotFoundError.
(pkg / "analysis" / "data").mkdir(parents=True)
(pkg / "analysis" / "figures").mkdir(parents=True)
(pkg / "src" / "rpy_polar_synth").mkdir(parents=True)
(pkg / "outputs_p3").mkdir(parents=True)

shutil.copy2(ROOT / "analysis" / "data" / "lro_alignment_allocations.csv",
             pkg / "analysis" / "data" / "lro_alignment_allocations.csv")
for py in (ROOT / "src" / "rpy_polar_synth").glob("*.py"):
    shutil.copy2(py, pkg / "src" / "rpy_polar_synth" / py.name)
for stem in ["run_p3_replay.py", "run_regime_map.py", "plot_p3_replay.py",
             "plot_paper_fig1.py", "plot_regime.py"]:
    s = ROOT / stem
    if s.exists():
        shutil.copy2(s, pkg / stem)
for f in (ROOT / "outputs_p3").iterdir():
    if f.is_file():
        shutil.copy2(f, pkg / "outputs_p3" / f.name)

(pkg / "analysis" / "figures" / "README.txt").write_text(
    "The figure scripts write their PNG output into this directory.\n",
    encoding="utf-8")
(pkg / "requirements.txt").write_text("numpy\nmatplotlib\n", encoding="utf-8")

(pkg / "README.md").write_text(
    f"""# Supplementary material

**{META['title']}**

{a['full_name']}, {a['affiliation']}, {a['address']}. {a['email']}

This package reproduces every number, table and figure in the manuscript.

## Layout

```
analysis/data/lro_alignment_allocations.csv   ten allocations transcribed from
                                              NASA 431-SPEC-000113 Rev A, each
                                              with its clause number and the
                                              verbatim sentence quoted
analysis/figures/                             output directory for the figures
src/rpy_polar_synth/                          solver and supporting modules
run_p3_replay.py                              replay of the specification
                                              (Section 5, Figure 2)
run_regime_map.py                             channel-count / ratio /
                                              heterogeneity sweeps (Section 6)
plot_paper_fig1.py                            Figure 1
plot_p3_replay.py                             Figure 2
plot_regime.py                                Figure 3
outputs_p3/                                   derived CSV and JSON behind every
                                              stated value
```

## Reproduce

Run everything from the package root; the scripts resolve paths relative to it.

```
python -m venv .venv
.venv\\Scripts\\activate            # POSIX: . .venv/bin/activate
pip install -r requirements.txt

set PYTHONPATH=src                # POSIX: export PYTHONPATH=src

python run_p3_replay.py           # rewrites outputs_p3/lro_channels.csv,
                                  # rescue_curve.csv, production_view.csv,
                                  # summary.json
python run_regime_map.py          # rewrites the regime_* files
python plot_paper_fig1.py         # Figure 1
python plot_p3_replay.py          # Figure 2
python plot_regime.py             # Figure 3
```

## Notes

- The solver `p3_replay.py` enumerates candidate common orientations; every reported
  feasibility verdict was cross-checked against an independent spherical-cap solver
  implemented in `replication.py`. The two agree on all 300 random instances tested.
- The specification itself is not redistributed. The transcription keeps the clause
  number and the verbatim sentence for each allocation, so every value can be traced
  to the public document.
""",
    encoding="utf-8",
)

zip_path = HERE / "Supplementary_material.zip"
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(pkg.rglob("*")):
        if f.is_file():
            z.write(f, f.relative_to(supp_root))

# --------------------------------------------------------------------------- #
# 7. manifest
# --------------------------------------------------------------------------- #

items = sorted(p for p in HERE.iterdir()
               if p.is_file() and p.name not in {"build_frontmatter.py",
                                                 "submission_meta.json",
                                                 "MANIFEST.txt"}
               and not p.name.startswith("_"))
lines = ["Submission package manifest", "=" * 26,
         f"journal : {META['journal']}", f"title   : {META['title']}", ""]
for p in items:
    lines.append(f"{p.name:32s} {p.stat().st_size:>10,d} B  {sha256(p)[:16]}")
lines += ["", "figures/"]
for p in sorted(fig_dir.iterdir()):
    lines.append(f"{'  ' + p.name:32s} {p.stat().st_size:>10,d} B  {sha256(p)[:16]}")
(HERE / "MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

print("\n--- highlight lengths ---")
for h in META["highlights"]:
    print(f"{len(h):3d}  {h}")
print("\nbuilt:", HERE)
