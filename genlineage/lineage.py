"""LineageGuard, component A: counterfactual lineage inference.

Infers which files a repository's generation command WRITES (outputs) and which files it
DEPENDS ON (inputs), using only black-box execution of the command in a sandbox copy:
  1. discover candidate regeneration commands (Makefile targets, generator-like scripts);
  2. outputs  = files whose mtime changes when the command runs (write detection, works for
                any generator language, including protoc's C++ core);
  3. inputs   = files whose deletion makes the command fail or changes some output beyond the
                generator's own run-to-run noise (counterfactual ablation);
  4. noise    = output lines that differ between two unperturbed runs (e.g. LALR state numbering).
No task metadata, headers or naming conventions are used.
"""
import difflib, os, re, shutil, tempfile, time
from genlineage.env import sh

GEN_TARGET = re.compile(r"^(gen|generate|codegen|regen|proto|protos|models|render|build[-_]?gen\w*|gen[-_]\w+)$")
BUILD_FILES = {"Makefile", "makefile", "GNUmakefile", "pyproject.toml", "setup.cfg", "tox.ini", "noxfile.py", "justfile"}
SKIP_DIRS = {".git", "__pycache__", "tests", "test"}

def files(repo):
    out = []
    for d, dirs, fs in os.walk(repo):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        out += [os.path.relpath(os.path.join(d, f), repo) for f in fs if not f.endswith(".pyc")]
    return sorted(out)

def discover_commands(repo):
    cmds = []
    mk = os.path.join(repo, "Makefile")
    if os.path.exists(mk):
        for l in open(mk).read().splitlines():
            m = re.match(r"^([A-Za-z0-9_.-]+)\s*:", l)
            if m and GEN_TARGET.match(m.group(1)): cmds.append(f"make {m.group(1)}")
    if not cmds:
        for f in files(repo):
            b = os.path.basename(f)
            if f.endswith(".py") and re.match(r"(gen|generate|render|codegen)[_\w]*\.py$", b): cmds.append(f"python {f}")
    return cmds

def _read(p):
    try: return open(p, errors="replace").read()
    except FileNotFoundError: return None

def _run(repo, cmd):
    old = 1_000_000_000
    for f in files(repo): os.utime(os.path.join(repo, f), (old, old))
    before = set(files(repo))
    rc, out = sh(cmd, repo)
    after = set(files(repo))
    written = sorted(f for f in after if f not in before or os.path.getmtime(os.path.join(repo, f)) != old)
    return rc, out, written

def _differs(a, b, noise):
    if a is None or b is None: return a != b
    if a == b: return False
    la, lb = a.splitlines(), b.splitlines()
    if len(la) != len(lb): return True
    return any(x != y for i, (x, y) in enumerate(zip(la, lb)) if i not in noise)

