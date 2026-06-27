# Dimension 1 Geometry Final Summary

Process compile rate is not taken from the best-of directory. Open-loop Workflow methods use four full rounds (`success/480`). Close-loop Workflow methods use the attempt-based feedback-log rule. Geometry and distribution metrics use per-sample best-of outputs.

| Method | Cohort | Compile (%) | Best-of valid | Mean CD | Median CD | Mean HD | MMD | COV (%) | JSD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek | Open-loop Workflow | 77.08 | 118/120 | 0.026440 | 0.022717 | 0.124181 | 0.021277 | 61.67 | 0.036687 |
| Codex-MCP | Open-loop Workflow | 100.00 | 120/120 | 0.029088 | 0.025758 | 0.125260 | 0.027244 | 51.67 | 0.041403 |
| Claude | Close-loop Workflow | 94.14 | 120/120 | 0.034785 | 0.025263 | 0.141544 | 0.024553 | 62.50 | 0.037561 |
| ChatGPT | Close-loop Workflow | 90.12 | 118/120 | 0.036417 | 0.026940 | 0.136991 | 0.023325 | 57.50 | 0.039572 |
| Qwen | Close-loop Workflow | 96.62 | 120/120 | 0.039942 | 0.029084 | 0.146493 | 0.023788 | 60.83 | 0.040208 |
| Gemini | Close-loop Workflow | 78.07 | 116/120 | 0.042068 | 0.027444 | 0.157122 | 0.025021 | 58.33 | 0.042109 |
| Text-to-CadQuery | Open-loop Workflow | 77.71 | 115/120 | 0.069661 | 0.061513 | 0.236708 | 0.042147 | 45.00 | 0.064197 |
| Text2CAD | Open-loop Workflow | 95.83 | 120/120 | 0.076520 | 0.067949 | 0.261296 | 0.044479 | 46.67 | 0.080056 |
