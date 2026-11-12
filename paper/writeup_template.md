# The Fix That Disappears
*A benchmark and a write gate for agent fixes that regeneration reverts*

## Abstract
Coding agents are scored by running the tests on the tree they leave behind. In repositories that commit generated code (protobuf stubs, OpenAPI clients, parser tables), that tree is not stable: the next `make gen` rebuilds generated files from their sources and reverts any fix written into them. GenLineage-Bench ({{p:bench.test}} validated tasks over real generators) scores a repair by rerunning the generator, then the tests. Unaided Gemma 4 E2B, E4B and 12B agents passed in {{p:pool.natural.imm}} of {{p:pool.natural.n}} runs on generator-dependent tasks, and {{p:pool.natural.lost}} of those fixes disappeared on regeneration; all {{p:pool.natural.lost_genonly}} had edited only generated files. LineageGuard runs the generator counterfactually to infer lineage and rejects only writes that regeneration would revert. The preregistered durable repair rate rose from {{p:pool.natural.DRR}} (natural), {{p:pool.hint.DRR}} (a prompt hint) and {{p:pool.headerguard.DRR}} (a header-based guard) to {{p:pool.full.DRR}} with full LineageGuard (pooled task-level Holm p at most {{p:tl.max_holm_prim}}; strict DRR {{p:pool.natural.strictpct}} to {{p:pool.full.strictpct}}). This is an upper bound, since its final check reuses the scorer's procedure, and per-model tests are significant on E2B and E4B, not 12B. The write gate alone, which never runs the tests, reached {{p:pool.gate.DRR}}; on E4B a static block pointing to the source matched it, so the gain is localization. Of {{p:aidev.prs}} real agent pull requests, {{p:aidev.edit_gen}} edit a file marked as generated.

## 1. Introduction
A Gemma 4 agent is asked to fix an API client. A test fails on a misspelled field in `client/models.py`, so the agent corrects the field there and the tests pass. But `client/models.py` is generated from `api/openapi.yaml`, which still has the typo, and the next `make gen`, in someone else's build, restores the bug (Figure 1). No test on the agent's tree can catch this, because the patch is correct today.

![Figure 1](figures/fig1_disappearing_fix.png)
*Figure 1. A passing fix that regeneration reverts, and the gated path to the source.*

It happens in practice. A review agent read a file headed `GENERATED from pre-review.src.sh -- DO NOT EDIT` in every run without flagging that a pull request's edits to it would be lost [fullsend2026issue1022], and a coding agent that could not run a generator hand-edited two generated files [konflux2026issue373]. Practitioners respond with labels: AGENTS.md rules [packer2026agentsmd], path hooks [rstudio2026hook] and header blockers [dsh2026protect]. Labels miss headerless files, misfire on hand-written ones [ohmypi2026pr13139], and cannot tell a correct edit inside a preserved region from one outside it. Standard benchmarks rarely test this ({{p:swe.gen_instances}} of {{p:swe.instances_total}} SWE-bench Verified instances touches a committed generated file), yet the companion competition grades the same way (apply the diff, run pytest), and rich, one of its repositories, commits generated Unicode width tables.


## 2. Problem and metrics
A repository holds hand-owned files, generator inputs and generated files produced by a committed command, here `make gen`. After the agent finishes, we restore the original tests and build files (SHA-256 checked), run the tests, run `make gen` in place, and run the tests again.
- **Immediate success rate (ISR)**: tests pass on the agent's tree.
- **Durable repair rate (DRR, preregistered primary)**: tests pass after regeneration, and no test file was modified. A *latent* fix (source fixed, outputs left stale) fails now but passes after regeneration. It counts as durable: the next build delivers it.
- **Strict DRR (secondary)**: passes both before and after regeneration.
- **Disappearing-fix rate (DFR)**: share of immediate passes that fail after regeneration.
- **Hand edits (HEG)**: the run edited a generated file. Test tampering is reported separately; because tests are restored, it never yields a pass.

