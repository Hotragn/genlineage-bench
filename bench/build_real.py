"""Build GenLineage-Bench tasks on REAL open-source repositories (split "real") and validate the oracle on each.

Usage (from build/genlineage-bench, inside the pinned venv):
    python bench/build_real.py              # builds bench/tasks_real/<id>/{repo,task.json,ref_outputs} + validation_real.json
    python bench/build_real.py rp1_...      # rebuild one task

Pattern (same as bench/build.py): export the real repository at a pinned commit (git archive, so no .git and no
untracked files), inject a bug into a generator INPUT, run the repository's own generation command so the committed
generated output is consistent with the buggy input, add a short failing test, record the reference fix (revert the
input line, then regenerate) and the generated-only anti-patch (the same output change applied by hand to the
generated file, computed as a diff between the buggy and the reference outputs).
The box has no GNU make; bench/bin/make is a shim that runs the literal recipe lines of one target, so the appended
`gen:` target spells out the repository's real recipe lines (no make variables).
"""
import difflib, json, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT)
from genlineage.env import sh
from genlineage.score import apply_patch, digest
from bench.build import validate

OSS = os.path.abspath(os.path.join(ROOT, "..", "data", "oss"))
OUT = os.path.join(HERE, "tasks_real")
PIN = {"pycparser": "3ec766b7cd94724cba714296509604597ea4ce4e", "yt-dlp": "412e7f0a4b0588fe884a02b344ac66a06538475b"}

PYC_GEN = "\n# --- GenLineage-Bench wrapper: the recipe of target regen-ast with ruff pinned (RUFF_VERSION 0.16.0) and --no-cache (no .ruff_cache/ writes) ---\ngen:\n\tpython3 pycparser/_ast_gen.py\n\truff format --no-cache pycparser/c_ast.py\n"
YT_TMPL = ["1_broken_site", "2_site_support_request", "3_site_feature_request", "4_bug_report", "5_feature_request", "6_question"]
YT_GEN_TMPL = ("\n# --- GenLineage-Bench wrapper: the recipe of target issuetemplates ---\ngen:\n"
               + "".join(f"\tpython3 devscripts/make_issue_template.py .github/ISSUE_TEMPLATE_tmpl/{t}.yml .github/ISSUE_TEMPLATE/{t}.yml\n" for t in YT_TMPL))
YT_GEN_LAZY = ("\n# --- GenLineage-Bench wrapper: the recipe of target yt_dlp/extractor/lazy_extractors.py ---\ngen:\n"
               "\tpython3 devscripts/make_lazy_extractors.py yt_dlp/extractor/lazy_extractors.py\n")

TEST_ELSE = '''import unittest

from pycparser import c_ast, c_parser


class CallCollector(c_ast.NodeVisitor):
    def __init__(self):
        self.names = []

    def visit_FuncCall(self, node):
        self.names.append(node.name.name)
        self.generic_visit(node)


class TestVisitorElse(unittest.TestCase):
    def test_visitor_visits_else_branch(self):
        ast = c_parser.CParser().parse("void f(int x) { if (x) a(); else b(); }")
        v = CallCollector()
        v.visit(ast)
        self.assertEqual(v.names, ["a", "b"])
'''
TEST_STRUCTREF = '''import unittest

from pycparser import c_generator, c_parser


class TestStructRefRoundTrip(unittest.TestCase):
    def test_member_access_round_trip(self):
        src = "struct s { int x; }; int f(struct s *p, struct s q) { return p->x + q.x; }"
        ast = c_parser.CParser().parse(src)
        out = c_generator.CGenerator().visit(ast)
        self.assertIn("p->x", out)
        self.assertIn("q.x", out)
'''
TEST_LAZY = '''import unittest

from yt_dlp.extractor import gen_extractor_classes


class TestCharlieRoseUrl(unittest.TestCase):
    def test_charlierose_episode_url(self):
        url = "https://charlierose.com/episodes/30887?autoplay=true"
        matches = [ie.ie_key() for ie in gen_extractor_classes() if ie.suitable(url)]
        self.assertEqual(matches[0], "CharlieRose")
'''
TEST_TMPL = '''import os
import unittest

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestBugReportForm(unittest.TestCase):
    def test_bug_report_requires_verbose_log(self):
        with open(os.path.join(ROOT, ".github", "ISSUE_TEMPLATE", "4_bug_report.yml")) as f:
            form = yaml.safe_load(f)
        body = {item.get("id"): item for item in form["body"] if item.get("id")}
        self.assertTrue(body["log"]["validations"]["required"])
        first = body["verbose"]["attributes"]["options"][0]
        self.assertTrue(first["required"])
'''

