"""Aggregate mined AIDev rows into PR-level and PR-file-level statistics, per agent.
Run: venv/bin/python -I build/inthewild/analyze.py <aidev_dir> <out_dir>
Inputs: out/flagged.jsonl.gz, out/pr_files.json.gz, out/all_pr_ids.json.gz (from mine.py), pull_request.parquet.
Outputs: out/summary.json, out/pairs.csv.gz (one row per PR x generated file), out/audit_candidates.csv (seeded sample).
"""
import csv, gzip, json, os, random, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from gendetect import is_plausible_source, path_rule

D, OUT = sys.argv[1], sys.argv[2]
SEED = 20261110
EDIT_STATUSES = {"modified", "renamed"}

pr = pd.read_parquet(os.path.join(D, "pull_request.parquet"), columns=["id", "agent", "state", "merged_at", "html_url", "repo_url"])
all_ids = set(json.load(gzip.open(os.path.join(OUT, "all_pr_ids.json.gz"), "rt")))
pr = pr[pr.id.isin(all_ids)].copy()
pr["merged"] = pr.merged_at.notna()
meta = pr.set_index("id")[["agent", "state", "merged", "html_url", "repo_url"]].to_dict("index")
pr_files = {int(k): v for k, v in json.load(gzip.open(os.path.join(OUT, "pr_files.json.gz"), "rt")).items()}

# ---- aggregate flagged rows to (pr, file) ----
pairs = {}          # (pr, file) -> dict
lock_prs = set()
with gzip.open(os.path.join(OUT, "flagged.jsonl.gz"), "rt") as fi:
    for l in fi:
        r = json.loads(l)
        if r["merge"] or r["pr_id"] not in meta: continue
        if r["lock"]: lock_prs.add(r["pr_id"]); continue
        strong = r["hdr"] == "strong"
        if not (r["path_rule"] or strong): continue
        k = (r["pr_id"], r["file"]); p = pairs.get(k)
        if p is None:
            p = pairs[k] = dict(pr=r["pr_id"], file=r["file"], path_rule=r["path_rule"], hdr_strong=False, hdr_weak=False,
                                cov_complete=False, statuses=set(), add=0.0, dele=0.0, shas=[], patch_null=False)
        p["hdr_strong"] |= strong; p["hdr_weak"] |= r["hdr"] == "weak"; p["cov_complete"] |= r["hdr_cov"] == "complete"
        p["statuses"].add(r["status"]); p["add"] += r["add"] or 0; p["dele"] += r["dele"] or 0; p["shas"].append(r["sha"])
        p["patch_null"] |= r["patch_null"]

for (pid, f), p in pairs.items():
    files = pr_files.get(pid, {})
    srcs = [g for g in files if g != f and files[g] != "removed" and is_plausible_source(g, f)]
    p["source_in_pr"] = bool(srcs); p["sources"] = srcs[:5]
    p["edited"] = bool(p["statuses"] & EDIT_STATUSES) and (p["add"] + p["dele"]) > 0
    p["method"] = "both" if (p["path_rule"] and p["hdr_strong"]) else ("path" if p["path_rule"] else "header")
    # header status of path-detected files, from patch text only
    p["hdr_status_patch"] = "present" if p["hdr_strong"] else ("absent" if p["cov_complete"] else "unknown")
    p["n_pr_files"] = len(files)

# ---- per-agent tables ----
def rate(a, b): return round(a / b, 4) if b else None
agents = sorted(set(v["agent"] for v in meta.values()))
by_pr = collections.defaultdict(list)
for p in pairs.values(): by_pr[p["pr"]].append(p)

def pr_sets(sel):
    """sel: predicate over pair -> set of PRs having >=1 such pair"""
    return {pid for pid, ps in by_pr.items() if any(sel(p) for p in ps)}

S = {
  "touch_gen_any": pr_sets(lambda p: True),
  "touch_gen_path": pr_sets(lambda p: p["path_rule"] is not None),
  "touch_gen_header": pr_sets(lambda p: p["hdr_strong"]),
  "edit_gen_any": pr_sets(lambda p: p["edited"]),
  "edit_gen_nosrc": pr_sets(lambda p: p["edited"] and not p["source_in_pr"]),
  "edit_gen_nosrc_path": pr_sets(lambda p: p["edited"] and not p["source_in_pr"] and p["path_rule"] is not None),
  "edit_gen_nosrc_header": pr_sets(lambda p: p["edited"] and not p["source_in_pr"] and p["hdr_strong"]),
}
S["touch_gen_all_with_src"] = {pid for pid in S["touch_gen_any"] if all(p["source_in_pr"] for p in by_pr[pid])}
S["edit_gen_all_with_src"] = {pid for pid in S["edit_gen_any"] if all(p["source_in_pr"] for p in by_pr[pid] if p["edited"])}

def merge_stats(ids):
    ids = [i for i in ids if i in meta]; m = sum(meta[i]["merged"] for i in ids)
    closed = [i for i in ids if meta[i]["state"] == "closed"]
    mc = sum(meta[i]["merged"] for i in closed)
    return dict(n=len(ids), merged=m, merge_rate=rate(m, len(ids)), n_closed=len(closed), merge_rate_closed=rate(mc, len(closed)))

summary = {"seed": SEED, "denominator_note": "PRs in AIDev-pop pull_request.parquet (v5) with >=1 row in pr_commit_details; merge commits excluded",
           "per_agent": {}, "all": {}}
