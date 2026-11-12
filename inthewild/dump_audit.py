"""Dump patches (non-merge commits) and the PR file list for the seeded audit sample, for manual review.
Run: venv/bin/python -I build/inthewild/dump_audit.py out/ > out/audit_patches.txt"""
import csv, gzip, json, os, sys
OUT = sys.argv[1]
rows = list(csv.DictReader(open(os.path.join(OUT, "audit_candidates.csv"))))
want = {(int(r["pr_id"]), r["file"]) for r in rows}; got = {}
with gzip.open(os.path.join(OUT, "flagged.jsonl.gz"), "rt") as fi:
    for l in fi:
        r = json.loads(l)
        if (r["pr_id"], r["file"]) in want and not r["merge"]: got.setdefault((r["pr_id"], r["file"]), []).append(r)
files = json.load(gzip.open(os.path.join(OUT, "pr_files.json.gz"), "rt"))
for i, r in enumerate(rows):
    k = (int(r["pr_id"]), r["file"]); fl = files.get(r["pr_id"], {})
    print(f"===== #{i+1} {r['agent']} {r['html_url']} merged={r['merged']}\nFILE {r['file']} method={r['method']} rule={r['path_rule']} hdr_patch={r['hdr_status_patch']} +{r['add']} -{r['dele']}")
    print("PR FILES (%d): %s" % (len(fl), ", ".join(sorted(fl))[:1500]))
    for x in got.get(k, []):
        print(f"--- commit {x['sha'][:10]} status={x['status']}"); print("\n".join((x.get("patch") or "<no patch>").split("\n")[:45]))
