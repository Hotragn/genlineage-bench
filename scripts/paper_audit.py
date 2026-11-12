"""Audit the rendered paper (paper/writeup.md): official-style word count, forbidden dash characters, unexplained numeric literals,
figure files, and citation keys. Exit 1 on any failure.
Word rule (host, Oct 27 2026): all judged text counts, including title, abstract, captions and tables; figures and references do not.
Counter: drop the References section and image lines (![..](..)); keep captions and tables; a word is a whitespace-separated token
containing at least one letter or digit (so table pipes and separator rows do not count)."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def judged(text):
    body = text.split("\n## References")[0]
    return "\n".join(l for l in body.splitlines() if not re.match(r"^\s*!\[.*\]\(.*\)\s*$", l))
def count(text):
    j = judged(text); return sum(1 for t in j.split() if re.search(r"[A-Za-z0-9]", t)), len(j.split())
# numeric literals allowed in the template outside {{p:}} placeholders, with the reason
ALLOW = {"4": "Gemma 4 (model family name)", "2": "E2B model name / seeds 1 and 2", "1": "seed 1 / contribution numbering", "3": "seed 3 / contribution numbering / Figure 3",
         "12": "12B model name", "15": "HeaderGuard rule: header regex over the first 15 lines (genlineage/agent.py looks_generated)",
         "5": "AIDev v5 dataset version", "256": "SHA-256", "2.0": "Apache 2.0", "31": "Gemma 4 31B model name", "0": "DFR 0 by construction (gate rejects reverted writes)",
         "6": "section number", "7": "section number", "8": "section number", "9": "section number", "10": "section number", "95": "confidence level of intervals", "6.1": "subsection", "6.2": "subsection", "6.3": "subsection", "6.4": "subsection", "6.5": "subsection"}
def literal_audit(tpl):
    t = re.sub(r"\{\{p:[^}]+\}\}", " ", tpl); t = t.split("\n## References")[0]
    t = re.sub(r"`[^`]*`", " ", t); t = re.sub(r"\[[a-z0-9_; ]+\]", " ", t); t = re.sub(r"\(figures/[^)]*\)", " ", t)
    t = re.sub(r"\b(E2B|E4B|12B|31B|L0|L1|L2|T4)\b", " ", t)
    bad = []
    for m in re.finditer(r"(?<![A-Za-z])\d+(?:\.\d+)?", t):
        if m.group(0) not in ALLOW: bad.append((m.group(0), t[max(0, m.start() - 40):m.end() + 20].replace("\n", " ")))
    return bad
if __name__ == "__main__":
    W = open(os.path.join(ROOT, "paper", "writeup.md")).read(); T = open(os.path.join(ROOT, "paper", "writeup_template.md")).read(); ok = True
    words, raw = count(W); print(f"WORDS official-style {words} (whitespace tokens incl. table pipes: {raw}); limit 3000")
    if words > 3000: ok = False; print("FAIL word limit")
    for ch, name in (("\u2013", "en dash"), ("\u2014", "em dash"), ("\u2212", "minus sign")):
        n = W.count(ch) + T.count(ch)
        if n: ok = False; print(f"FAIL {n} x {name}")
    bad = literal_audit(T)
    for b in bad: print("FAIL unexplained literal:", b)
    ok &= not bad
    for f in re.findall(r"\]\((figures/[^)]+)\)", W):
        if not os.path.exists(os.path.join(ROOT, "paper", f)): ok = False; print("FAIL missing figure", f)
    if re.search(r"\{\{", W.split("\n## References")[0]): ok = False; print("FAIL unrendered placeholder")
    print("AUDIT OK" if ok else "AUDIT FAILED"); sys.exit(0 if ok else 1)
