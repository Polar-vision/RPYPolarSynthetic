// Render analysis/paper/pairwise_sufficiency.md -> paper.html (A4, single column, English).
// Math: markdown-it-texmath + KaTeX (dollars only, per project convention).
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const MarkdownIt = require('markdown-it');
const texmath = require('markdown-it-texmath');
const katex = require('katex');

const BUILD = __dirname;
const ANALYSIS = path.resolve(BUILD, '..');
const PAPER = path.join(ANALYSIS, 'paper');
const SRC = path.join(PAPER, 'pairwise_sufficiency.md');
const OUT = path.join(BUILD, 'paper.html');

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

const md = new MarkdownIt({ html: false, linkify: false, typographer: false, breaks: false })
  .use(texmath, {
    engine: katex,
    delimiters: 'dollars',
    katexOptions: { throwOnError: false, strict: false, output: 'html' },
  });

let src = fs.readFileSync(SRC, 'utf8').replace(/\r\n/g, '\n');

const lines = src.split('\n');
const titleLine = lines.find((l) => l.startsWith('# ')) || '# Untitled';
const title = titleLine.replace(/^#\s+/, '').trim();
let rest = lines.filter((l) => l !== titleLine).join('\n');

// The subtitle is the first bold-italic line after the title; lift it out.
const subMatch = rest.match(/^\s*\*\*(.+?)\*\*\s*\n/i);
const subtitle = subMatch ? subMatch[1] : '';
if (subMatch) rest = rest.replace(subMatch[0], '');

let bodyHtml = md.render(rest);

// Figures: wrap <p><img></p> + <p><em>Figure n. ...</em></p> in a <figure> so the
// image and its caption never split across a page.
bodyHtml = bodyHtml.replace(/<p><em>(Figure\s+\d)/g, '<p class="caption"><em>$1');
bodyHtml = bodyHtml.replace(
  /<p>(<img[^>]+>)<\/p>\s*<p class="caption">([\s\S]*?)<\/p>/g,
  (m, img, cap) => `<figure>${img}<figcaption>${cap}</figcaption></figure>`);
// Resolve image paths against the markdown file, so the HTML can live elsewhere.
bodyHtml = bodyHtml.replace(/src="([^"]+)"/g, (m, p) => {
  if (/^(https?:|file:|data:)/.test(p)) return m;
  return `src="${pathToFileURL(path.resolve(PAPER, p)).href}"`;
});

const css = `
@page { size: A4; margin: 20mm 21mm 18mm 21mm; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  font-family: "Times New Roman", Times, "Liberation Serif", serif;
  font-size: 10.4pt; line-height: 1.485; color: #111; margin: 0;
  text-align: justify; -webkit-hyphens: auto; hyphens: auto;
}
h1 { font-size: 17pt; line-height: 1.28; font-weight: 700; margin: 0 0 4pt;
     text-align: left; letter-spacing: 0.1pt; }
.subtitle { font-size: 11pt; font-style: italic; color: #333; margin: 0 0 10pt; }
.title-rule { border: 0; border-top: 1pt solid #1a1a1a; margin: 6pt 0 12pt; }
h2 { font-size: 11.6pt; font-weight: 700; margin: 13pt 0 5pt; text-align: left;
     break-after: avoid; page-break-after: avoid; }
h2.abstract { font-size: 9.6pt; margin: 12pt 0 4pt; letter-spacing: 0.4pt;
              text-transform: uppercase; }
h3 { font-size: 10.6pt; font-style: italic; font-weight: 700; margin: 12pt 0 4pt;
     text-align: left; break-after: avoid; }
p { margin: 0 0 5.6pt; }
strong { font-weight: 700; }
em { font-style: italic; }
a { color: inherit; text-decoration: none; }
code { font-family: "Consolas", monospace; font-size: 8.8pt; }
pre { font-family: Consolas, monospace; font-size: 8.4pt; line-height: 1.38;
      background: #f7f7f7; border: 0.4pt solid #ddd; padding: 5pt 7pt;
      margin: 6pt 0 8pt; white-space: pre-wrap; break-inside: avoid; }
ul, ol { margin: 0 0 6pt; padding-left: 15pt; }
li { margin: 1.5pt 0; text-align: justify; }
blockquote { margin: 6pt 0; padding: 1pt 0 1pt 9pt; border-left: 1.6pt solid #ccc; color: #333; }
hr { border: 0; border-top: 0.4pt solid #bbb; margin: 10pt 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 8pt;
        font-size: 8.6pt; line-height: 1.35;
        break-inside: avoid; page-break-inside: avoid; }
thead { display: table-header-group; }
tr { break-inside: avoid; page-break-inside: avoid; }
th, td { border-top: 0.5pt solid #333; border-bottom: 0.5pt solid #333;
         padding: 2.6pt 4pt; text-align: left; vertical-align: top; }
thead th { border-top: 1pt solid #111; border-bottom: 0.6pt solid #111; }
tbody tr:last-child td { border-bottom: 1pt solid #111; }
img { max-width: 100%; display: block; margin: 8pt auto 3pt; }
figure { margin: 9pt 0 11pt; break-inside: avoid; page-break-inside: avoid; }
figure img { margin: 0 auto 3pt; }
figcaption { font-size: 8.3pt; line-height: 1.4; text-align: left; color: #1a1a1a; }
figcaption em { font-style: normal; }
.katex { font-size: 1.0em; }
.katex-display { margin: 7pt 0 8pt; break-inside: avoid; }
.katex-display > .katex { font-size: 1.02em; }
`;

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const html = `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>${esc(title)}</title>
<link rel="stylesheet" href="katex/katex.min.css">
<style>${css}</style></head><body>
<h1>${esc(title)}</h1>
${subtitle ? `<div class="subtitle">${esc(subtitle)}</div>` : ''}
<hr class="title-rule">
${bodyHtml}
</body></html>`;

fs.writeFileSync(OUT, html, 'utf8');
console.log('wrote', OUT, html.length, 'bytes');
