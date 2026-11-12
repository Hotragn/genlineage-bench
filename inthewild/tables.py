"""Render out/summary.json as markdown tables (pasted into README.md). Run: venv/bin/python -I build/inthewild/tables.py out/"""
import json, os, sys
s = json.load(open(os.path.join(sys.argv[1], "summary.json")))
def pct(a, b): return f"{100*a/b:.1f}%" if b else "n/a"
print("| Agent | PRs with file data | PRs touching lockfile | PRs touching generated (a or b) | PRs editing generated | ...without plausible source | ...with source for every edited gen file | merge rate: edit-gen w/o source | merge rate: edit-gen with source | merge rate: no generated file |")
print("|---|---|---|---|---|---|---|---|---|---|")
for a, r in s["per_agent"].items():
    m1, m2, m3 = r["merge_nosrc"], r["merge_edit_gen_with_src"], r["merge_no_gen"]
    print(f"| {a} | {r['prs_with_file_data']:,} | {r['prs_touching_lockfile']:,} ({pct(r['prs_touching_lockfile'], r['prs_with_file_data'])}) | {r['touch_gen_any']:,} ({pct(r['touch_gen_any'], r['prs_with_file_data'])}) | "
          f"{r['edit_gen_any']:,} ({pct(r['edit_gen_any'], r['prs_with_file_data'])}) | {r['edit_gen_nosrc']:,} ({pct(r['edit_gen_nosrc'], r['edit_gen_any'])} of editing) | "
          f"{r['edit_gen_all_with_src']:,} ({pct(r['edit_gen_all_with_src'], r['edit_gen_any'])}) | {pct(m1['merged'], m1['n'])} (n={m1['n']:,}) | {pct(m2['merged'], m2['n'])} (n={m2['n']:,}) | {pct(m3['merged'], m3['n'])} (n={m3['n']:,}) |")
print()
print("| Agent | touch gen: path (a) | touch gen: header (b) | touch gen: all touched gen files have a source in PR |")
print("|---|---|---|---|")
for a, r in s["per_agent"].items():
    print(f"| {a} | {r['touch_gen_path']:,} | {r['touch_gen_header']:,} | {r['touch_gen_all_with_src']:,} of {r['touch_gen_any']:,} ({pct(r['touch_gen_all_with_src'], r['touch_gen_any'])}) |")
print(); print("pairs:", json.dumps(s["pairs"])); print("path rules (PR-file pairs):", json.dumps(s["path_rule_counts"]))
print("edited w/o source by rule:", json.dumps(s["path_rule_edited_nosrc"])); print("repos edit-gen:", s["distinct_repos_edit_gen"], "repos edit-gen w/o src:", s["distinct_repos_edit_gen_nosrc"])