## 3. GenLineage-Bench
Each task is a small Python repository around a real generator: protobuf (grpcio-tools {{p:pin.grpcio-tools}}), OpenAPI (datamodel-code-generator {{p:pin.datamodel-code-generator}}), Jinja2 {{p:pin.Jinja2}} templates, a Lark {{p:pin.lark}} standalone parser, and a round-trip generator we wrote that preserves `USER CODE` regions. The test split has {{p:bench.test}} tasks: {{p:bench.regen}} *regen* (the fix belongs in a generator input), {{p:bench.inregion}} *in-region* (the fix belongs inside a preserved region of a generated file), {{p:bench.mixed}} *mixed* and {{p:bench.control}} *controls* (a bug in hand-owned code, so refusing every edit fails). Headers and AGENTS.md vary; {{p:hl.tasks}} regen tasks have no header. {{p:bench.dev}} more dev tasks only built the harness.

Validation is mechanical ({{p:bench.validated}} tasks pass). The untouched repository fails, the reference fix passes both checks, a generated-file-only patch ({{p:bench.antipatch}} of {{p:bench.rm}} regen and mixed tasks) passes now and fails after regeneration, and regeneration is deterministic up to a noise mask. Shell commands are diffed, so shell edits count as hand edits.

## 4. LineageGuard
![Figure 2](figures/fig2_overview.png)
*Figure 2. LineageGuard reruns the generator in a copy at A, R, G and V; the scorer regenerates, then tests.*

**A. Lineage inference (once per repository; Figure 2).** We run the generation command in a sandbox. Its outputs are the files it writes; two runs measure line noise. Deleting each other file in turn marks the inputs; for small data-like inputs, deleting single lines maps output lines to source lines. No headers or names are used. On our tasks this takes {{p:graph.runs_min}} to {{p:graph.runs_max}} generator runs (median {{p:graph.med_s}} s on CPU). The lineage is also exported as a NetworkX graph (`produced_by`, `generated_from`, `derived_from` and `part_of` edges over file, command and line nodes). The competition's code graphs link Python symbols, so a generated module has no edge to its `.proto` or YAML source; these edges supply it. No agent queried the graph; lineage reached agents only through R and G.

**R. Read-time banners.** `list_files` and `read_file` mark generated files with their command and inputs.

**G. Survival-gated writes.** A write to a generated file is applied in a shadow copy and the generator is rerun. The write is rejected only if regeneration reverts it, with a pointer to the source lines, so edits inside preserved regions go through. Shell edits are checked the same way.

**V. Regenerate-then-verify.** When the agent stops, we regenerate a shadow copy, run the tests and return any failures (at most {{p:cfg.vrounds}} more rounds). V runs the scorer's own procedure, so conditions with V are oracle-in-the-loop upper bounds.

## 5. Setup and statistics
**Agent.** A minimal tool-calling agent (list_files, read_file, write_file, replace_in_file, run_tests, run_command) over ollama {{p:ollama.version}} with Gemma 4 QAT checkpoints (`gemma4:e2b-it-qat`, `gemma4:e4b-it-qat`, `gemma4:12b-it-qat`) on two Kaggle T4 GPUs: temperature {{p:cfg.temp}}, thinking off, {{p:cfg.ctx}}-token context, {{p:cfg.predict}} output tokens per step and at most {{p:cfg.steps}} steps. This is not the competition's ADK harness or checkpoints, though our tools mirror its file and shell tools. 31B was not run: the weekly GPU quota allowed one five-hour session.

**Conditions.** *natural*; *hint* (a system-prompt sentence: generated files are rebuilt, fix sources); *HeaderGuard* (re-implements dsh-protect-generated-files: header regex over 15 lines plus protobuf names, deny with a hint); *StaticBlock* (G's rejection message on every generated-file write, without regeneration, so in-region edits are blocked too); *VerifyTests* (V's extra rounds, tests only); *V*; *R*; *R+G* (the gate); *R+G+V* (full LineageGuard). E4B ran all nine; E2B and 12B the first three and the last two.

**Runs.** {{p:runs.total}} runs completed (E2B {{p:runs.k_e2b}}, E4B {{p:runs.k_e4b}}, 12B {{p:runs.k_12b}}), with {{p:runs.infra}} infrastructure error excluded. Seeds 1 and 2, complete everywhere, are the primary data; E4B's partial seed 3 ({{p:runs.e4b_seed3_range}} tasks per condition) is a robustness check.

