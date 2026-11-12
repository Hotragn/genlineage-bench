"""Component A (counterfactual lineage inference) on real open-source repositories.

For each repo we run the repository's own documented regeneration command in a sandbox copy
(tests/, docs/ and .git excluded), detect written files by mtime, measure run-to-run noise, and
ablate candidate inputs one at a time. Ground truth for outputs and declared inputs comes from the
repo itself (Makefile rule, tox env, generator source); see SPECS.
"""
import json, os, random, re, shutil, subprocess, sys, tempfile, time
ROOT = os.environ.get("REALREPOS", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".realrepos"))
IGN = shutil.ignore_patterns(".git", "tests", "test", "docs", "doc", "__pycache__", "*.pyc", "node_modules", "vendor", "benchmarks", "assets", "imgs")
PY = sys.executable
SPECS = {
 "aiohttp": dict(cmd=f"{PY} tools/gen.py", cwd=".",
     gt_out=["aiohttp/_find_header.c", "aiohttp/_headers.pxi"],
     declared_in=["aiohttp/hdrs.py", "tools/gen.py"],
     source="Makefile rule 'aiohttp/_find_header.c: $(call to-hash,aiohttp/hdrs.py ./tools/gen.py)'; .pxi named only in a comment"),
 "pygments": dict(cmd=f"{PY} scripts/gen_mapfiles.py", cwd=".",
     gt_out=["pygments/lexers/_mapping.py", "pygments/formatters/_mapping.py", "pygments/styles/_mapping.py"],
     declared_in=["scripts/gen_mapfiles.py"], declared_glob=r"^pygments/(lexers|formatters|styles)/(?!_mapping)[^/]+\.py$",
     source="tox env 'mapfiles'; generator walks pygments/{lexers,formatters,styles}/*.py"),
 "rich": dict(cmd=f"{PY} make_width_tables.py", cwd="tools", gt_out_glob=r"^rich/_unicode_data/[^/]+\.py$",
     gt_out=[], declared_in=["tools/make_width_tables.py"], declared_glob=r"^rich/cells\.py$",
     source="tools/make_width_tables.py header; writes rich/_unicode_data/*.py from the wcwidth package", pythonpath="."),
 "grpc": dict(cmd=f"{PY} -m grpc_tools.protoc -I../../protos --python_out=. --pyi_out=. --grpc_python_out=. ../../protos/helloworld.proto", cwd="examples/python/helloworld",
     gt_out=["examples/python/helloworld/helloworld_pb2.py", "examples/python/helloworld/helloworld_pb2.pyi", "examples/python/helloworld/helloworld_pb2_grpc.py"],
     declared_in=["examples/protos/helloworld.proto"],
     source="grpc.io Python quickstart codegen command; sparse checkout of examples/python/helloworld and examples/protos"),
 "black": dict(cmd=f"{PY} scripts/generate_schema.py --outfile src/black/resources/black.schema.json", cwd=".",
     gt_out=["src/black/resources/black.schema.json"], declared_in=["scripts/generate_schema.py"], declared_glob=r"^src/black/__init__\.py$",
     source="tox env 'generate_schema'; options are declared in src/black/__init__.py", pythonpath="src"),
}
def walk(r):
    out = []
    for d, ds, fs in os.walk(r):
        out += [os.path.relpath(os.path.join(d, f), r) for f in fs]
    return sorted(out)
def copy(src):
    base = tempfile.mkdtemp(prefix="rl_"); w = os.path.join(base, "r"); shutil.copytree(src, w, ignore=IGN, symlinks=True); return base, w