def infer(repo, max_candidates=60, commands=None):
    """commands: optional list of declared generation commands; None (default) = discover_commands(repo)."""
    t0 = time.time(); res = {"commands": [], "outputs": {}, "seconds": 0.0, "regen_runs": 0}
    for cmd in (discover_commands(repo) if commands is None else list(commands)):
        base = tempfile.mkdtemp(prefix="lin_")
        try:
            w1 = os.path.join(base, "a"); shutil.copytree(repo, w1, ignore=shutil.ignore_patterns("__pycache__"))
            rc, out, written = _run(w1, cmd); res["regen_runs"] += 1
            if rc != 0 or not written: continue
            w2 = os.path.join(base, "b"); shutil.copytree(repo, w2, ignore=shutil.ignore_patterns("__pycache__"))
            _run(w2, cmd); res["regen_runs"] += 1
            ref = {o: _read(os.path.join(w1, o)) for o in written}
            noise = {}
            for o in written:
                a, b = (ref[o] or "").splitlines(), (_read(os.path.join(w2, o)) or "").splitlines()
                noise[o] = {i for i, (x, y) in enumerate(zip(a, b)) if x != y} if len(a) == len(b) else set(range(max(len(a), len(b))))
            deps = {o: [] for o in written}
            cands = [f for f in files(repo) if f not in written and not f.endswith(".md") and os.path.getsize(os.path.join(repo, f)) > 0][:max_candidates]
            for c in cands:
                w = os.path.join(base, "c"); shutil.rmtree(w, ignore_errors=True)
                shutil.copytree(repo, w, ignore=shutil.ignore_patterns("__pycache__")); os.remove(os.path.join(w, c))
                rc2, _, _ = _run(w, cmd); res["regen_runs"] += 1
                for o in written:
                    if rc2 != 0 or _differs(ref[o], _read(os.path.join(w, o)), noise[o]): deps[o].append(c)
            # line-level counterfactual map for data-like inputs (specs, templates, grammars): delete one line at a time
            lm = {}
            for c in sorted({i for o in written for i in deps[o]}):
                if c.endswith((".py", ".sh")) or os.path.basename(c) in BUILD_FILES: continue
                src_lines = open(os.path.join(repo, c), errors="replace").read().splitlines()
                if len(src_lines) > 120: continue
                for li, line in enumerate(src_lines):
                    if not line.strip(): continue
                    w = os.path.join(base, "l"); shutil.rmtree(w, ignore_errors=True)
                    shutil.copytree(repo, w, ignore=shutil.ignore_patterns("__pycache__"))
                    open(os.path.join(w, c), "w").write("\n".join(src_lines[:li] + src_lines[li + 1:]) + "\n")
                    rc3, _, _ = _run(w, cmd); res["regen_runs"] += 1
                    if rc3 != 0: continue
                    for o in written:
                        new = (_read(os.path.join(w, o)) or "").splitlines(); old = (ref[o] or "").splitlines()
                        sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
                        hit = sorted({i for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal" for i in (range(i1, i2) if i2 > i1 else [i1]) if i not in noise[o]})
                        if hit and len(hit) <= 12: lm.setdefault(o, []).append([c, li + 1, line.strip()[:80], hit])
            res.setdefault("line_map", {}).update(lm)
            res["commands"].append(cmd)
            for o in written:
                if o in res["outputs"]: continue
                ins = deps[o]
                res["outputs"][o] = {"command": cmd, "inputs": ins,
                                     "generators": [i for i in ins if i.endswith((".py", ".sh"))],
                                     "build": [i for i in ins if os.path.basename(i) in BUILD_FILES],
                                     "specs": [i for i in ins if not i.endswith((".py", ".sh")) and os.path.basename(i) not in BUILD_FILES],
                                     "noisy_lines": len(noise[o])}
        finally:
            shutil.rmtree(base, ignore_errors=True)
    res["seconds"] = round(time.time() - t0, 2)
    return res

def pointer(lin, rel, old_text, new_text, k=3):
    """Map the output lines touched by an edit to the input lines whose deletion changes them (most specific first)."""
    entries = (lin or {}).get("line_map", {}).get(rel, [])
    if not entries: return ""
    sm = difflib.SequenceMatcher(None, old_text.splitlines(), new_text.splitlines(), autojunk=False)
    touched = set()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal": touched.update(range(max(0, i1 - 1), i2 + 1))
    ranked = sorted([e for e in entries if touched & set(e[3])], key=lambda e: (len(e[3]), e[0], e[1]))
    best_per_file = {}
    for e in ranked: best_per_file.setdefault(e[0], e)
    cands = list(best_per_file.values()) + [e for e in ranked if e not in best_per_file.values()]
    cands = cands[:k]
    if not cands: return ""
    return " The lines you changed are derived from: " + "; ".join(f"{c}:{n} `{t}`" for c, n, t, _ in cands) + "."

def edit_survives(repo, cmd, rel, new_text, old_text=None):
    """Shadow regeneration: would writing new_text to rel survive running cmd? Returns (survives, detail)."""
    base = tempfile.mkdtemp(prefix="surv_")
    try:
        w = os.path.join(base, "r"); shutil.copytree(repo, w, ignore=shutil.ignore_patterns("__pycache__"))
        old = old_text if old_text is not None else (_read(os.path.join(w, rel)) or "")
        p = os.path.join(w, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(new_text)
        rc, out = sh(cmd, w)
        after = _read(p) or ""
        if rc != 0: return False, f"regeneration failed after the edit: {out[-300:]}"
        sm = difflib.SequenceMatcher(None, old.splitlines(), new_text.splitlines(), autojunk=False)
        added, removed = [], []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("replace", "delete"): removed += [l for l in old.splitlines()[i1:i2] if l.strip()]
            if tag in ("replace", "insert"): added += [l for l in new_text.splitlines()[j1:j2] if l.strip()]
        if after == new_text: return True, "edit preserved by regeneration"
        al = after.splitlines(); nl = new_text.splitlines()
        lost_add = sorted({l for l in added if al.count(l) < nl.count(l)})  # multiset check: a copy elsewhere does not count
        back = [l for l in removed if al.count(l) > new_text.splitlines().count(l)]
        if not lost_add and not back: return True, "edit preserved by regeneration"
        return False, "regeneration reverted: " + "; ".join((["removed your line: " + l.strip() for l in lost_add] + ["restored: " + l.strip() for l in back])[:4])
    finally:
        shutil.rmtree(base, ignore_errors=True)