for ag in agents + ["ALL"]:
    ids = {i for i, v in meta.items() if ag == "ALL" or v["agent"] == ag}
    row = {"prs_with_file_data": len(ids), "prs_touching_lockfile": len(ids & lock_prs)}
    for k, s in S.items(): row[k] = len(ids & s)
    row["rate_touch_gen_any"] = rate(row["touch_gen_any"], len(ids))
    row["rate_edit_gen_any"] = rate(row["edit_gen_any"], len(ids))
    row["rate_nosrc_among_edit_gen"] = rate(row["edit_gen_nosrc"], row["edit_gen_any"])
    row["rate_all_with_src_among_touch_gen"] = rate(row["touch_gen_all_with_src"], row["touch_gen_any"])
    row["rate_all_with_src_among_edit_gen"] = rate(row["edit_gen_all_with_src"], row["edit_gen_any"])
    row["merge_nosrc"] = merge_stats(ids & S["edit_gen_nosrc"])
    row["merge_edit_gen_with_src"] = merge_stats(ids & (S["edit_gen_any"] - S["edit_gen_nosrc"]))
    row["merge_no_gen"] = merge_stats(ids - S["touch_gen_any"])
    row["merge_all"] = merge_stats(ids)
    summary["per_agent"][ag] = row

# ---- pair-level stats ----
P = list(pairs.values())
pl = collections.Counter()
for p in P:
    pl["pairs"] += 1; pl["pairs_" + p["method"]] += 1
    if p["edited"]: pl["edited_pairs"] += 1; pl["edited_pairs_with_src"] += p["source_in_pr"]
    if p["path_rule"]:
        pl["path_pairs"] += 1; pl["path_pairs_hdr_" + p["hdr_status_patch"]] += 1
summary["pairs"] = dict(pl)
summary["path_rule_counts"] = dict(collections.Counter(p["path_rule"] for p in P if p["path_rule"]).most_common())
summary["path_rule_edited_nosrc"] = dict(collections.Counter(p["path_rule"] or "header_only" for p in P if p["edited"] and not p["source_in_pr"]).most_common())
summary["distinct_repos_edit_gen_nosrc"] = len({meta[p["pr"]]["repo_url"] for p in P if p["edited"] and not p["source_in_pr"]})
summary["distinct_repos_edit_gen"] = len({meta[p["pr"]]["repo_url"] for p in P if p["edited"]})

with gzip.open(os.path.join(OUT, "pairs.csv.gz"), "wt", newline="") as fo:
    w = csv.writer(fo); w.writerow(["pr_id", "agent", "html_url", "file", "method", "path_rule", "hdr_status_patch", "statuses", "add", "dele", "edited", "source_in_pr", "sources", "n_pr_files", "merged", "last_sha"])
    for p in P:
        m = meta[p["pr"]]
        w.writerow([p["pr"], m["agent"], m["html_url"], p["file"], p["method"], p["path_rule"] or "", p["hdr_status_patch"], "|".join(sorted(p["statuses"])),
                    int(p["add"]), int(p["dele"]), int(p["edited"]), int(p["source_in_pr"]), "|".join(p["sources"]), p["n_pr_files"], int(m["merged"]), p["shas"][-1]])

# ---- seeded samples ----
rng = random.Random(SEED)
nosrc = sorted([p for p in P if p["edited"] and not p["source_in_pr"]], key=lambda p: (p["pr"], p["file"]))
# one pair per PR so a single huge PR cannot dominate the sample
first = {}
for p in nosrc: first.setdefault(p["pr"], p)
audit = rng.sample(sorted(first.values(), key=lambda p: (p["pr"], p["file"])), 30)
with open(os.path.join(OUT, "audit_candidates.csv"), "w", newline="") as fo:
    w = csv.writer(fo); w.writerow(["pr_id", "agent", "html_url", "file", "method", "path_rule", "hdr_status_patch", "add", "dele", "n_pr_files", "merged", "last_sha"])
    for p in audit:
        m = meta[p["pr"]]; w.writerow([p["pr"], m["agent"], m["html_url"], p["file"], p["method"], p["path_rule"] or "", p["hdr_status_patch"], int(p["add"]), int(p["dele"]), p["n_pr_files"], int(m["merged"]), p["shas"][-1]])
# header-check sample: path-detected pairs whose header status is unknown from the patch (one per PR), for GitHub content fetch
rng2 = random.Random(SEED + 1)
path_pairs = {}
for p in sorted([p for p in P if p["path_rule"]], key=lambda p: (p["pr"], p["file"])): path_pairs.setdefault(p["pr"], p)
hs = rng2.sample(sorted(path_pairs.values(), key=lambda p: (p["pr"], p["file"])), min(200, len(path_pairs)))
with open(os.path.join(OUT, "header_sample.csv"), "w", newline="") as fo:
    w = csv.writer(fo); w.writerow(["pr_id", "agent", "html_url", "repo_url", "file", "path_rule", "hdr_status_patch", "last_sha", "statuses"])
    for p in hs:
        m = meta[p["pr"]]; w.writerow([p["pr"], m["agent"], m["html_url"], m["repo_url"], p["file"], p["path_rule"], p["hdr_status_patch"], p["shas"][-1], "|".join(sorted(p["statuses"]))])
summary["audit_population_prs"] = len(first); summary["header_sample_population_prs"] = len(path_pairs)
json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
print(json.dumps(summary, indent=1))
