#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deepseek_api_client import extract_text, request_json


PROMPT_HEADER_RE = re.compile(r"^\[(UB40-[BIE]\d{3})\]\s+\[(UB40-T\d{3})\]\s*$")
CODE_FENCE_RE = re.compile(r"^```(?:python)?\s*|\s*```$", re.MULTILINE)

DEFAULT_SYSTEM_PROMPT = textwrap.dedent(
    """
    You are a FreeCAD modeling code generator.
    Your only task is to generate a single FreeCAD Python program from the user's CAD prompt.

    Follow these rules strictly:
    1. Output valid JSON only.
    2. The JSON object must contain exactly one key: "python_code".
    3. The value of "python_code" must be executable FreeCAD Python code as a plain string.
    4. Do not include markdown code fences.
    5. Prefer stable, direct, reproducible FreeCAD APIs and prefer Part primitives and boolean operations.
    6. Do not rely on GUI clicking or manual interaction.
    7. Reuse the active document if one exists; otherwise create one.
    8. Unless otherwise specified, interpret dimensions in millimeters.
    9. If the prompt is ambiguous, choose one conservative best-effort interpretation and still return code.
    10. The code should create a final solid model and leave it accessible as either:
       - a variable named result_shape containing a Part.Shape, or
       - a variable named result_obj containing a document object with a Shape.
    11. If you cannot reasonably create one of those variables, still create the model in the active document so the last visible shape object can be exported.
    12. The code must end with App.ActiveDocument.recompute().
    """
).strip()


@dataclass
class PromptRecord:
    sample_id: str
    target_code: str
    prompt: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DeepSeek prompt-to-FreeCAD batch generation.")
    parser.add_argument("--prompt-file")
    parser.add_argument("--manifest-jsonl")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--freecad-cmd", default=os.environ.get("FREECAD_CMD", "FreeCADCmd"))
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=12000)
    parser.add_argument("--sample-ids", nargs="*")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def parse_prompt_file(path: Path) -> list[PromptRecord]:
    lines = path.read_text(encoding="utf-8").splitlines()
    records: list[PromptRecord] = []
    i = 0
    while i < len(lines):
        match = PROMPT_HEADER_RE.match(lines[i].strip())
        if not match:
            i += 1
            continue
        sample_id = match.group(1)
        target_code = match.group(2)
        i += 1
        prompt_lines: list[str] = []
        while i < len(lines) and lines[i].strip():
            prompt_lines.append(lines[i].rstrip())
            i += 1
        prompt = " ".join(line.strip() for line in prompt_lines).strip()
        if prompt:
            records.append(PromptRecord(sample_id=sample_id, target_code=target_code, prompt=prompt))
        i += 1
    if not records:
        raise ValueError(f"No prompt records found in {path}")
    return records


def parse_manifest_jsonl(path: Path) -> list[PromptRecord]:
    records: list[PromptRecord] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        obj = json.loads(raw)
        records.append(
            PromptRecord(
                sample_id=str(obj["sample_id"]),
                target_code=str(obj.get("target_code", obj.get("uid", ""))),
                prompt=str(obj["prompt"]).strip(),
            )
        )
    if not records:
        raise ValueError(f"No prompt records found in {path}")
    return records


def sanitize_python_code(text: str) -> str:
    text = text.strip()
    if text.startswith("{"):
        try:
            payload = json.loads(text)
            text = str(payload.get("python_code", "")).strip()
        except json.JSONDecodeError:
            pass
    text = CODE_FENCE_RE.sub("", text).strip()
    return text


def build_user_prompt(cad_prompt: str) -> str:
    return (
        "Return json only.\n"
        "Create FreeCAD Python code for this CAD prompt:\n\n"
        f"{cad_prompt}\n"
    )


