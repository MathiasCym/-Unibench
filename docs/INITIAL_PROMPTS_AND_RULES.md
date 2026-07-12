# Initial Prompts and Final Protocol Rules

Last protocol update: 2026-07-13

This document records the initial prompts and protocol rules needed to reproduce the current Unibench setup. It separates final benchmark rules from exploratory study evidence.

## Final Core Metrics

The final Unibench core metrics are:

- Geometry accuracy: Compile Rate, Mean CD, Watertight Rate, EECM.
- Semantic fidelity: AI Semantic Fidelity Score using a fixed checklist and AI scoring prompt.
- Prompt robustness: CD Variation and Variant Compile Rate.

Metrics such as Median CD, HD, MMD, COV, JSD, HD Variation, and human semantic scoring remain useful for exploratory interpretation and Step 4 consolidation evidence, but they are not final core metrics.

## Prompt Screening Rule

Prompt-level screening uses:

- Mean prompt length.
- Mean compile failure.
- Geometry error index.

Compile Failure is used only for prompt-level screening. Formal benchmark metrics use Compile Rate.

## Geometry Accuracy Generation Initial Prompt

```text
You are now a FreeCAD modeling code generator. Your only task is to generate a single piece of FreeCAD Python code, based on the geometry description I provide next, to create the corresponding CAD model. Follow these rules strictly:
1. Output only one final result. Do not provide multiple options.
2. Output only Python code. Do not include explanations, commentary, titles, introductions, conclusions, or Markdown code fences unless I explicitly ask for them.
3. The code must be as directly executable as possible in FreeCAD, either as a macro or in the FreeCAD Python console.
4. Prefer stable, direct, and reproducible FreeCAD Python APIs. Prioritize the use of the Part module, primitive solids, sketches only when necessary, extrusion, boolean operations, fillets, chamfers, mirrors, arrays, translations, and rotations.
5. Do not rely on GUI interaction or any manual clicking steps.
6. Reuse the active document if one already exists; otherwise create a new document.
7. The code must end with App.ActiveDocument.recompute().
8. The model should result in one clear final solid object. Intermediate objects may exist, but the final result must be clear and usable.
9. Unless I explicitly specify otherwise, interpret all dimensions in millimeters.
10. If the description contains minor ambiguity, choose the most direct, conservative, and easiest-to-implement geometric interpretation. Do not invent extra structures.
11. Do not output placeholders. Do not write "TODO". Do not omit key parameters.
12. Even if the description is not fully sufficient to determine a unique model, still output one single best-effort code result. Do not ask follow-up questions. Do not provide alternatives. Your goal is not to explain but to generate code. From my next message onward, I will provide a geometry or modeling request, and you should respond directly with FreeCAD Python code.
```

## AI Semantic Scoring Initial Prompt

```text
Enter four binary digits in order: Validity Structure Features Geometry.

Examples: 1111, 1011, 0000.

If validity = 0, the remaining three digits should also be 0.

Scoring rules:

1. Validity: the output is a recognizable 3D object rather than a collapsed 2D / broken fragment.
2. Structure: the main body and major part arrangement are basically correct.
3. Features: key holes, slots, bosses, openings, flanges, arms, or other salient features are basically correct.
4. Geometry: visible proportions, relative placement, and overall appearance are basically reasonable.
```

## Semantic Fidelity Use in the Final Benchmark

During the exploratory study, both human and AI scoring were recorded to check whether the fixed AI scoring prompt was usable. In the final Unibench protocol, human scoring is not required. The retained semantic-fidelity component is the fixed checklist and AI scoring prompt applied to rendered views.

## Step 4 Consolidation Rule

Step 4 uses the broader exploratory study results to decide which components enter the final benchmark. The four linked aspects are:

1. Workflow feasibility.
2. Prompt suitability.
3. Metric discriminability.
4. Protocol consolidation.

The Step 4 results explain how and why components are retained or treated as supplementary evidence. The final Unibench section should describe only the final components and metrics.
