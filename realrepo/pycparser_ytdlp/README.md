# Lineage inference (LineageGuard component A) on additional real repositories

Complements the other pipeline's run on aiohttp, black, pygments, rich and grpc helloworld
(realrepo/RESULTS.md); no repository or generator family is repeated. Script:
`real_lineage.py` (adapted from realrepo/real_lineage.py, same method: write detection by
mtime, two unperturbed runs for noise, delete-one ablation over declared inputs (all, or 25 sampled) and 40 sampled
other files; `content` = an output changed, `crash` = generation failed). Additions: a line-level ablation of one data
input (20 sampled lines), survival-gate spot checks (shadow regeneration of a one-line edit), and a check of
`genlineage.lineage.discover_commands` on the real repos.

Safety: clones (shallow, default branch) in build/data/oss/; generators ran only in temp copies, under
`unshare -rn` (no network; verified that a urlopen fails inside), with a 300 s timeout.
Run Tue Nov 10 2026 ~5:40 to 6:11 AM EST on the shared 8-core box (ollama E4B running concurrently, so seconds are
upper bounds). Python 3.13.5, ruff 0.16.0 (pinned by pycparser's Makefile).
Commands: `python -I realrepos/real_lineage.py pycparser_ast` (raw: results_run1.json) and
`python -I realrepos/real_lineage.py ytdlp_supportedsites ytdlp_issuetemplates ytdlp_readme` (raw: results_ytdlp.json;
the first yt-dlp attempt in results_run1.json failed because the copy excluded a real package named `vendor`).

Commits: pycparser 3ec766b7cd94724cba714296509604597ea4ce4e (2026-10-22); yt-dlp 412e7f0a4b0588fe884a02b344ac66a06538475b (2026-11-04).

| spec | family | command (from the repo's Makefile) | outputs found vs declared | committed == regen | noise lines | declared inputs flagged | undeclared flagged (of 40) | regen runs | s |
|---|---|---|---|---|---|---|---|---|---|
| pycparser_ast | config file -> Python AST classes (custom generator + formatter) | `python3 pycparser/_ast_gen.py && ruff format pycparser/c_ast.py` (target regen-ast) | 1/1 (`pycparser/c_ast.py`) | yes | 0 | 2/2 (both crash on whole-file deletion) | 0 | 66 | 8.3 |
| ytdlp_supportedsites | code-first doc generation (imports every extractor) | `python3 devscripts/make_supportedsites.py supportedsites.md` | 1/1 | yes | 0 | 25/25 sampled of 941 extractor files (all crash) | 17, all crash (core modules) | 67 | 82.3 |
| ytdlp_issuetemplates | template rendering (6 YAML templates) | 6 x `make_issue_template.py <tmpl> <out>` | 6/6 | yes (6/6) | 0 | 7/8 (missed `yt_dlp/version.py`, see below) | 0 | 50 | 20.7 |
| ytdlp_readme | section-rewriting generator over a hand-written file | `COLUMNS=80 python3 yt_dlp/__main__.py --ignore-config --help \| python3 devscripts/make_readme.py` | 1/1 (`README.md`, which is also an input) | no, 1 line (trailing space in wrapped help text) | 0 | 3/3 (crash) | 3, crash | 47 | 28.2 |

Line-level lineage (pycparser): deleting each of 20 sampled lines of `_c_ast.cfg` (e.g. `If: [cond*, iftrue*, iffalse*]`)
changed a contiguous block of 16 to 39 lines of `c_ast.py` (the generated class), 20/20 with exit code 0. So the
line map gives a precise pointer from a generated class to its one-line spec, whereas whole-file deletion only
says "crash".

Survival gate (shadow regeneration), 4/4 as expected:
| file | edit | verdict |
|---|---|---|
| pycparser/c_ast.py (generated) | append `# hand edit` to `class FileAST(Node):` | lost |
| pycparser/c_parser.py (hand-written) | insert a comment line | kept |
| yt-dlp README.md, inside the generated options section | `Print program version and exit` + ` (hand edit)` | lost |
| yt-dlp README.md, outside that section | `# INSTALLATION` + ` (hand edit)` | kept |
The README case is a real instance of the benchmark's in-region kind: one file mixes hand-owned and generated text,
so a file-level label ("README.md is generated" or "is not") is wrong either way; the survival check is right on both.

Findings
1. Write detection found every declared output in all 4 commands (9/9 files), with zero noise lines.
2. Committed outputs equal a fresh regeneration for 8/9 files; the README differs by one trailing space, i.e. the
   output depends on the Python/argparse version (same lesson as rich and grpc in the other run: pin the generator).
3. The crash-versus-content split reported for the other 5 repos does NOT hold here: for supportedsites every
   declared input (an extractor module) and 17/40 other modules crash when deleted, because the generator imports the
   whole package. Delete-one ablation cannot distinguish "input" from "runtime dependency" for code-first generators;
   a finer perturbation (line deletion, as for pycparser) is needed. This matches the in-the-wild audit, where most
   edits to generated files came from code-first generators.
4. A Makefile prerequisite can over-declare: `yt_dlp/version.py` is listed for issuetemplates, but the script does not
   read it; deleting it leaves all 6 outputs unchanged, so inference correctly does not report it.
5. Command discovery (`genlineage.lineage.discover_commands`) does not transfer: it found none of the 4 real commands
   (pycparser's target is `regen-ast`; yt-dlp's are `supportedsites`, `issuetemplates`, `README.md`, which the
   target regex does not match), and on yt-dlp it proposed 5 wrong commands because the script-name regex
   `(gen|generate|render|codegen)[_\w]*\.py` matches `generic.py`, `genericembeds.py`, `genius.py`,
   `generate_aes_testdata.py`, `generate_third_party_licenses.py`. Discovery executes what it finds, so on a real
   repository it must be replaced by declared commands (Makefile/tox/CI) or a human-confirmed list. The benchmark
   numbers for discovery do not generalize; the paper should say commands are supplied, as the other run did.
Limitations: 2 repositories, 4 commands, Python generators only; sampled ablation; one gate edit per side.
