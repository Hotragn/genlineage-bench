# Generated files in SWE-bench Verified gold patches

Run Tue Nov 10 2026 ~4:55 AM EST: `python prevalence/swebench_generated.py` (needs pyarrow; data: princeton-nlp/SWE-bench_Verified test parquet from Hugging Face, 500 instances). For every file touched by a gold patch or test patch, the first 15 lines were fetched at the instance's base commit and checked for generated-code markers (Linguist-style regex), known generated names (PLY parsetab/lextab, protobuf _pb2, ANTLR output) and linguist-generated entries in .gitattributes.

- Files checked: 1,287 (1,261 present at base, 26 created by the patch).
- Flagged: 2 files, both in one instance, astropy__astropy-14369.
  - `astropy/units/format/cds_parsetab.py`: header "This file was automatically generated from ply. To re-generate this file, ...". The gold patch edits it. This is a true generated file.
  - `astropy/units/format/cds.py`: flagged by a comment saying the module includes generated files; it is the hand-written grammar source (false positive of the marker regex). The gold patch changes the grammar rule `division_of_units` in its docstring.
- So 1 of 500 Verified tasks (0.2%) needs a change to a committed generated file, and in that task the developer changed the grammar source and the regenerated table together.

Reading: the standard benchmark almost never exercises the source-to-generated relation, so agent behaviour on it is unmeasured there. That is the gap GenLineage-Bench targets. It is not evidence about prevalence in industry repositories, which commit far more generated code (protobuf, OpenAPI clients) than these 12 scientific and web Python projects.
