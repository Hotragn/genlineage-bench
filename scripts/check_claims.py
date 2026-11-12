"""Claims checker for the merged paper. Steps:
1. scripts/paper_stats.py recomputes every result number from raw transcripts (results/runs, runs_ladder, runs_real) and
   released artifacts (inthewild, prevalence, realrepo, lineage_graph, bench validation) into results/summary/paper_stats.json.
2. paper/writeup_template.md is rendered ({{p:key}} placeholders) and must equal paper/writeup.md byte for byte.
3. scripts/paper_audit.py: word limit, forbidden dashes, every numeric literal outside placeholders is allow-listed, figures exist.
4. scripts/cross_check.py: per-cell counts agree with two independently written analyses (scripts/analyze.py and the analysis behind results/crosscheck).
Usage: python scripts/check_claims.py [--no-recompute]"""
import difflib, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from claims import ROOT
if "--no-recompute" not in sys.argv:
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "paper_stats.py")], check=True, stdout=subprocess.DEVNULL)
from render_writeup import render
tpl = open(os.path.join(ROOT, "paper", "writeup_template.md")).read(); shipped = open(os.path.join(ROOT, "paper", "writeup.md")).read()
fresh = render(tpl); n = len(re.findall(r"\{\{p:[^}]+\}\}", tpl)); keys = len(set(re.findall(r"\{\{p:([^}]+)\}\}", tpl)))
if fresh != shipped:
    print("CLAIMS MISMATCH:"); sys.stdout.writelines(difflib.unified_diff(shipped.splitlines(True), fresh.splitlines(True), "shipped", "recomputed")); sys.exit(1)
print(f"CLAIMS OK: {n}/{n} placeholders ({keys} distinct claims) in writeup.md match values recomputed from raw logs and artifacts")
rc = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "paper_audit.py")]).returncode
rc |= subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "cross_check.py")]).returncode
sys.exit(rc)
