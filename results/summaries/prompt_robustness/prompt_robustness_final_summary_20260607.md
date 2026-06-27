# Prompt Robustness Benchmark Summary

Scope: 40 intermediate prompts, three prompt variants per target: `original`, `WO` (word-order variant), and `RD` (redundant wording variant).

Main UniBench signal: each variant is compared with the paired reference mesh. `mean_cd_std_to_reference` is the average within-sample standard deviation of reference-aligned Chamfer distance across the three variants; lower is more stable.

Supplementary pairwise signal: generated outputs from the same target are compared against each other over `original-WO`, `original-RD`, and `WO-RD`; lower pairwise CD is more stable. Missing or invalid variants reduce compile/pair rates but are not inserted into the distance average.

| Method | Variant success | Compile (%) | CD std to ref | HD std to ref | Pair success | Mean pairwise CD |
|---|---:|---:|---:|---:|---:|---:|
| Codex-MCP | 120/120 | 100.00 | 0.003683 | 0.010702 | 120/120 | 0.015490 |
| ChatGPT | 118/120 | 98.33 | 0.003795 | 0.017870 | 116/120 | 0.017671 |
| DeepSeek | 95/120 | 79.17 | 0.004187 | 0.017475 | 79/120 | 0.019629 |
| Claude | 115/120 | 95.83 | 0.006791 | 0.027939 | 110/120 | 0.023170 |
| Qwen | 115/120 | 95.83 | 0.008966 | 0.035906 | 112/120 | 0.023353 |
| Gemini | 113/120 | 94.17 | 0.009925 | 0.038282 | 109/120 | 0.028074 |
| CadQuery | 93/120 | 77.50 | 0.024846 | 0.066481 | 81/120 | 0.072358 |
| Text2CAD | 113/120 | 94.17 | 0.027693 | 0.073596 | 107/120 | 0.073211 |

Source results: `full prompt-robustness output tree not included in release`.
