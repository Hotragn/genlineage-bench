"""LineageGuard component A (counterfactual lineage inference) on additional real OSS repositories, plus survival-gate
spot checks. Adapted from final/genlineage-bench/realrepo/real_lineage.py (other pipeline; aiohttp, black, pygments,
rich, grpc); this file adds different generator families: pycparser (config -> AST classes), yt-dlp (code-first doc
generation, template rendering, and a README generator that rewrites only one section of a hand-written file).

Safety: repositories are untrusted. Their generators run ONLY inside throwaway temp copies, without network
(`unshare -rn`), with a timeout. Clones live in build/data/oss/<name> and are never executed in place.
Usage: python -I build/realrepos/real_lineage.py [spec ...] > build/realrepos/results.json
"""
import json, os, random, re, shutil, subprocess, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__)); BUILD = os.path.dirname(HERE)
ROOT = os.path.join(BUILD, "data", "oss")
sys.path.insert(0, os.path.join(BUILD, "genlineage-bench"))
from genlineage.lineage import discover_commands
IGN = shutil.ignore_patterns(".git", "tests", "test", "docs", "doc", "__pycache__", "*.pyc", "node_modules", "vendor", "benchmarks", "assets", "imgs")
RUFF = os.path.join(BUILD, "venv", "bin", "ruff")
TPL = " && ".join(f"python3 devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/{i}.yml .github/ISSUE_TEMPLATE/{i}.yml"
                  for i in ("1_broken_site", "2_site_support_request", "3_site_feature_request", "4_bug_report", "5_feature_request", "6_question"))
SPECS = {
 "pycparser_ast": dict(repo="pycparser", cmd=f"python3 pycparser/_ast_gen.py && {RUFF} format --no-cache pycparser/c_ast.py",
     gt_out=["pycparser/c_ast.py"], declared_in=["pycparser/_ast_gen.py", "pycparser/_c_ast.cfg"],
     line_ablate="pycparser/_c_ast.cfg",
     source="Makefile target regen-ast (python3 pycparser/_ast_gen.py; make format = ruff 0.16.0 format); c_ast.py header 'automatically generated from _c_ast.cfg'",
     gate=[("pycparser/c_ast.py", "class FileAST(Node):", "class FileAST(Node):  # hand edit", "lost"),
           ("pycparser/c_parser.py", "\n", "\n# hand edit\n", "kept")]),
 "ytdlp_supportedsites": dict(repo="yt-dlp", cmd="python3 devscripts/make_supportedsites.py supportedsites.md",
     gt_out=["supportedsites.md"], declared_in=["devscripts/make_supportedsites.py"], declared_glob=r"^yt_dlp/extractor/(?!lazy_extractors)[^/]+\.py$",
     source="Makefile target supportedsites; generator imports every extractor in yt_dlp/extractor/"),
 "ytdlp_issuetemplates": dict(repo="yt-dlp", cmd=TPL,
     gt_out=[f".github/ISSUE_TEMPLATE/{i}.yml" for i in ("1_broken_site", "2_site_support_request", "3_site_feature_request", "4_bug_report", "5_feature_request", "6_question")],
     declared_in=["devscripts/make_issue_template.py", "yt_dlp/version.py"] + [f".github/ISSUE_TEMPLATE_tmpl/{i}.yml" for i in ("1_broken_site", "2_site_support_request", "3_site_feature_request", "4_bug_report", "5_feature_request", "6_question")],
     source="Makefile target issuetemplates (prerequisites list the _tmpl files, the script and yt_dlp/version.py)"),
 "ytdlp_readme": dict(repo="yt-dlp", cmd="COLUMNS=80 python3 yt_dlp/__main__.py --ignore-config --help | python3 devscripts/make_readme.py",
     gt_out=["README.md"], declared_in=["devscripts/make_readme.py", "yt_dlp/options.py", "README.md"],
     source="Makefile rule 'README.md: $(PY_CODE_FILES) devscripts/make_readme.py'; the script replaces only the options section of the hand-written README.md",
     gate=[("README.md", "Print program version and exit", "Print program version and exit (hand edit)", "lost"),
           ("README.md", "# INSTALLATION", "# INSTALLATION (hand edit)", "kept")]),
}

