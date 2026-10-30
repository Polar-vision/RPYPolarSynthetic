"""Stamp "N / M" page numbers onto a print-to-PDF output.

Usage:
    python stamp.py report_raw.pdf technical_report_polar_geometry.pdf

The title page (page 1) is left unnumbered, matching the previous build;
numbering counts it, so page 2 shows "2 / M".
"""
import io
import sys

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color

FONT = "Helvetica"
SIZE = 8.5
GRAY = Color(0.42, 0.42, 0.42)
BOTTOM_PT = 35.0  # ~12.3 mm from the page edge


def make_overlay(width, height, label):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    c.setFont(FONT, SIZE)
    c.setFillColor(GRAY)
    c.drawCentredString(width / 2.0, BOTTOM_PT, label)
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


def main(src, dst):
    reader = PdfReader(src)
    total = len(reader.pages)
    writer = PdfWriter()

    for i, page in enumerate(reader.pages):
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        if i > 0:
            page.merge_page(make_overlay(w, h, f"{i + 1} / {total}"))
        writer.add_page(page)

    writer.add_metadata({
        "/Title": "从像平面到方向光锥：RPY 分层极坐标观测模型的数学性质、UV 对比与工程转化价值",
        "/Subject": "技术报告 · 基于仓库 RPYPolarSynthetic 的代码、实验 CSV 与既有图",
        "/Author": "RPYPolarSynthetic",
        "/Creator": "markdown-it + KaTeX + headless Chrome",
    })

    with open(dst, "wb") as fh:
        writer.write(fh)
    print(f"stamped {total} pages -> {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