TASKS = [
    dict(id="rp1_pycparser_if_else", family="pycparser-astgen", repo="pycparser", header=True,
         issue=("pycparser's c_ast.NodeVisitor never visits the `else` branch of an `if` statement: a visitor that collects "
                "function calls finds `a` but not `b` in `void f(int x) { if (x) a(); else b(); }`. "
                "test_visitor_visits_else_branch fails. Please fix."),
         sources=["pycparser/_c_ast.cfg"], generators=["pycparser/_ast_gen.py"], generated=["pycparser/c_ast.py"],
         bug={"pycparser/_c_ast.cfg": [["\nIf: [cond*, iftrue*, iffalse*]", "\nIf: [cond*, iftrue*, iffalse]"]]},
         tests={"tests/test_issue_else.py": TEST_ELSE}, makefile_add=PYC_GEN, trim=[], keep_tests=["__init__.py", "test_c_ast.py"]),
    dict(id="rp2_pycparser_structref", family="pycparser-astgen", repo="pycparser", header=True,
         issue=("c_generator.CGenerator crashes with AttributeError when it regenerates C code containing struct member "
                "access (`p->x` or `q.x`); parsing works. test_member_access_round_trip fails. Please fix."),
         sources=["pycparser/_c_ast.cfg"], generators=["pycparser/_ast_gen.py"], generated=["pycparser/c_ast.py"],
         bug={"pycparser/_c_ast.cfg": [["\nStructRef: [name*, type, field*]", "\nStructRef: [name*, kind, field*]"]]},
         tests={"tests/test_issue_structref.py": TEST_STRUCTREF}, makefile_add=PYC_GEN, trim=[], keep_tests=["__init__.py", "test_c_ast.py"]),
    dict(id="ry1_ytdlp_lazy_url", family="ytdlp-lazyextractors", repo="yt-dlp", header=False,
         issue=("yt-dlp no longer recognizes Charlie Rose episode pages: for https://charlierose.com/episodes/30887 no "
                "extractor except the generic one claims the URL, so it is handled by Generic instead of CharlieRose. "
                "test_charlierose_episode_url fails. Please fix."),
         sources="EXTRACTORS", generators=["devscripts/make_lazy_extractors.py", "devscripts/lazy_load_template.py"],
         generated=["yt_dlp/extractor/lazy_extractors.py"],
         bug={"yt_dlp/extractor/charlierose.py": [["(?:video|episode)(?:s|/player)", "(?:video|epsiode)(?:s|/player)"]]},
         tests={"tests/__init__.py": "", "tests/test_issue_url.py": TEST_LAZY}, makefile_add=YT_GEN_LAZY, trim=["test"]),
    dict(id="ry2_ytdlp_issue_template", family="ytdlp-issuetemplates", repo="yt-dlp", header=False,
         issue=("Core bug reports are being filed without logs: the bug report issue form (.github/ISSUE_TEMPLATE/4_bug_report.yml) "
                "no longer makes the complete verbose output mandatory. test_bug_report_requires_verbose_log fails. Please fix."),
         sources=[f".github/ISSUE_TEMPLATE_tmpl/{t}.yml" for t in YT_TMPL], generators=["devscripts/make_issue_template.py"],
         generated=[f".github/ISSUE_TEMPLATE/{t}.yml" for t in YT_TMPL],
         bug={".github/ISSUE_TEMPLATE_tmpl/4_bug_report.yml": [["\n  %(verbose)s", "\n  %(verbose_optional)s"]]},
         tests={"tests/__init__.py": "", "tests/test_issue_template.py": TEST_TMPL}, makefile_add=YT_GEN_TMPL, trim=["test"]),
]

