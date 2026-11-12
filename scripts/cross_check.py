"""Independent cross-check: per (model, condition) counts on regen+mixed tasks, seeds 1-2, from paper_stats.py versus
(a) results/summary/rows.json written by scripts/analyze.py (main pipeline) and (b) results/crosscheck/lab_out_s12_runs.csv
written by a separately developed analysis script during the study. Exit 1 on any disagreement."""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paper_stats as S
ROOT = S.ROOT; bad = 0; n = 0
mine = {}
for m in S.MODELS:
    for c in sorted({r["c"] for r in S.rows if r["m"] == m}):
        rs = S.sel(m, c); al = S.sel(m, c, kinds=None)
        mine[(m, c)] = dict(n=len(rs), imm=sum(r["imm"] for r in rs), dur=sum(r["dur"] for r in rs), strict=sum(r["strict"] for r in rs), tt=sum(r["tt"] for r in al))
A = json.load(open(os.path.join(ROOT, "results", "summary", "rows.json")))
L = list(csv.DictReader(open(os.path.join(ROOT, "results", "crosscheck", "lab_out_s12_runs.csv"))))
for (m, c), v in mine.items():
    ra = [r for r in A if r["model"] == m and r["cond"] == c and int(r["seed"]) in (1, 2)]
    a = dict(n=sum(1 for r in ra if r["kind"] in S.RM), imm=sum(r["imm"] for r in ra if r["kind"] in S.RM), dur=sum(r["dur"] for r in ra if r["kind"] in S.RM),
             strict=sum(r["strict"] for r in ra if r["kind"] in S.RM), tt=sum(r["tamper"] for r in ra))
    rl = [r for r in L if r["tag"] == m and r["cond"] == c]
    l = dict(n=sum(1 for r in rl if r["kind"] in S.RM), imm=sum(int(r["imm"]) for r in rl if r["kind"] in S.RM),
             dur=sum(int(r["post"]) and not int(r["tt"]) for r in rl if r["kind"] in S.RM),
             strict=sum(int(r["imm"]) and int(r["post"]) and not int(r["tt"]) for r in rl if r["kind"] in S.RM), tt=sum(int(r["tt"]) for r in rl))
    for k in v:
        n += 2
        if v[k] != a[k]: bad += 1; print("MISMATCH main", m, c, k, v[k], a[k])
        if v[k] != l[k]: bad += 1; print("MISMATCH lab", m, c, k, v[k], l[k])
print(f"CROSS-CHECK {'OK' if not bad else 'FAILED'}: {n - bad}/{n} cell counts agree across three analysis codes"); sys.exit(1 if bad else 0)