def walk(r):
    out = []
    for d, ds, fs in os.walk(r):
        out += [os.path.relpath(os.path.join(d, f), r) for f in fs]
    return sorted(out)

IGN_YT = shutil.ignore_patterns(".git", "test", "__pycache__", "*.pyc")   # yt-dlp has a real package named `vendor`
IGNORE = {"yt-dlp": IGN_YT}
CUR_IGN = [IGN]
def copy(src):
    base = tempfile.mkdtemp(prefix="rr_"); w = os.path.join(base, "r"); shutil.copytree(src, w, ignore=CUR_IGN[0], symlinks=True); return base, w

def run(w, spec, timeout=300):
    old = 1_000_000_000
    for f in walk(w):
        try: os.utime(os.path.join(w, f), (old, old), follow_symlinks=False)
        except OSError: pass
    before = set(walk(w)); env = dict(os.environ, PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1")
    try:
        p = subprocess.run(["unshare", "-rn", "sh", "-c", spec["cmd"]], cwd=w, env=env, capture_output=True, text=True, timeout=timeout)
        rc, log = p.returncode, (p.stdout + p.stderr)[-600:]
    except subprocess.TimeoutExpired:
        rc, log = 124, "TIMEOUT"
    after = set(walk(w))
    wr = sorted(f for f in after if f not in before or os.lstat(os.path.join(w, f)).st_mtime != old)
    return rc, log, wr

def rd(p):
    try: return open(p, errors="replace").read()
    except FileNotFoundError: return None

def survives(src, spec, rel, old, new):
    """Shadow regeneration: apply a one-line edit (first occurrence) and check whether regeneration keeps it."""
    b, w = copy(src); p = os.path.join(w, rel); s = rd(p)
    if s is None or old not in s: shutil.rmtree(b, ignore_errors=True); return "edit_not_applicable"
    s2 = s.replace(old, new, 1); open(p, "w").write(s2)
    added = [l for l in new.splitlines() if l not in s.splitlines()]
    rc, _, _ = run(w, spec); after = (rd(p) or "").splitlines()
    shutil.rmtree(b, ignore_errors=True)
    if rc != 0: return "regen_failed"
    return "kept" if all(l in after for l in added) else "lost"

def main(name, n_neg=40, seed=0):
    spec = dict(SPECS[name]); src = os.path.join(ROOT, spec["repo"]); t0 = time.time(); runs = 0
    CUR_IGN[0] = IGNORE.get(spec["repo"], IGN)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=src, capture_output=True, text=True).stdout.strip()
    b1, w1 = copy(src); rc, log, written = run(w1, spec); runs += 1
    res = dict(spec=name, repo=spec["repo"], commit=head, cmd=spec["cmd"].replace(RUFF, "ruff"), rc=rc, written=written, gt_out=spec["gt_out"], source=spec["source"],
               discovered_commands=discover_commands(src))
    if rc != 0: res["log"] = log; return res
    b2, w2 = copy(src); run(w2, spec); runs += 1
    ref = {o: rd(os.path.join(w1, o)) for o in written}
    noise = {o: sum(1 for x, y in zip((ref[o] or "").splitlines(), (rd(os.path.join(w2, o)) or "").splitlines()) if x != y) for o in written}
    tracked = set(subprocess.run(["git", "ls-files"], cwd=src, capture_output=True, text=True).stdout.split())
    res["committed"] = {o: o in tracked for o in written}
    res["committed_equals_regen"] = {o: rd(os.path.join(src, o)) == ref[o] for o in written if o in tracked}
    res["committed_diff_lines"] = {o: sum(1 for x, y in zip((rd(os.path.join(src, o)) or "").splitlines(), (ref[o] or "").splitlines()) if x != y) for o in written if o in tracked}
    allf = [f for f in walk(w1) if f not in written and os.path.getsize(os.path.join(w1, f)) > 0]
    glob = re.compile(spec["declared_glob"]) if spec.get("declared_glob") else None
    declared = sorted(set(spec["declared_in"]) | {f for f in allf if glob and glob.match(f)})
    rnd = random.Random(seed)
    pos = declared if len(declared) <= 25 else sorted(rnd.sample(declared, 25))
    others = [f for f in allf if f not in declared]
    neg = sorted(rnd.sample(others, min(n_neg, len(others))))
    flagged = {}
    for c in pos + neg:
        b, w = copy(src)
        if os.path.exists(os.path.join(w, c)): os.remove(os.path.join(w, c))
        rc2, _, _ = run(w, spec); runs += 1
        changed = rc2 == 0 and any(rd(os.path.join(w, o)) != ref[o] for o in written if noise[o] == 0)
        flagged[c] = {"flagged": rc2 != 0 or changed, "kind": "content" if changed else ("crash" if rc2 != 0 else "none"), "declared": c in declared}
        shutil.rmtree(b, ignore_errors=True)
    # line-level counterfactual map for one data input (delete one line at a time, sample of 20 non-blank lines)
    if spec.get("line_ablate"):
        lines = open(os.path.join(src, spec["line_ablate"])).read().split("\n")
        cand = [i for i, l in enumerate(lines) if l.strip() and not l.lstrip().startswith("#")]
        samp = sorted(rnd.sample(cand, min(20, len(cand)))); lm = []
        for i in samp:
            b, w = copy(src); open(os.path.join(w, spec["line_ablate"]), "w").write("\n".join(lines[:i] + lines[i + 1:]))
            rc3, _, _ = run(w, spec); runs += 1
            o = spec["gt_out"][0]; new = (rd(os.path.join(w, o)) or "").splitlines(); old = (ref.get(o) or "").splitlines()
            import difflib
            sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
            hit = sorted({k for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal" for k in (range(i1, i2) if i2 > i1 else [i1])})
            lm.append({"input_line": i + 1, "text": lines[i].strip()[:80], "rc": rc3, "output_lines_changed": len(hit), "first_output_lines": [k + 1 for k in hit[:5]]})
            shutil.rmtree(b, ignore_errors=True)
        res["line_map_sample"] = lm
    gate = []
    for rel, old, new, expect in spec.get("gate", []):
        v = survives(src, spec, rel, old, new); runs += 1; gate.append({"file": rel, "edit": f"{old!r} -> {new!r}", "verdict": v, "expected": expect})
    for b in (b1, b2): shutil.rmtree(b, ignore_errors=True)
    tp = [c for c in pos if flagged[c]["flagged"]]; fpn = [c for c in neg if flagged[c]["flagged"]]
    res.update(noise_lines=noise, n_declared=len(declared), sampled_declared=len(pos), declared_recall=f"{len(tp)}/{len(pos)}",
               missed_declared=[c for c in pos if not flagged[c]["flagged"]], sampled_undeclared=len(neg),
               undeclared_flagged={c: flagged[c]["kind"] for c in fpn}, declared_kinds={c: flagged[c]["kind"] for c in pos}, gate=gate,
               regen_runs=runs, seconds=round(time.time() - t0, 1),
               out_precision=f"{len(set(written) & set(spec['gt_out']))}/{len(written)}", out_recall=f"{len(set(written) & set(spec['gt_out']))}/{len(spec['gt_out'])}")
    return res

if __name__ == "__main__":
    out = {}
    for n in (sys.argv[1:] or SPECS):
        out[n] = main(n); print(json.dumps({k: v for k, v in out[n].items() if k not in ("declared_kinds",)})[:1500], file=sys.stderr, flush=True)
    print(json.dumps(out, indent=1))