def export(repo_name, dst):
    src = os.path.join(OSS, repo_name); os.makedirs(dst)
    tar = subprocess.run(["git", "-C", src, "archive", PIN[repo_name]], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", dst], input=tar, check=True)

def hunks(old, new, ctx=2):
    """(old_chunk, new_chunk) replacement pairs turning old into new (difflib groups, so chunks never overlap);
    context grows until each old chunk is unique in the file."""
    a, b = old.splitlines(True), new.splitlines(True); pairs = []
    for grp in difflib.SequenceMatcher(None, a, b, autojunk=False).get_grouped_opcodes(ctx):
        i1, i2, j1, j2 = grp[0][1], grp[-1][2], grp[0][3], grp[-1][4]; c = 0
        while True:
            lo, hi = max(0, i1 - c), min(len(a), i2 + c)
            o = "".join(a[lo:hi]); n = "".join(a[lo:i1] + b[j1:j2] + a[i2:hi])
            if old.count(o) == 1 or (lo == 0 and hi == len(a)): break
            c += 2
        pairs.append([o, n])
    return pairs

def reverse(patch):
    return {f: [[n, o] for o, n in pairs] for f, pairs in patch.items()}

def build_one(t):
    root = os.path.join(OUT, t["id"]); repo = os.path.join(root, "repo")
    shutil.rmtree(root, ignore_errors=True); os.makedirs(root)
    export(t["repo"], repo)
    for d in t["trim"]: shutil.rmtree(os.path.join(repo, d))
    trimmed = list(t["trim"])
    if t.get("keep_tests") is not None:  # keep the run_tests output short enough for the agent (tool output is capped at 4000 chars)
        for e in sorted(os.listdir(os.path.join(repo, "tests"))):
            if e not in t["keep_tests"]:
                q = os.path.join(repo, "tests", e); trimmed.append("tests/" + e)
                shutil.rmtree(q) if os.path.isdir(q) else os.remove(q)
    with open(os.path.join(repo, "Makefile"), "a") as f: f.write(t["makefile_add"])
    for rel, s in t["tests"].items():
        p = os.path.join(repo, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(s)
    # sanity: on the clean (unbugged) export, regeneration is a no-op on committed outputs and the tests pass
    clean = os.path.join(root, "_clean"); shutil.copytree(repo, clean)
    d0 = digest(clean); rc, out = sh("make gen", clean); assert rc == 0, out[-800:]
    d1 = digest(clean); clean_changed = sorted(k for k in d1 if d0.get(k) != d1[k])
    rc_t, out_t = sh("python -m unittest discover -s tests", clean); assert rc_t == 0, (t["id"], "clean tests fail", out_t[-1200:])
    shutil.rmtree(clean)
    # inject the bug into the generator input, then regenerate so the committed output carries the bug
    ref_fix = t["bug"]; apply_patch(repo, ref_fix); ref_fix = reverse(ref_fix)
    before = digest(repo); rc, out = sh("make gen", repo); assert rc == 0, out[-800:]
    after = digest(repo); produced = sorted(k for k in after if before.get(k) != after[k])
    assert set(produced) <= set(t["generated"]) and produced, (t["id"], produced)
    sources = t["sources"]
    if sources == "EXTRACTORS":
        sources = sorted(os.path.join("yt_dlp/extractor", f) for f in os.listdir(os.path.join(repo, "yt_dlp/extractor"))
                         if f.endswith(".py") and f != "lazy_extractors.py")
    meta = dict(id=t["id"], family=t["family"], split="real", kind="regen", fix_locus="spec", header=t["header"], agents_md=False,
                issue=t["issue"], generated=t["generated"], sources=sources, generators=t["generators"], ref_fix=ref_fix,
                gen_cmd="make gen", lineage_commands=["make gen"],
                upstream={"repo": t["repo"], "commit": PIN[t["repo"]], "trimmed": trimmed, "clean_regen_changed": clean_changed,
                          "bug_regen_changed": produced, "makefile": "real Makefile + appended `gen:` target"})
    meta["test_hashes"] = {k: v for k, v in digest(repo).items() if k.startswith("tests/")}
    meta["build_files"] = ["Makefile"]
    ref = os.path.join(root, "_ref"); shutil.copytree(repo, ref); apply_patch(ref, ref_fix)
    sh("make gen", ref); a = {g: open(os.path.join(ref, g)).read() for g in t["generated"]}
    sh("make gen", ref); b = {g: open(os.path.join(ref, g)).read() for g in t["generated"]}
    os.makedirs(os.path.join(root, "ref_outputs")); meta["noise_lines"] = {}; meta["gen_only_fix"] = {}
    for g in t["generated"]:
        open(os.path.join(root, "ref_outputs", g.replace("/", "__")), "w").write(a[g])
        la, lb = a[g].splitlines(), b[g].splitlines()
        meta["noise_lines"][g] = [i for i, (x, y) in enumerate(zip(la, lb)) if x != y]
        cur = open(os.path.join(repo, g)).read()
        if cur != a[g]: meta["gen_only_fix"][g] = hunks(cur, a[g])
    shutil.rmtree(ref)
    json.dump(meta, open(os.path.join(root, "task.json"), "w"), indent=1)
    return meta, repo

if __name__ == "__main__":
    only = sys.argv[1:]; os.makedirs(OUT, exist_ok=True); rows = []
    for t in TASKS:
        if only and t["id"] not in only: continue
        meta, repo = build_one(t)
        r = validate(meta, repo); r["gen_only_fix_hunks"] = {g: len(p) for g, p in meta["gen_only_fix"].items()}
        r["upstream"] = meta["upstream"]; rows.append(r); print(json.dumps(r), flush=True)
    index = {t["id"]: {"family": t["family"], "split": "real", "kind": "regen", "fix_locus": "spec", "header": t["header"], "agents_md": False} for t in TASKS}
    json.dump(index, open(os.path.join(OUT, "index.json"), "w"), indent=1)
    if not only: json.dump(rows, open(os.path.join(HERE, "validation_real.json"), "w"), indent=1)
    bad = [r["task"] for r in rows if not r["ok"]]
    print("ALL OK" if not bad else f"FAILED: {bad}")