**Plan.** The preregistration (SHA-256 `{{p:prereg.sha8}}`) fixes the outcome, DRR on the {{p:bench.rm}} regen and mixed tasks, and three primary contrasts (natural, hint and HeaderGuard, each against R+G+V), tested per model by exact McNemar on (task, seed) pairs with Holm adjustment. A pre-results amendment added HeaderGuard vs R+G as the oracle-free mechanism contrast, and permutation p values. Seeds are unmatched at temperature {{p:cfg.temp}} and tasks are shared across models, so we lead with a pooled exact sign-flip permutation test with tasks as units ({{p:tl.units}} units, each a mean paired difference; Holm over the three primaries) and also report model-task units and the planned per-model tests. Everything else is exploratory; intervals are bootstraps clustered by task.

## 6. Results
### 6.1 Passing fixes disappear
**Table 1.** Regen and mixed tasks, seeds 1 and 2 ({{p:cell.n}} runs per cell; 12B natural {{p:k_12b.natural.n}}). Percent of runs; DRR with task-clustered 95% interval. R+G+V is an oracle-in-the-loop upper bound; strict DRR is in Figure 3.

| Model | Condition | ISR | DRR [95% CI] | DFR |
|---|---|---|---|---|
| E2B | natural | {{p:k_e2b.natural.ISR}} | {{p:k_e2b.natural.DRR}} {{p:k_e2b.natural.DRR_ci}} | {{p:k_e2b.natural.DFR}} |
| E2B | hint | {{p:k_e2b.hint.ISR}} | {{p:k_e2b.hint.DRR}} {{p:k_e2b.hint.DRR_ci}} | {{p:k_e2b.hint.DFR}} |
| E2B | HeaderGuard | {{p:k_e2b.headerguard.ISR}} | {{p:k_e2b.headerguard.DRR}} {{p:k_e2b.headerguard.DRR_ci}} | {{p:k_e2b.headerguard.DFR}} |
| E2B | R+G | {{p:k_e2b.gate.ISR}} | {{p:k_e2b.gate.DRR}} {{p:k_e2b.gate.DRR_ci}} | {{p:k_e2b.gate.DFR}} |
| E2B | R+G+V | {{p:k_e2b.full.ISR}} | {{p:k_e2b.full.DRR}} {{p:k_e2b.full.DRR_ci}} | {{p:k_e2b.full.DFR}} |
| E4B | natural | {{p:k_e4b.natural.ISR}} | {{p:k_e4b.natural.DRR}} {{p:k_e4b.natural.DRR_ci}} | {{p:k_e4b.natural.DFR}} |
| E4B | hint | {{p:k_e4b.hint.ISR}} | {{p:k_e4b.hint.DRR}} {{p:k_e4b.hint.DRR_ci}} | {{p:k_e4b.hint.DFR}} |
| E4B | HeaderGuard | {{p:k_e4b.headerguard.ISR}} | {{p:k_e4b.headerguard.DRR}} {{p:k_e4b.headerguard.DRR_ci}} | {{p:k_e4b.headerguard.DFR}} |
| E4B | R+G | {{p:k_e4b.gate.ISR}} | {{p:k_e4b.gate.DRR}} {{p:k_e4b.gate.DRR_ci}} | {{p:k_e4b.gate.DFR}} |
| E4B | R+G+V | {{p:k_e4b.full.ISR}} | {{p:k_e4b.full.DRR}} {{p:k_e4b.full.DRR_ci}} | {{p:k_e4b.full.DFR}} |
| 12B | natural | {{p:k_12b.natural.ISR}} | {{p:k_12b.natural.DRR}} {{p:k_12b.natural.DRR_ci}} | {{p:k_12b.natural.DFR}} |
| 12B | hint | {{p:k_12b.hint.ISR}} | {{p:k_12b.hint.DRR}} {{p:k_12b.hint.DRR_ci}} | {{p:k_12b.hint.DFR}} |
| 12B | HeaderGuard | {{p:k_12b.headerguard.ISR}} | {{p:k_12b.headerguard.DRR}} {{p:k_12b.headerguard.DRR_ci}} | {{p:k_12b.headerguard.DFR}} |
| 12B | R+G | {{p:k_12b.gate.ISR}} | {{p:k_12b.gate.DRR}} {{p:k_12b.gate.DRR_ci}} | {{p:k_12b.gate.DFR}} |
| 12B | R+G+V | {{p:k_12b.full.ISR}} | {{p:k_12b.full.DRR}} {{p:k_12b.full.DRR_ci}} | {{p:k_12b.full.DFR}} |