def run(w, spec):
    old = 1_000_000_000
    for f in walk(w):
        try: os.utime(os.path.join(w, f), (old, old), follow_symlinks=False)
        except OSError: pass
    before = set(walk(w)); env = dict(os.environ, PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1")
    if spec.get("pythonpath"): env["PYTHONPATH"] = os.path.join(w, spec["pythonpath"])
    p = subprocess.run(spec["cmd"], shell=True, cwd=os.path.join(w, spec["cwd"]), env=env, capture_output=True, text=True, timeout=600)
    after = set(walk(w))
    wr = sorted(f for f in after if f not in before or os.lstat(os.path.join(w, f)).st_mtime != old)
    return p.returncode, (p.stdout + p.stderr)[-600:], wr
def rd(p):
    try: return open(p, errors="replace").read()
    except FileNotFoundError: return None
def main(name, n_neg=40, seed=0):
    spec = dict(SPECS[name]); src = os.path.join(ROOT, name); t0 = time.time(); runs = 0
    if spec.get("gt_out_glob"):
        g = re.compile(spec["gt_out_glob"]); spec["gt_out"] = [f for f in walk(src) if g.match(f) and "__pycache__" not in f and not f.endswith("__init__.py")]
    b1, w1 = copy(src); rc, log, written = run(w1, spec); runs += 1
    res = dict(repo=name, cmd=spec["cmd"].replace(PY, "python"), rc=rc, written=written, gt_out=spec["gt_out"], source=spec["source"])
    if rc != 0: res["log"] = log; return res
    b2, w2 = copy(src); run(w2, spec); runs += 1
    ref = {o: rd(os.path.join(w1, o)) for o in written}
    noise = {o: sum(1 for x, y in zip((ref[o] or "").splitlines(), (rd(os.path.join(w2, o)) or "").splitlines()) if x != y) for o in written}
    # does the committed file already equal a fresh regeneration? (repo-level drift)
    tracked = set(subprocess.run(["git", "ls-files"], cwd=src, capture_output=True, text=True).stdout.split())
    res["committed"] = {o: o in tracked for o in written}
    res["committed_equals_regen"] = {o: rd(os.path.join(src, o)) == ref[o] for o in written if o in tracked}
    allf = [f for f in walk(w1) if f not in written and os.path.getsize(os.path.join(w1, f)) > 0]
    glob = re.compile(spec["declared_glob"]) if spec.get("declared_glob") else None
    declared = sorted(set(spec["declared_in"]) | {f for f in allf if glob and glob.match(f)})
    rnd = random.Random(seed)
    pos = declared if len(declared) <= 25 else sorted(rnd.sample(declared, 25))
    others = [f for f in allf if f not in declared]
    neg = sorted(rnd.sample(others, min(n_neg, len(others))))
    flagged = {}
    for c in pos + neg:
        b, w = copy(src); os.remove(os.path.join(w, c)); rc2, _, _ = run(w, spec); runs += 1
        hit = rc2 != 0 or any(rd(os.path.join(w, o)) != ref[o] for o in written if noise[o] == 0)
        changed = rc2 == 0 and any(rd(os.path.join(w, o)) != ref[o] for o in written if noise[o] == 0)
        flagged[c] = {"flagged": bool(hit), "kind": "content" if changed else ("crash" if rc2 != 0 else "none"), "declared": c in declared}
        shutil.rmtree(b, ignore_errors=True)
    for b in (b1, b2): shutil.rmtree(b, ignore_errors=True)
    tp = [c for c in pos if flagged[c]["flagged"]]; fpn = [c for c in neg if flagged[c]["flagged"]]
    res.update(noise_lines=noise, n_declared=len(declared), sampled_declared=len(pos), declared_recall=f"{len(tp)}/{len(pos)}",
               missed_declared=[c for c in pos if not flagged[c]["flagged"]], sampled_undeclared=len(neg),
               undeclared_flagged={c: flagged[c]["kind"] for c in fpn}, declared_kinds={c: flagged[c]["kind"] for c in pos}, regen_runs=runs, seconds=round(time.time() - t0, 1),
               out_precision=f"{len(set(written) & set(spec['gt_out']))}/{len(written)}", out_recall=f"{len(set(written) & set(spec['gt_out']))}/{len(spec['gt_out'])}")
    return res
if __name__ == "__main__":
    out = {n: main(n) for n in (sys.argv[1:] or SPECS)}
    print(json.dumps(out, indent=1))
