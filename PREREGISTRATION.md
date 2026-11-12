# Analysis plan, fixed before any valid grid result was seen

Written Tue Nov 10 2026, 4:45 AM EST. The only model outputs seen before this point were the Nov 8 pilot (mismatched configs, not used) and the Nov 10 gl-smoke run (8 runs, generators missing, invalid, not used). The grid gl-grid-a v3 was pushed at 4:36 AM EST and no output has been downloaded.

Population: test split, 19 tasks (12 regen, 2 inregion, 1 mixed, 4 control). Dev split (7 tasks) was used only to build and debug the harness; it is not analysed.
Unit: one (model, condition, task, seed) run. Pairing for tests: (task, seed).

Primary outcome: durable repair rate (DRR) on regeneration tasks (kind regen or mixed, 13 tasks): original tests (restored, SHA-256 checked) pass after `make gen` with pinned build files, and no test file was modified.

Primary contrasts (per model, two-sided exact McNemar on (task, seed) pairs, alpha 0.05, Holm across the three within a model):
- P1 natural vs full (does LineageGuard improve durability?)
- P2 headerguard vs full (does execution-grounded lineage beat the header-based practitioner guard?)
- P3 hint vs full (do affordances beat a prompt instruction?)
Effect size: paired difference in DRR with a task-clustered bootstrap 95% CI (5,000 resamples).

Secondary (reported with unadjusted p and CIs, labelled exploratory):
- Attribution ablations on E4B: staticblock vs gate (shadow regeneration vs a static block with the same message), verify_tests vs verify (regeneration vs extra rounds), lineage vs gate (gate on top of banners), verify vs full.
- Immediate success rate (ISR), disappearing-fix rate DFR = lost / immediate passes, hand edits to generated files, test and build tampering, root-cause rate, control-task DRR (no harm check), in-region DRR, steps, tokens, wall time, gate overhead.
- Factor breakdowns (header present, AGENTS.md present, generator family) on natural and full.
- Reward-mislabel: share of runs a test-on-tree reward would pay that fail after regeneration.

Stopping rule: the grid runs until its fixed 4.8 h budget ends; all completed cells are analysed; incomplete (task, seed) pairs are excluded from paired tests only. No cell is rerun selectively, except runs that end in an infrastructure error (model server unreachable), which are rerun once and listed. Any deviation from this plan is listed in the paper.

## Amendment 1 (Tue Nov 10 ~5:05 AM EST, still before any grid output was downloaded)
Prompted by an internal hostile review (claude_log C3):
- Added secondary contrast HeaderGuard vs gate (R+G, no V) for all three models, because full includes V, which runs the same regenerate-and-test procedure as the scorer (oracle in the loop). The mechanism claim (execution-grounded gating vs header labels) will rest on HeaderGuard vs gate, reported as secondary.
- Added, next to every McNemar p, a task-level sign-flip permutation p (per-task mean paired difference, all 2^k sign patterns, or 20,000 random flips if k > 15), because (task, seed) pairs are not independent across seeds.
- Will report planned vs completed runs per cell, DFR numerator and denominator, and gate overhead.
