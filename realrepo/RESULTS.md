# Lineage inference (component A) on real open-source repositories

Run Tue Nov 10 2026 ~4:25 AM EST (grpc added ~5:05 AM) on the box CPU, `python realrepo/real_lineage.py aiohttp black rich pygments grpc` (raw: res_all.json). Shallow clones of default branches on Nov 10. Command = the repository's own documented regeneration command (Makefile rule or tox env); the command is given, not discovered (discovery is evaluated only on the benchmark). Sandbox copies exclude .git, tests and docs.
Input check: delete-one ablation over (a) the declared inputs (all, or a random sample of 25 when more) and (b) a random sample of 40 other files. "content" = deleting the file changed an output; "crash" = generation failed.

| repo | command | outputs found vs ground truth | noise lines | declared inputs flagged | undeclared files flagged (of 40) | regen runs | seconds |
|---|---|---|---|---|---|---|---|
| aiohttp | python tools/gen.py | 2/2 (both gitignored; `_headers.pxi` is not in the Makefile rule) | 0 | 2/2 (crash) | 0 | 44 | 5.3 |
| black | scripts/generate_schema.py (tox generate_schema) | 1/1, committed file equals regeneration | 0 | 2/2 (`__init__.py` content, script crash) | 11, all crash (transitive imports) | 44 | 13.3 |
| pygments | python scripts/gen_mapfiles.py (tox mapfiles) | 3/3, committed files equal regeneration | 0 | 25/25 sampled lexer/style modules (20 content, 5 crash) | 10, all crash (core modules: lexer.py, util.py, ...) | 67 | 43.4 |
| grpc (examples/python/helloworld) | python -m grpc_tools.protoc ... helloworld.proto (grpc.io quickstart) | 3/3; committed `_pb2.py` and `_pb2_grpc.py` differ from regeneration (committed with protobuf 5.27.2, regenerated with grpcio-tools 1.85.1), `.pyi` equal | 0 | 1/1 (crash) | 0 | 43 | 2.3 |
| rich | tools/make_width_tables.py | wrote 2 files: `_versions.py` (committed, differs) and `unicode18-0-0.py` (new); 1 of 22 committed tables touched | 0 | 2/2 (crash) | 1, crash | 44 | 5.5 |

Findings
1. Write detection found every output of the documented command in all 5 repos (including protoc's C++ code generator), including an output that the build rule does not declare (aiohttp `_headers.pxi`).
2. No undeclared file changed output content; every undeclared flag was a crash caused by deleting an imported module. So a crash-versus-content split separates editable sources from runtime dependencies: in the benchmark lineage map only content inputs carry line pointers.
3. Generation can depend on the environment: with wcwidth 0.9.4 installed, rich's generator writes only the newest Unicode table and a changed versions file, and grpc's committed stubs differ from what the current grpcio-tools emits. A durability oracle must pin generator versions (our benchmark pins all generators in requirements.txt).
4. Cost is seconds to under a minute per repo, i.e. it can be cached per repository and recomputed only when the generator or its inputs change.
Limitations: 5 repos, Python generators only, commands supplied by hand from the repos' own build files; delete-one ablation cannot see redundant inputs.

Commits analysed (shallow clones, Nov 10 2026):
- aiohttp: d1e21bf9e819acf4b39dba3a4b0032e0e6d6410e (2026-11-09T14:24:51Z)
- black: b4f1fcae48826790b6f93ca9226d20003bce0eaa (2026-11-04T07:36:13-08:00)
- rich: 3a109ccdffe5b2d0e30684a304fbd388e99ce57b (2026-11-07T11:26:07Z)
- pygments: 156d85fdd18d34427fe893527e71da91dcfb0eb5 (2026-09-27T09:00:22+02:00)
- grpc: ec36b58a9b9ba773c19bd98c224016d34215b9e7 (2026-11-09T14:59:02-08:00), sparse checkout

## Survival gate (component G) on real repositories
`python realrepo/real_gate.py` (raw: res_gate.json), same commits. 5 of 5 edits classified as expected, about 2.4 s in total:
| repo | edited file | edit | gate verdict |
|---|---|---|---|
| pygments | pygments/lexers/_mapping.py (generated) | 'PythonLexer' -> 'PythonLexerX' | rejected: regeneration removes the edited line |
| pygments | README.rst (hand-written) | Pygments -> Pygments! | admitted |
| black | src/black/resources/black.schema.json (generated) | "integer" -> "number" | rejected: regeneration restores "integer" |
| grpc | helloworld_pb2_grpc.py (generated) | SayHello -> SayHelo | rejected: regeneration restores SayHello |
| grpc | greeter_server.py (hand-written) | Hello -> Hi | admitted |
These are spot checks, not a benchmark: they show the gate needs nothing repository-specific beyond the regeneration command.
