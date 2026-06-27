#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_FREECAD_CMD = os.environ.get("FREECAD_CMD", "FreeCADCmd")


@dataclass
class PromptRecord:
    sample_id: str
    target_code: str
    level: str
    prompt: str
    raw: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Execute one-shot Codex-MCP FreeCAD scripts under the open-loop "
            "protocol. This runner does not generate or repair code."
        )
    )
    parser.add_argument("--manifest-jsonl", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--freecad-cmd", default=DEFAULT_FREECAD_CMD)
    parser.add_argument("--execution-mode", choices=["freecadcmd", "mcp"], default="freecadcmd")
    parser.add_argument("--mcp-host", default="127.0.0.1")
    parser.add_argument("--mcp-port", type=int, default=9876)
    parser.add_argument("--protocol", default="open_loop_one_shot")
    parser.add_argument("--sample-ids", nargs="*")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--init-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def parse_manifest(path: Path) -> list[PromptRecord]:
    records: list[PromptRecord] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        obj = json.loads(raw_line)
        records.append(
            PromptRecord(
                sample_id=str(obj["sample_id"]),
                target_code=str(obj.get("target_code", obj.get("uid", ""))),
                level=str(obj.get("level", obj.get("difficulty", ""))),
                prompt=str(obj["prompt"]).strip(),
                raw=obj,
            )
        )
    if not records:
        raise ValueError(f"No records found in {path}")
    return records


def ensure_dirs(root: Path) -> dict[str, Path]:
    dirs = {
        "freecad_py": root / "freecad_py",
        "wrapped_py": root / "wrapped_py",
        "stl": root / "stl",
        "step": root / "step",
        "fcstd": root / "fcstd",
        "logs": root / "logs",
        "metadata": root / "metadata",
        "prompts": root / "prompts",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def write_prompt_files(records: list[PromptRecord], dirs: dict[str, Path]) -> None:
    for record in records:
        prompt_path = dirs["prompts"] / f"{record.sample_id}.txt"
        if prompt_path.exists():
            continue
        prompt_path.write_text(record.prompt + "\n", encoding="utf-8")


def build_wrapper(model_code: str, step_path: Path, stl_path: Path, fcstd_path: Path) -> str:
    step_literal = str(step_path)
    stl_literal = str(stl_path)
    fcstd_literal = str(fcstd_path)
    return "\n".join(
        [
            "import os",
            "import FreeCAD as App",
            "import Part",
            "import Mesh",
            "",
            "if App.ActiveDocument is None:",
            "    App.newDocument('CodexMCPDoc')",
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
            f"step_path = r'{step_literal}'",
            f"stl_path = r'{stl_literal}'",
            f"fcstd_path = r'{fcstd_literal}'",
            "os.makedirs(os.path.dirname(step_path), exist_ok=True)",
            "os.makedirs(os.path.dirname(stl_path), exist_ok=True)",
            "os.makedirs(os.path.dirname(fcstd_path), exist_ok=True)",
            "Part.export([export_obj], step_path)",
            "Mesh.export([export_obj], stl_path)",
            "doc.saveAs(fcstd_path)",
            "doc.recompute()",
            "",
        ]
    )


def run_freecad(freecad_cmd: str, script_path: Path, log_path: Path) -> int:
    proc = subprocess.run(
        [freecad_cmd, str(script_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log_path.write_text(
        f"STDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}",
        encoding="utf-8",
    )
    return int(proc.returncode)


def send_mcp_command(host: str, port: int, command: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(command, ensure_ascii=False).encode("utf-8")
    with socket.create_connection((host, port), timeout=20) as sock:
        sock.settimeout(120)
        sock.sendall(payload)
        chunks: list[bytes] = []
        while True:
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                if chunks:
                    break
                raise
            if not chunk:
                break
            chunks.append(chunk)
            sock.settimeout(1)
    raw = b"".join(chunks).decode("utf-8", errors="replace")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"result": "decode_error", "raw": raw}


def run_mcp(host: str, port: int, sample_id: str, wrapper_path: Path, log_path: Path) -> tuple[int, dict[str, Any]]:
    macro_name = f"CodexMCP_{sample_id}"
    code = wrapper_path.read_text(encoding="utf-8")
    update_response = send_mcp_command(
        host,
        port,
        {"type": "update_macro", "params": {"macro_name": macro_name, "code": code}},
    )
    run_response = send_mcp_command(
        host,
        port,
        {
            "type": "run_macro",
            "params": {
                "macro_path": f"{macro_name}.FCMacro",
                "params": {"doc_name": macro_name.replace("-", "_")},
            },
        },
    )
    payload = {
        "macro_name": macro_name,
        "update_response": update_response,
        "run_response": run_response,
    }
    log_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return (0 if run_response.get("result") == "success" else 1), payload


def run_record(
    record: PromptRecord,
    dirs: dict[str, Path],
    freecad_cmd: str,
    resume: bool,
    execution_mode: str,
    mcp_host: str,
    mcp_port: int,
    protocol: str,
) -> dict[str, Any]:
    code_path = dirs["freecad_py"] / f"{record.sample_id}.py"
    wrapper_path = dirs["wrapped_py"] / f"{record.sample_id}.py"
    step_path = dirs["step"] / f"{record.sample_id}.step"
    stl_path = dirs["stl"] / f"{record.sample_id}.stl"
    fcstd_path = dirs["fcstd"] / f"{record.sample_id}.FCStd"
    log_path = dirs["logs"] / f"{record.sample_id}.log"
    metadata_path = dirs["metadata"] / f"{record.sample_id}.json"

    metadata: dict[str, Any] = {
        "sample_id": record.sample_id,
        "target_code": record.target_code,
        "level": record.level,
        "prompt": record.prompt,
        "method": "Codex-MCP",
        "protocol": protocol,
        "attempt_policy": "single_generation_single_execution_no_repair",
        "freecad_cmd": freecad_cmd,
        "execution_mode": execution_mode,
        "mcp_host": mcp_host,
        "mcp_port": mcp_port,
        "code_path": str(code_path),
        "wrapper_path": str(wrapper_path),
        "step_path": str(step_path),
        "stl_path": str(stl_path),
        "fcstd_path": str(fcstd_path),
        "log_path": str(log_path),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }

    if not code_path.exists():
        metadata["status"] = "missing_code"
        metadata["completed_at"] = datetime.now(timezone.utc).isoformat()
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return metadata

    if resume and stl_path.exists() and step_path.exists():
        metadata["status"] = "skipped_existing"
        metadata["completed_at"] = datetime.now(timezone.utc).isoformat()
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return metadata

    model_code = code_path.read_text(encoding="utf-8")
    wrapper_path.write_text(build_wrapper(model_code, step_path, stl_path, fcstd_path), encoding="utf-8")
    mcp_payload: dict[str, Any] | None = None
    if execution_mode == "mcp":
        returncode, mcp_payload = run_mcp(mcp_host, mcp_port, record.sample_id, wrapper_path, log_path)
    else:
        returncode = run_freecad(freecad_cmd, wrapper_path, log_path)
    metadata["returncode"] = returncode
    if mcp_payload is not None:
        metadata["mcp_payload"] = mcp_payload
    metadata["step_exists"] = step_path.exists()
    metadata["stl_exists"] = stl_path.exists()
    metadata["fcstd_exists"] = fcstd_path.exists()
    metadata["status"] = "success" if returncode == 0 and step_path.exists() and stl_path.exists() else "failed"
    metadata["completed_at"] = datetime.now(timezone.utc).isoformat()
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest_jsonl)
    output_root = Path(args.output_root)
    freecad_cmd = args.freecad_cmd

    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    if args.execution_mode == "freecadcmd" and not Path(freecad_cmd).exists():
        raise SystemExit(f"FreeCADCmd not found: {freecad_cmd}")

    records = parse_manifest(manifest_path)
    if args.sample_ids:
        wanted = set(args.sample_ids)
        records = [record for record in records if record.sample_id in wanted]
    if args.limit is not None:
        records = records[: args.limit]

    dirs = ensure_dirs(output_root)
    shutil.copy2(manifest_path, output_root / manifest_path.name)
    write_prompt_files(records, dirs)

    summary: dict[str, Any] = {
        "method": "Codex-MCP",
        "protocol": args.protocol,
        "manifest": str(manifest_path),
        "output_root": str(output_root),
        "freecad_cmd": freecad_cmd,
        "execution_mode": args.execution_mode,
        "mcp_host": args.mcp_host,
        "mcp_port": args.mcp_port,
        "record_count": len(records),
        "init_only": bool(args.init_only),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "results": [],
    }

    if not args.init_only:
        for index, record in enumerate(records, start=1):
            print(f"[{index}/{len(records)}] {record.sample_id}")
            summary["results"].append(
                run_record(
                    record,
                    dirs,
                    freecad_cmd,
                    args.resume,
                    args.execution_mode,
                    args.mcp_host,
                    args.mcp_port,
                    args.protocol,
                )
            )

    summary["completed_at"] = datetime.now(timezone.utc).isoformat()
    summary["success_count"] = sum(1 for item in summary["results"] if item.get("status") == "success")
    summary["failed_count"] = sum(1 for item in summary["results"] if item.get("status") == "failed")
    summary["missing_code_count"] = sum(1 for item in summary["results"] if item.get("status") == "missing_code")
    (output_root / "codex_mcp_freecad_runner_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
