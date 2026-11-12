"""Render paper/writeup_template.md -> writeup.md, replacing {{c:key}} with values from claims.py. Fails on unknown keys."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from claims import build, ROOT
def refs(tpl):
    bib = open(os.path.join(ROOT, "paper", "refs.bib")).read(); ents = {}
    for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", bib, re.S):
        f = dict(re.findall(r"(\w+) = \{(.*?)\},?\n", m.group(3) + "\n"))
        a = f.get("author", "").split(" and "); first = a[0].split(",")[0].strip("{}")
        au = first + (" et al" if len(a) > 1 else "")
        where = f.get("booktitle") or f.get("journal") or f.get("howpublished", "")
        arx = re.search(r"arXiv(?: preprint)? (\d{4}\.\d{5})", f.get("howpublished", ""))
        link = ("https://doi.org/" + f["doi"]) if "doi" in f else f.get("url", ("https://arxiv.org/abs/" + arx.group(1)) if arx else "")
        t = f.get('title', '').replace('{', '').replace('}', '').replace('\\"', '"'); t = t if t.endswith(("?", "!")) else t + "."
        ents[m.group(2).strip()] = f"{au}. {t} {where} {f.get('year', '')}. {link}".strip()  # references do not count toward the word limit
    cited = []
    for grp in re.findall(r"\[([a-z0-9_; ]+)\]", tpl):
        for k in grp.split(";"):
            k = k.strip()
            if k in ents and k not in cited: cited.append(k)
    unknown = sorted({k.strip() for grp in re.findall(r"\[([a-z0-9_; ]+)\]", tpl) for k in grp.split(";") if re.match(r"^[a-z]+\d{4}\w+$", k.strip()) and k.strip() not in ents})
    if unknown: raise SystemExit(f"citations missing from refs.bib: {unknown}")
    return "\n".join(f"- [{k}] {ents[k]}" for k in sorted(cited))
def render(tpl):
    if "{{REFS}}" in tpl: tpl = tpl.replace("{{REFS}}", refs(tpl))
    PS = json.load(open(os.path.join(ROOT, "results", "summary", "paper_stats.json")))
    pm = sorted({k for k in re.findall(r"\{\{p:([^}]+)\}\}", tpl) if k not in PS})
    if pm: raise SystemExit(f"unknown paper_stats keys: {pm}")
    tpl = re.sub(r"\{\{p:([^}]+)\}\}", lambda m: PS[m.group(1)], tpl)
    C = build(); missing = sorted({k for k in re.findall(r"\{\{c:([^}]+)\}\}", tpl) if k not in C})
    if missing: raise SystemExit(f"unknown claim keys: {missing}")
    return re.sub(r"\{\{c:([^}]+)\}\}", lambda m: C[m.group(1)], tpl)
if __name__ == "__main__":
    tpl = open(os.path.join(ROOT, "paper", "writeup_template.md")).read(); out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "paper", "writeup.md")
    open(out, "w").write(render(tpl)); print("wrote", out)