def call_deepseek(model: str, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    return request_json("POST", "/chat/completions", payload)


def build_wrapper(model_code: str, stl_path: Path, export_fcstd: bool = False) -> str:
    stl_literal = str(stl_path).replace("\\", "\\\\")
    fcstd_literal = str(stl_path.with_suffix(".FCStd")).replace("\\", "\\\\")
    parts = [
        "import os",
        "import FreeCAD as App",
        "import Part",
        "import Mesh",
        "import MeshPart",
        "",
        "if App.ActiveDocument is None:",
        "    App.newDocument('DeepSeekDoc')",
        "",
        model_code.rstrip(),
        "",
        "doc = App.ActiveDocument",
        "if doc is None:",
        "    raise RuntimeError('No active document after model code execution.')",
        "",
        "doc.recompute()",
        "",
        "export_obj = None",
        "if 'result_obj' in globals() and getattr(result_obj, 'Shape', None) is not None:",
        "    export_obj = result_obj",
        "elif 'result_shape' in globals() and isinstance(result_shape, Part.Shape):",
        "    export_obj = doc.addObject('Part::Feature', 'ResultShape')",
        "    export_obj.Shape = result_shape",
        "    doc.recompute()",
        "else:",
        "    for candidate in reversed(list(doc.Objects)):",
        "        if getattr(candidate, 'Shape', None) is not None and not candidate.Shape.isNull():",
        "            export_obj = candidate",
        "            break",
        "",
        "if export_obj is None or getattr(export_obj, 'Shape', None) is None or export_obj.Shape.isNull():",
        "    raise RuntimeError('No exportable solid object found after model code execution.')",
        "",
        f"stl_path = r'{stl_literal}'",
        "os.makedirs(os.path.dirname(stl_path), exist_ok=True)",
        "Mesh.export([export_obj], stl_path)",
        "doc.recompute()",
        "",
        f"if {str(export_fcstd)}:",
        f"    doc.saveAs(r'{fcstd_literal}')",
        "",
    ]
    return "\n".join(parts)


def run_freecad(freecad_cmd: str, script_path: Path, log_path: Path) -> tuple[int, str]:
    command = [freecad_cmd, str(script_path)]
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    combined = f"STDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}"
    log_path.write_text(combined, encoding="utf-8")
    return proc.returncode, combined


def ensure_dirs(root: Path) -> dict[str, Path]:
    dirs = {
        "raw_response": root / "raw_response",
        "freecad_py": root / "freecad_py",
        "wrapped_py": root / "wrapped_py",
        "stl": root / "stl",
        "logs": root / "logs",
        "metadata": root / "metadata",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root)
    freecad_cmd = args.freecad_cmd

    if not Path(freecad_cmd).exists():
        raise SystemExit(f"FreeCADCmd not found: {freecad_cmd}")
    if bool(args.prompt_file) == bool(args.manifest_jsonl):
        raise SystemExit("Specify exactly one of --prompt-file or --manifest-jsonl")

    dirs = ensure_dirs(output_root)
    if args.prompt_file:
        records = parse_prompt_file(Path(args.prompt_file))
        source_descriptor = str(Path(args.prompt_file))
    else:
        records = parse_manifest_jsonl(Path(args.manifest_jsonl))
        source_descriptor = str(Path(args.manifest_jsonl))
    if args.sample_ids:
        wanted = set(args.sample_ids)
        records = [r for r in records if r.sample_id in wanted]
    if args.limit is not None:
        records = records[: args.limit]

    run_summary: list[dict[str, Any]] = []

    for record in records:
        sample_id = record.sample_id
        raw_json_path = dirs["raw_response"] / f"{sample_id}.json"
        raw_text_path = dirs["raw_response"] / f"{sample_id}.txt"
        model_py_path = dirs["freecad_py"] / f"{sample_id}.py"
        wrapped_py_path = dirs["wrapped_py"] / f"{sample_id}.py"
        stl_path = dirs["stl"] / f"{sample_id}.stl"
        log_path = dirs["logs"] / f"{sample_id}.log"
        metadata_path = dirs["metadata"] / f"{sample_id}.json"

        if args.resume and stl_path.exists():
            run_summary.append({
                "sample_id": sample_id,
                "target_code": record.target_code,
                "status": "skipped_existing_stl",
            })
            continue

        result = call_deepseek(
            model=args.model,
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            user_prompt=build_user_prompt(record.prompt),
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        raw_json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        raw_text = extract_text(result)
        raw_text_path.write_text(raw_text, encoding="utf-8")

        model_code = sanitize_python_code(raw_text)
        model_py_path.write_text(model_code, encoding="utf-8")
        wrapped_code = build_wrapper(model_code, stl_path)
        wrapped_py_path.write_text(wrapped_code, encoding="utf-8")

        return_code, _ = run_freecad(freecad_cmd, wrapped_py_path, log_path)
        ok = return_code == 0 and stl_path.exists()

        metadata = {
            "sample_id": sample_id,
            "target_code": record.target_code,
            "prompt": record.prompt,
            "model": args.model,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "freecad_cmd": freecad_cmd,
            "return_code": return_code,
            "stl_exists": stl_path.exists(),
            "status": "ok" if ok else "failed",
        }
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        run_summary.append(metadata)
        print(f"[{sample_id}] {'ok' if ok else 'failed'}")

    summary_path = output_root / "deepseek_freecad_batch_summary.json"
    payload = {
        "source": source_descriptor,
        "records": run_summary,
    }
    summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[done] wrote summary to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
