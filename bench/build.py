"""Build GenLineage-Bench task repositories and validate the durability oracle on every task.

Usage: python bench/build.py            # builds bench/tasks/<id>/{repo,task.json} and writes bench/validation.json
Deterministic: generated files are produced by running the real generators on the buggy inputs.
"""
import json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from bench.families import TASKS
from genlineage.env import sh
from genlineage.score import apply_patch, score, digest

OUT = os.path.join(HERE, "tasks")

def write(base, rel, s):
    p = os.path.join(base, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f: f.write(s)

def build_one(t):
    root = os.path.join(OUT, t["id"]); repo = os.path.join(root, "repo")
    shutil.rmtree(root, ignore_errors=True); os.makedirs(repo)
    for rel, s in t["files"].items(): write(repo, rel, s)
    for g in t["generated"]:  # generated dirs must exist (protoc does not create package dirs' __init__)
        os.makedirs(os.path.dirname(os.path.join(repo, g)), exist_ok=True)
    if t.get("user_regions"):
        stub = "".join(f"    # BEGIN USER CODE {k}\n{v}    # END USER CODE {k}\n" for k, v in t["user_regions"].items())
        write(repo, t["generated"][0], stub)
    before = digest(repo)
    rc, out = sh(t["gen_cmd"], repo)
    assert rc == 0, (t["id"], out)
    after = digest(repo)
    produced = sorted(k for k in after if before.get(k) != after.get(k))
    assert produced == sorted(t["generated"]), (t["id"], produced, t["generated"])
    meta = {k: v for k, v in t.items() if k not in ("files", "user_regions")}
    meta["test_hashes"] = {k: v for k, v in digest(repo).items() if k.startswith("tests/")}
    meta["build_files"] = [f for f in ("Makefile",) if os.path.exists(os.path.join(repo, f))]
    # reference outputs: regenerate after the reference fix; noise = lines that differ across two regenerations
    ref = os.path.join(root, "_ref"); shutil.rmtree(ref, ignore_errors=True); shutil.copytree(repo, ref)
    apply_patch(ref, t["ref_fix"]); sh(t["gen_cmd"], ref); a = {g: open(os.path.join(ref, g)).read() for g in t["generated"]}
    sh(t["gen_cmd"], ref); b = {g: open(os.path.join(ref, g)).read() for g in t["generated"]}
    os.makedirs(os.path.join(root, "ref_outputs"), exist_ok=True)
    meta["noise_lines"] = {}
    for g in t["generated"]:
        open(os.path.join(root, "ref_outputs", g.replace("/", "__")), "w").write(a[g])
        la, lb = a[g].splitlines(), b[g].splitlines()
        meta["noise_lines"][g] = [i for i, (x, y) in enumerate(zip(la, lb)) if x != y]
    shutil.rmtree(ref, ignore_errors=True)
    json.dump(meta, open(os.path.join(root, "task.json"), "w"), indent=1)
    return meta, repo

def validate(meta, repo):
    row = {"task": meta["id"], "kind": meta["kind"]}
    work_root = os.path.join(HERE, "_validate", meta["id"]); shutil.rmtree(work_root, ignore_errors=True)
    # determinism: regenerating the untouched repo reproduces the committed generated files byte for byte
    w = os.path.join(work_root, "regen"); shutil.copytree(repo, w)
    d0 = digest(w); sh(meta["gen_cmd"], w); d1 = digest(w)
    row["deterministic_regen"] = all(d0[g] == d1.get(g) for g in meta["generated"])
    variants = [("none", None), ("ref_fix", meta["ref_fix"])]
    if meta.get("gen_only_fix"): variants.append(("gen_only_fix", meta["gen_only_fix"]))
    for kind, patch in variants:
        w = os.path.join(work_root, kind); shutil.copytree(repo, w)
        if patch:
            apply_patch(w, patch)
            if kind == "ref_fix" and meta["kind"] in ("regen", "mixed"): sh(meta["gen_cmd"], w)
        s = score(meta, w, repo)
        row[kind] = [s["immediate_pass"], s["durable_pass"]]
        row[kind + "_root_cause"] = s["root_cause_fixed"]
    exp = {"none": [False, False], "ref_fix": [True, True], "gen_only_fix": [True, False]}
    row["ok"] = row.get("ref_fix_root_cause", False) and (row["deterministic_regen"] or meta.get("regen_nondeterministic", False)) and all(row[k] == exp[k] for k in exp if k in row)
    shutil.rmtree(work_root, ignore_errors=True)
    return row

def validate_existing():
    rows = []
    for t in TASKS:
        meta = json.load(open(os.path.join(OUT, t["id"], "task.json")))
        rows.append(validate(meta, os.path.join(OUT, t["id"], "repo")))
    bad = [r["task"] for r in rows if not r["ok"]]
    print(json.dumps(rows)); print("VALIDATE ALL OK" if not bad else f"VALIDATE FAILED: {bad}")

if __name__ == "__main__":
    if "--validate-only" in sys.argv: validate_existing(); sys.exit()
    only = sys.argv[1:]
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for t in TASKS:
        if only and t["id"] not in only: continue
        meta, repo = build_one(t)
        r = validate(meta, repo); rows.append(r); print(json.dumps(r), flush=True)
    index = {t["id"]: {k: t[k] for k in ("family", "split", "kind", "fix_locus", "header", "agents_md")} for t in TASKS}
    json.dump(index, open(os.path.join(OUT, "index.json"), "w"), indent=1)
    if not only: json.dump(rows, open(os.path.join(HERE, "validation.json"), "w"), indent=1)
    bad = [r["task"] for r in rows if not r["ok"]]
    print("ALL OK" if not bad else f"FAILED: {bad}")
