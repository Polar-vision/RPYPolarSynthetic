// Render analysis/technical_report_polar_geometry.md -> report.html (A4 print CSS).
// Math: markdown-it-texmath + KaTeX (dollars delimiters only, per project convention).
const fs = require('fs');
const path = require('path');
const MarkdownIt = require('markdown-it');
const texmath = require('markdown-it-texmath');
const katex = require('katex');

const BUILD = __dirname;
const ANALYSIS = path.resolve(BUILD, '..');
const SRC = path.join(ANALYSIS, 'technical_report_polar_geometry.md');
const OUT = path.join(BUILD, 'report.html');

// --- KaTeX assets: copy css + fonts next to the html -------------------------
const katexDist = path.join(BUILD, 'node_modules', 'katex', 'dist');
const katexOut = path.join(BUILD, 'katex');
fs.mkdirSync(katexOut, { recursive: true });
fs.copyFileSync(path.join(katexDist, 'katex.min.css'), path.join(katexOut, 'katex.min.css'));
const fontSrc = path.join(katexDist, 'fonts');
const fontOut = path.join(katexOut, 'fonts');
fs.mkdirSync(fontOut, { recursive: true });
for (const f of fs.readdirSync(fontSrc)) {
  if (f.endsWith('.woff2') || f.endsWith('.woff') || f.endsWith('.ttf')) {
    fs.copyFileSync(path.join(fontSrc, f), path.join(fontOut, f));
  }
}

const md = new MarkdownIt({
  html: false,
  linkify: false,
  typographer: false,
  breaks: false,
}).use(texmath, {
  engine: katex,
  delimiters: 'dollars',
  katexOptions: { throwOnError: false, strict: false, output: 'html' },
});

let src = fs.readFileSync(SRC, 'utf8');
// Normalise line endings so the parser never sees stray \r
src = src.replace(/\r\n/g, '\n');

// Split off the H1 title line: the PDF renders a title block with a subtitle.
const lines = src.split('\n');
const titleLine = lines.find((l) => l.startsWith('# ')) || '# 技术报告';
const title = titleLine.replace(/^#\s+/, '').trim();
const rest = lines.filter((l) => l !== titleLine).join('\n');

const bodyHtml = md.render(rest);

const esc = (s) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const css = `
@page {
  size: A4;
  margin: 17mm 17mm 18mm 17mm;
}
html {
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
body {
  font-family: "SimSun", "Songti SC", "Noto Serif CJK SC", serif;
  font-size: 10.5pt;
  line-height: 1.78;
  color: #111;
  margin: 0;
  text-align: justify;
  text-justify: inter-ideograph;
  word-break: break-word;
}
h1, h2, h3, h4, th, .subtitle {
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
}
h1 {
  font-size: 19.5pt;
  line-height: 1.38;
  font-weight: 700;
  margin: 2pt 0 5pt;
  text-align: left;
  letter-spacing: 0.2pt;
}
.subtitle {
  font-size: 8.8pt;
  color: #4a4a4a;
  margin: 0 0 5pt;
  text-align: left;
  font-weight: 400;
}
.title-rule {
  border: 0;
  border-top: 1.1pt solid #1a1a1a;
  margin: 7pt 0 16pt;
}
h2 {
  font-size: 14pt;
  font-weight: 700;
  margin: 20pt 0 11pt;
  padding-top: 11pt;
  border-top: 0.5pt solid #b0b0b0;
  break-after: avoid;
  page-break-after: avoid;
  text-align: left;
}
h2.abstract {
  border-top: 0;
  padding-top: 0;
  margin-top: 0;
  padding-bottom: 7pt;
  border-bottom: 0.5pt solid #b0b0b0;
}
h3 {
  font-size: 11.6pt;
  font-weight: 700;
  margin: 16pt 0 7pt;
  break-after: avoid;
  page-break-after: avoid;
  text-align: left;
}
h4 {
  font-size: 10.6pt;
  font-weight: 700;
  margin: 12pt 0 5pt;
  break-after: avoid;
  text-align: left;
}
p {
  margin: 0 0 6.5pt;
}
strong { font-weight: 700; }
a { color: inherit; text-decoration: none; }
code {
  font-family: Consolas, "Courier New", monospace;
  font-size: 9.4pt;
  padding: 0;
}
pre {
  font-family: Consolas, monospace;
  font-size: 9pt;
  line-height: 1.5;
  background: #f6f6f6;
  border: 0.4pt solid #ddd;
  padding: 7pt 9pt;
  margin: 8pt 0 10pt;
  white-space: pre-wrap;
  break-inside: avoid;
}
pre code { background: none; padding: 0; font-size: 9pt; }
ul, ol { margin: 0 0 7pt; padding-left: 17pt; }
li { margin: 2.5pt 0; text-align: justify; }
li > p { margin: 0 0 3pt; }
blockquote {
  margin: 8pt 0;
  padding: 2pt 0 2pt 10pt;
  border-left: 2pt solid #ccc;
  color: #333;
}
hr {
  border: 0;
  border-top: 0.4pt solid #ccc;
  margin: 14pt 0;
}
table {
  border-collapse: collapse;
  width: 100%;
  margin: 7pt 0 11pt;
  font-size: 8.9pt;
  line-height: 1.5;
  break-inside: auto;
}
thead { display: table-header-group; }
tr { break-inside: avoid; page-break-inside: avoid; }
th, td {
  border: 0.5pt solid #9a9a9a;
  padding: 3.2pt 5pt;
  text-align: left;
  vertical-align: top;
}
th {
  background: #efefef;
  font-weight: 700;
  font-size: 8.9pt;
}
td code, th code { font-size: 8.6pt; }
img {
  max-width: 100%;
  display: block;
  margin: 9pt auto 5pt;
  break-inside: avoid;
  page-break-inside: avoid;
}
.katex { font-size: 1.03em; }
.katex-display {
  margin: 10pt 0 11pt;
  break-inside: avoid;
}
.katex-display > .katex { font-size: 1.08em; }
`;

let html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>${esc(title)}</title>
<link rel="stylesheet" href="katex/katex.min.css">
<style>${css}</style>
</head>
<body>
<div class="title-block">
<h1>${esc(title)}</h1>
<div class="subtitle">技术报告 · 基于仓库 RPYPolarSynthetic 的代码、实验 CSV 与既有图</div>
<hr class="title-rule">
</div>
${bodyHtml}
</body>
</html>
`;

// Figures live in analysis/figures; html sits in analysis/_build/
html = html.replace(/(<img[^>]*src=")figures\//g, '$1../figures/');

// The abstract heading gets its own rule style (border-bottom instead of top).
html = html.replace('<h2>摘要</h2>', '<h2 class="abstract">摘要</h2>');

fs.writeFileSync(OUT, html, 'utf8');

// --- Sanity report ----------------------------------------------------------
const rawMath = (html.match(/\$\$/g) || []).length;
const inlineLeft = (html.match(/[^\\]\$[^$\n]{1,80}\$/g) || []).length;
const imgs = (html.match(/<img /g) || []).length;
const tables = (html.match(/<table>/g) || []).length;
const katexErrors = (html.match(/katex-error/g) || []).length;
console.log(JSON.stringify({
  out: OUT,
  bytes: html.length,
  images: imgs,
  tables,
  rawDollarDollarLeft: rawMath,
  inlineDollarPairsLeft: inlineLeft,
  katexErrors,
}, null, 2));
