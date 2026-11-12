"""Render paper/writeup.md and its figures to paper/GenLineage_paper.pdf.
Needs: pip install markdown weasyprint (WeasyPrint also needs Pango from the system).
Usage: python scripts/make_pdf.py [out.pdf]"""
import os, re, sys
import markdown
from weasyprint import HTML

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPER = os.path.join(ROOT, "paper")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PAPER, "GenLineage_paper.pdf")
REPO = "https://github.com/Hotragn/genlineage-bench"

CSS = """
@page { size: Letter; margin: 2.2cm 2.3cm 2.2cm 2.3cm;
        @bottom-center { content: counter(page); font: 9pt 'Source Serif Pro', serif; color: #555; } }
html { font-family: 'Source Serif Pro', 'Noto Serif', serif; font-size: 10.5pt; line-height: 1.38; color: #1a1a1a; }
body { margin: 0; }
h1 { font-size: 20pt; text-align: center; margin: 0 0 4pt 0; font-weight: 600; }
.subtitle { text-align: center; font-size: 12pt; font-style: italic; margin: 0 0 10pt 0; }
.byline { text-align: center; font-size: 10.5pt; margin: 0 0 2pt 0; }
.venue { text-align: center; font-size: 9.5pt; color: #444; margin: 0 0 16pt 0; }
.venue a { color: #444; }
h2 { font-size: 12.5pt; margin: 16pt 0 5pt 0; font-weight: 600; page-break-after: avoid; }
h3 { font-size: 11pt; margin: 11pt 0 4pt 0; font-weight: 600; page-break-after: avoid; }
p { margin: 0 0 6pt 0; text-align: justify; hyphens: auto; }
ul { margin: 0 0 6pt 0; padding-left: 16pt; }
li { margin: 0 0 2pt 0; text-align: justify; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 8.6pt; }
a { color: #1f4e8c; text-decoration: none; }
.abstract { margin: 0 1.2cm 10pt 1.2cm; font-size: 9.8pt; }
.abstract h2 { text-align: center; font-size: 11pt; margin: 0 0 4pt 0; }
figure { margin: 10pt 0 10pt 0; text-align: center; page-break-inside: avoid; }
figure img { width: 100%; height: auto; }
figure.tall img { width: 92%; }
figcaption { font-size: 9pt; margin-top: 4pt; text-align: center; }
table { border-collapse: collapse; margin: 4pt auto 10pt auto; font-size: 8.8pt; page-break-inside: avoid;
        border-top: 1.2pt solid #222; border-bottom: 1.2pt solid #222; }
thead th { border-bottom: 0.7pt solid #222; font-weight: 600; }
th, td { padding: 2.2pt 7pt; text-align: center; }
td:first-child, th:first-child { text-align: left; }
.tcap { font-size: 9pt; text-align: justify; margin: 8pt 0 2pt 0; page-break-after: avoid; }
.refs li { font-size: 8.6pt; text-align: left; overflow-wrap: anywhere; margin-bottom: 2.5pt; }
.refs ul { list-style: none; padding-left: 0; }
"""

def build_html():
    md = open(os.path.join(PAPER, "writeup.md"), encoding="utf-8").read()
    title, rest = md.split("\n", 1)
    title = title.lstrip("# ").strip()
    sub_m = re.match(r"\*(.+?)\*\n", rest)
    subtitle = sub_m.group(1) if sub_m else ""
    rest = rest[sub_m.end():] if sub_m else rest
    # python-markdown needs a blank line before a list that follows a paragraph
    rest = re.sub(r"(?m)^(?![-*] |\s*$)(.+)\n(- )", r"\1\n\n\2", rest)
    body = markdown.markdown(rest, extensions=["tables", "sane_lists"])
    # figure image followed by its caption paragraph -> <figure>
    body = re.sub(r'<p><img alt="([^"]*)" src="([^"]+)" />\s*(?:</p>\s*<p>)?<em>(.*?)</em></p>',
                  lambda m: f'<figure class="{"tall" if "overview" in m.group(2) else ""}"><img alt="{m.group(1)}" src="{m.group(2)}" /><figcaption>{m.group(3)}</figcaption></figure>', body, flags=re.S)
    body = re.sub(r'<p><img alt="([^"]*)" src="([^"]+)" /></p>', r'<figure><img alt="\1" src="\2" /></figure>', body)
    # table captions ("**Table N.** ...") get their own style
    body = re.sub(r"<p><strong>(Table \d+\.)</strong>", r'<p class="tcap"><strong>\1</strong>', body)
    # abstract block
    body = re.sub(r"(<h2>Abstract</h2>\s*<p>.*?</p>)", r'<div class="abstract">\1</div>', body, count=1, flags=re.S)
    # references: smaller, clickable links
    head, _, refs = body.partition("<h2>References</h2>")
    if refs:
        refs = re.sub(r"(?<![\"'>])(https?://[^\s<]+?)([.,;]?)(?=\s|</li>|<)", r'<a href="\1">\1</a>\2', refs)
        body = head + '<h2>References</h2><div class="refs">' + refs + "</div>"
    # bare URLs in the body (Section 10)
    body = re.sub(r"(?<![\"'>=])(https?://[^\s<)]+[^\s<).,;])", r'<a href="\1">\1</a>', head) + body[len(head):] if refs else body
    body = body.replace("<p>Code, tasks", "<p style=\"text-align: left\">Code, tasks")  # long URLs justify badly
    front = (f"<h1>{title}</h1><p class='subtitle'>{subtitle}</p>"
             "<p class='byline'>Hotragn Pettugani</p>"
             f"<p class='venue'>Kaggle Gemma 4 Developer Agent Paper Track, 2026. Code and data: <a href='{REPO}'>{REPO.replace('https://', '')}</a></p>")
    return f"<!doctype html><html><head><meta charset='utf-8'><meta name='author' content='Hotragn Pettugani'><title>{title}</title><style>{CSS}</style></head><body>{front}{body}</body></html>"

if __name__ == "__main__":
    HTML(string=build_html(), base_url=PAPER + "/").write_pdf(OUT, pdf_variant=None)
    print("wrote", OUT)