Under natural prompting, `make gen` reverted {{p:pool.natural.lost}} of {{p:pool.natural.imm}} passing fixes ({{p:pool.natural.DFR}}). DFR falls with model size (E2B {{p:k_e2b.natural.DFR}}%, E4B {{p:k_e4b.natural.DFR}}%, 12B {{p:k_12b.natural.DFR}}%) but persists, and {{p:pool.natural.HEGpct}} of natural runs hand-edited a generated file. A reward computed on the agent's tree would have paid all {{p:pool.natural.lost}}. Latent fixes explain why DRR exceeds surviving passes: {{p:pool.natural.latent}} natural runs fixed a source without regenerating.

![Figure 3](figures/fig3_immediate_vs_durable.png)
*Figure 3. Immediate pass rate, DRR with 95% interval, and strict DRR (tick).*

### 6.2 Primary contrasts
Pooled over models, full LineageGuard raised DRR from {{p:pool.natural.DRR}} to {{p:pool.full.DRR}} against natural ({{p:pool.natural_vs_full.disc}} discordant pairs, {{p:pool.natural_vs_full.diff}} points {{p:pool.natural_vs_full.ci}}, task-level Holm p {{p:tl.natural_vs_full.holm}}), from {{p:pool.hint.DRR}} against the hint ({{p:pool.hint_vs_full.disc}}, {{p:pool.hint_vs_full.diff}} {{p:pool.hint_vs_full.ci}}, p {{p:tl.hint_vs_full.holm}}) and from {{p:pool.headerguard.DRR}} against HeaderGuard ({{p:pool.headerguard_vs_full.disc}}, {{p:pool.headerguard_vs_full.diff}} {{p:pool.headerguard_vs_full.ci}}, p {{p:tl.headerguard_vs_full.holm}}). With model-task units all three Holm p are {{p:pool.natural_vs_full.holm}}, and under strict DRR the task-level p are at most {{p:tl.strict_max_p_prim}}. Paired changes use only complete (model, task, seed) pairs, so may differ slightly from marginal rates.

**Table 2.** Per-model DRR change in points (R+G+V or R+G minus baseline), with discordant pairs (treatment-only:baseline-only) and unadjusted task-level permutation p.

| Model | natural vs R+G+V | hint vs R+G+V | HeaderGuard vs R+G+V | HeaderGuard vs R+G |
|---|---|---|---|---|
| E2B | {{p:k_e2b.natural_vs_full.diff}} ({{p:k_e2b.natural_vs_full.colon}}; {{p:k_e2b.natural_vs_full.p}}) | {{p:k_e2b.hint_vs_full.diff}} ({{p:k_e2b.hint_vs_full.colon}}; {{p:k_e2b.hint_vs_full.p}}) | {{p:k_e2b.headerguard_vs_full.diff}} ({{p:k_e2b.headerguard_vs_full.colon}}; {{p:k_e2b.headerguard_vs_full.p}}) | {{p:k_e2b.headerguard_vs_gate.diff}} ({{p:k_e2b.headerguard_vs_gate.colon}}; {{p:k_e2b.headerguard_vs_gate.p}}) |
| E4B | {{p:k_e4b.natural_vs_full.diff}} ({{p:k_e4b.natural_vs_full.colon}}; {{p:k_e4b.natural_vs_full.p}}) | {{p:k_e4b.hint_vs_full.diff}} ({{p:k_e4b.hint_vs_full.colon}}; {{p:k_e4b.hint_vs_full.p}}) | {{p:k_e4b.headerguard_vs_full.diff}} ({{p:k_e4b.headerguard_vs_full.colon}}; {{p:k_e4b.headerguard_vs_full.p}}) | {{p:k_e4b.headerguard_vs_gate.diff}} ({{p:k_e4b.headerguard_vs_gate.colon}}; {{p:k_e4b.headerguard_vs_gate.p}}) |
| 12B | {{p:k_12b.natural_vs_full.diff}} ({{p:k_12b.natural_vs_full.colon}}; {{p:k_12b.natural_vs_full.p}}) | {{p:k_12b.hint_vs_full.diff}} ({{p:k_12b.hint_vs_full.colon}}; {{p:k_12b.hint_vs_full.p}}) | {{p:k_12b.headerguard_vs_full.diff}} ({{p:k_12b.headerguard_vs_full.colon}}; {{p:k_12b.headerguard_vs_full.p}}) | {{p:k_12b.headerguard_vs_gate.diff}} ({{p:k_12b.headerguard_vs_gate.colon}}; {{p:k_12b.headerguard_vs_gate.p}}) |

