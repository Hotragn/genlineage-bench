| Agent | PRs with file data | PRs touching lockfile | PRs touching generated (a or b) | PRs editing generated | ...without plausible source | ...with source for every edited gen file | merge rate: edit-gen w/o source | merge rate: edit-gen with source | merge rate: no generated file |
|---|---|---|---|---|---|---|---|---|---|
| Claude_Code | 171,169 | 19,948 (11.7%) | 3,935 (2.3%) | 2,939 (1.7%) | 1,059 (36.0% of editing) | 1,880 (64.0%) | 70.8% (n=1,059) | 69.5% (n=1,880) | 72.0% (n=167,234) |
| Copilot | 98,333 | 7,991 (8.1%) | 1,894 (1.9%) | 1,064 (1.1%) | 423 (39.8% of editing) | 641 (60.2%) | 58.9% (n=423) | 64.1% (n=641) | 60.6% (n=96,439) |
| Cursor | 12,885 | 1,509 (11.7%) | 253 (2.0%) | 189 (1.5%) | 99 (52.4% of editing) | 90 (47.6%) | 69.7% (n=99) | 47.8% (n=90) | 58.2% (n=12,632) |
| Devin | 11,211 | 1,472 (13.1%) | 357 (3.2%) | 216 (1.9%) | 128 (59.3% of editing) | 88 (40.7%) | 69.5% (n=128) | 59.1% (n=88) | 58.6% (n=10,854) |
| Google_Jules | 3,456 | 356 (10.3%) | 39 (1.1%) | 32 (0.9%) | 7 (21.9% of editing) | 25 (78.1%) | 42.9% (n=7) | 40.0% (n=25) | 60.2% (n=3,417) |
| OpenAI_Codex | 62,681 | 3,140 (5.0%) | 669 (1.1%) | 525 (0.8%) | 267 (50.9% of editing) | 258 (49.1%) | 62.2% (n=267) | 65.1% (n=258) | 75.4% (n=62,012) |
| ALL | 359,735 | 34,416 (9.6%) | 7,147 (2.0%) | 4,965 (1.4%) | 1,983 (39.9% of editing) | 2,982 (60.1%) | 66.9% (n=1,983) | 66.8% (n=2,982) | 68.4% (n=352,588) |

| Agent | touch gen: path (a) | touch gen: header (b) | touch gen: all touched gen files have a source in PR |
|---|---|---|---|
| Claude_Code | 2,855 | 1,863 | 2,474 of 3,935 (62.9%) |
| Copilot | 1,058 | 1,110 | 999 of 1,894 (52.7%) |
| Cursor | 184 | 99 | 131 of 253 (51.8%) |
| Devin | 241 | 186 | 149 of 357 (41.7%) |
| Google_Jules | 34 | 19 | 28 of 39 (71.8%) |
| OpenAI_Codex | 456 | 316 | 321 of 669 (48.0%) |
| ALL | 4,828 | 3,593 | 4,102 of 7,147 (57.4%) |

pairs: {"pairs": 72894, "pairs_header": 32540, "edited_pairs": 37318, "edited_pairs_with_src": 23960, "pairs_path": 34163, "path_pairs": 40354, "path_pairs_hdr_unknown": 27882, "pairs_both": 6191, "path_pairs_hdr_present": 6191, "path_pairs_hdr_absent": 6281}
path rules (PR-file pairs): {"generated_dir": 19464, "dot_gen": 6900, "protobuf_go": 3639, "dart_build_runner": 2414, "dot_generated": 2404, "go_underscore_gen": 1417, "dotnet_designer": 934, "protobuf_js_ts": 841, "protobuf_py": 749, "k8s_zz_generated": 632, "dotnet_g_cs": 540, "sqlc_go": 380, "protobuf_swift": 23, "protobuf_cpp": 17}
edited w/o source by rule: {"generated_dir": 4308, "dot_gen": 3635, "header_only": 3201, "dart_build_runner": 746, "dot_generated": 712, "go_underscore_gen": 311, "protobuf_go": 249, "dotnet_g_cs": 75, "k8s_zz_generated": 32, "protobuf_js_ts": 27, "dotnet_designer": 23, "protobuf_py": 19, "protobuf_cpp": 11, "sqlc_go": 5, "protobuf_swift": 4}
repos edit-gen: 1075 repos edit-gen w/o src: 576
