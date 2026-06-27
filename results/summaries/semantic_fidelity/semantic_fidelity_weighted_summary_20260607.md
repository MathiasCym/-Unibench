# Semantic Fidelity Weighted Summary

Source directory: `full semantic-fidelity image workspace not included in release`

Official methods: `Text2CAD`, `Text-to-CadQuery`, `DeepSeek`, `Codex-MCP`, `ChatGPT`, `Claude`, `Gemini`, `Qwen`.

Scoring rule:
- Each sample uses a four-bit score in the order `Validity`, `Structure`, `Features`, `Geometry`.
- Sample score = number of positive bits / 4.
- Method manual score = mean sample score over 120 one-shot outputs.
- Method AI score = mean sample score over 120 one-shot outputs.
- Final semantic-fidelity score = `0.5 * manual_mean + 0.5 * ai_mean`.

| Method | Manual | AI | Final | Final (%) |
|---|---:|---:|---:|---:|
| Claude | 0.843750 | 0.895833 | 0.869792 | 86.98 |
| Codex-MCP | 0.843750 | 0.881250 | 0.862500 | 86.25 |
| ChatGPT | 0.783333 | 0.845833 | 0.814583 | 81.46 |
| Qwen | 0.781250 | 0.806250 | 0.793750 | 79.38 |
| DeepSeek | 0.616667 | 0.670833 | 0.643750 | 64.38 |
| Gemini | 0.616667 | 0.660417 | 0.638542 | 63.85 |
| Text2CAD | 0.329167 | 0.331250 | 0.330208 | 33.02 |
| Text-to-CadQuery | 0.304167 | 0.329167 | 0.316667 | 31.67 |

Component columns and point totals are stored in `semantic_fidelity_weighted_summary_20260607.csv`.
File validation is stored in `semantic_fidelity_scoring_file_validation_20260607.csv`.