Per model, the planned McNemar tests agree on E2B and E4B (all Holm p at most {{p:holm.max_e2b_e4b}}). On 12B no contrast is significant (natural vs R+G+V Holm p {{p:k_12b.natural_vs_full.holm}}), so we claim no 12B effect. Adding E4B seed 3 changes nothing (natural vs R+G+V {{p:e4b123.natural_vs_full.diff}} points {{p:e4b123.natural_vs_full.ci}}, p {{p:e4b123.natural_vs_full.p}}).

### 6.3 What helps without the grader
The gate alone (R+G) reruns the generator but never the tests (every condition can call run_tests). It reached {{p:pool.gate.DRR}} pooled, above HeaderGuard ({{p:pool.headerguard_vs_gate.disc}}, {{p:pool.headerguard_vs_gate.diff}} points, task-level p {{p:tl.headerguard_vs_gate.p}}), the hint ({{p:pool.hint_vs_gate.disc}}, p {{p:tl.hint_vs_gate.p}}) and natural ({{p:pool.natural_vs_gate.disc}}, p {{p:tl.natural_vs_gate.p}}). These are secondary; per model the mechanism contrast is significant only on {{p:mech.sig_models}} (Table 2).

Under any gate DFR is 0 by construction. The cost is more failing runs that change no file ({{p:pool.natural.noedit}} of {{p:pool.natural.n}} natural, {{p:pool.gate.noedit}} of {{p:pool.gate.n}} under R+G). In exploratory E4B ablations, StaticBlock, which shows the same source pointer without regeneration, tied the gate on regen and mixed tasks ({{p:k_e4b.staticblock.DRR}}% vs {{p:k_e4b.gate.DRR}}%, {{p:k_e4b.staticblock_vs_gate.disc}} discordant pairs; natural {{p:k_e4b.natural.DRR}}%, HeaderGuard {{p:k_e4b.headerguard.DRR}}%). There the gain comes from lineage-derived localization, not from the survival check. The check may matter where the fix belongs inside a generated file: on in-region tasks, which natural agents solved ({{p:inreg.k_e4b.natural}}), StaticBlock solved {{p:inreg.k_e4b.staticblock}} and the gate {{p:inreg.k_e4b.gate}} (untested). V alone reached {{p:k_e4b.verify.DRR}}% against {{p:k_e4b.verify_tests.DRR}}% for test-only extra rounds ({{p:k_e4b.verify_tests_vs_verify.disc}}, p {{p:k_e4b.verify_tests_vs_verify.p}}), and V on top of the gate added more ({{p:k_e4b.gate_vs_full.disc}}, p {{p:k_e4b.gate_vs_full.p}}). Banners alone (R) reached {{p:k_e4b.lineage.DRR}}%; agents still write to outputs labeled generated.

**Headerless files.** On the {{p:hl.tasks}} regen tasks without a header, pooled DRR was {{p:hl.natural.dur}} of {{p:hl.natural.n}} runs under natural, {{p:hl.hint.dur}} under the hint, {{p:hl.headerguard.dur}} under HeaderGuard, {{p:hl.gate.dur}} under the gate and {{p:hl.full.dur}} under R+G+V (gate vs HeaderGuard {{p:hl.headerguard_vs_gate.disc}}, p {{p:hl.headerguard_vs_gate.p}}; exploratory). HeaderGuard cannot see these files ({{p:hl.headerguard.lost}} of its {{p:hl.headerguard.imm}} passes there disappeared), yet it blocked a hand-owned source {{p:blocksrc.headerguard}} times (templates matching its header rules); the survival gate blocked none.

### 6.4 Harm, tampering and cost
On the {{p:bench.control}} control tasks, DRR was {{p:ctrl.pool.natural}} (natural), {{p:ctrl.pool.hint}} (hint), {{p:ctrl.pool.headerguard}} (HeaderGuard), {{p:ctrl.pool.gate}} (gate) and {{p:ctrl.pool.full}} (R+G+V): no gross harm. Test tampering, on all {{p:bench.test}} tasks and the same seeds, was rare and not reduced: {{p:pool.natural.tt}} of {{p:pool.natural.n_all}} natural runs ({{p:pool.natural.ttpct}}), {{p:pool.hint.tt}} of {{p:pool.hint.n_all}} hint, {{p:pool.headerguard.tt}} of {{p:pool.headerguard.n_all}} HeaderGuard, {{p:pool.gate.tt}} of {{p:pool.gate.n_all}} gate and {{p:pool.full.tt}} of {{p:pool.full.n_all}} R+G+V. 12B never tampered, and no build file was altered. A mean E4B run took {{p:k_e4b.natural.steps}} steps, {{p:k_e4b.natural.tokens}} tokens and {{p:k_e4b.natural.wall}} s under natural, {{p:k_e4b.gate.steps}}, {{p:k_e4b.gate.tokens}} and {{p:k_e4b.gate.wall}} s under the gate, and {{p:k_e4b.full.steps}}, {{p:k_e4b.full.tokens}} and {{p:k_e4b.full.wall}} s under R+G+V.

### 6.5 Signal ladder and noise floor
Natural E4B ran the {{p:bench.rm}} regen and mixed tasks with no signal (L0), a do-not-edit header (L1) or header plus AGENTS.md (L2), {{p:ladder.n}} runs each. DRR was {{p:ladder.L0.dur}}, {{p:ladder.L1.dur}} and {{p:ladder.L2.dur}} of {{p:ladder.n}}. A header helped (discordant {{p:ladder.L0L1.dur.disc}}, p {{p:ladder.L0L1.dur.p}}). The agent opened AGENTS.md in {{p:ladder.L2.read_agents}} of {{p:ladder.n}} L2 runs [yang2026contribrules], yet L2 scored below L1 ({{p:ladder.L1L2.dur.disc}}, p {{p:ladder.L1L2.dur.p}}). An unread file moving {{p:ladder.L1L2.moved}} of {{p:ladder.n}} outcomes sets a noise floor; per-model contrasts of that size deserve caution, and the pooled primaries ({{p:pool.natural_vs_full.disc}}, {{p:pool.hint_vs_full.disc}}) exceed it.

## 7. Beyond the benchmark
**Real repositories.** Lineage inference ran on {{p:rr.repos}} open-source projects (aiohttp, black, pygments, rich, gRPC helloworld, pycparser, yt-dlp). On pycparser and yt-dlp, write detection found {{p:rr.outputs_found}} declared outputs with {{p:rr.noise}} noise lines, and the gate classified {{p:rr.gate}} spot-check edits as expected, two of them in yt-dlp's README, which mixes hand-written and generated text, so any file-level label misjudges one. Negatives: delete-one ablation cannot separate inputs from imports for code-first generators (every yt-dlp module deletion crashes the generator).

**Real-repository tasks (negative).** We built {{p:real.tasks_ok}} validated tasks by injecting bugs into generator inputs of pycparser and yt-dlp. HeaderGuard's rules match {{p:realtask.hg_matches}} of their {{p:realtask.gen_files}} generated files (pycparser's header says "automatically generated ... Do not modify it directly"; yt-dlp's outputs have none). In {{p:real.runs}} E4B CPU runs on pycparser the agent solved {{p:real.imm}} and {{p:real.tt}} modified tests (generated `c_ast.py` has {{p:realtask.c_ast_lines}} lines; prompts reached {{p:realtask.max_prompt}} tokens). They are not durability evidence; we release them for larger models.

**Agent pull requests in the wild.** In AIDev v5 [li2026aidev], {{p:aidev.edit_gen}} of {{p:aidev.prs}} agent pull requests ({{p:aidev.edit_gen_pct}}) edit a file that path or header rules mark as generated, and {{p:aidev.nosrc}} change no plausible source. A hand audit of {{p:audit.n}} of these found {{p:audit.consistent}} consistent outputs of code-first generators, {{p:audit.lost}} hand edits that regeneration would revert, {{p:audit.unclear}} unclear and {{p:audit.notgen}} not generated. One of the {{p:audit.lost}} came from a regeneration commit, so {{p:audit.lost_net}} are confirmed (Wilson 95% CI {{p:audit.wilson_net}}). Of {{p:hdr.n}} path-detected generated files, {{p:hdr.nostrong}} carry no do-not-edit header in their first 15 lines and {{p:hdr.invisible}} are invisible to HeaderGuard's rules. Labels mis-predict loss both ways, so this measures exposure, not loss.

![Figure 4](figures/fig4_aidev.png)
*Figure 4. Agent pull requests touching generated files (log scale) and the hand audit.*

## 8. Related work
**Oracles.** SWE-bench [jimenez2024swebench], live variants [zhang2025swelive] and scaffolds [yang2024sweagent; xia2025agentless; wang2025openhands] score the post-edit tree, and training rewards inherit it [pan2025swegym; wei2025swerl]. Critiques expose wrong patches [wang2026solved], weak tests [yu2025utboost] and test exploitation [zhong2026impossiblebench]. They strengthen the tests, while we first rerun the repository's generator. Projects run regenerate-and-diff CI checks [kubernetes2026verifycodegen; azure2026pr840], but no agent benchmark applies them, and a diff check rejects legitimate preserved-region edits.

**Durability.** SWE-Maintain [pan2026swemaintain] and SWE-CI [chen2026sweci] follow agent code across later tasks, and SWE-Touch injects user edits mid-task [tan2026swetouch]. None reruns a repository operation right after the repair.

**Boundaries.** Prompt-level awareness is not enough without constrained affordances [trong2026swemisbehavior], boundary contracts leave enforcement open [eun2026boundary], and context files help little [gloaguen2026agentsmd]. Code-graph localizers [chen2025locagent; ouyang2025repograph] also lack these edges.

**Builds and round trips.** Build tools infer dependencies by tracing [spall2020perfect; fan2020escaping]; we use write detection and delete-one ablation [zeller2002dd]. Protected regions preserve hand edits by generator design [greifenberg2015integration; predoaia2025preservation].

## 9. Limitations and deviations
- **Scope.** Small Python repositories we wrote around real generators; {{p:bench.rm}} primary tasks give wide intervals; one model family and harness. R+G+V is an upper bound, and the survival check's benefit rests on few in-region runs.
- **The generator must run.** A and G need a supplied, runnable, deterministic command; discovery found {{p:rr.discovered}} real commands [konflux2026issue373].
- **Deviations.** We lead with a pooled permutation test, not per-model McNemar; seeds 1 and 2 are primary, while the plan used all completed pairs; strict DRR is added. The one infrastructure error was not rerun (no quota). Root-cause-fix rates and factor breakdowns are only in released summaries; per-write gate latency is unreported. E4B seed 3 is partial, and the ladder ran on CPU. The grid was launched nine minutes before the plan was written, though no output had been seen, and the plan has no public timestamp earlier than the repository release.

## 10. Reproducibility and release
Code, tasks, transcripts, lineage graphs and analysis are released under Apache 2.0 at https://github.com/Hotragn/genlineage-bench (Kaggle notebook: https://www.kaggle.com/code/pettuganihotragn/genlineage-the-fix-that-disappears). `scripts/check_claims.py` recomputes every number here from raw transcripts and fails on any mismatch.

## References
{{REFS}}
