#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
PROMPT_DIR = REPO_ROOT / "data" / "manifests"
RESULT_BASE = REPO_ROOT / "runs" / "codex_mcp_open_loop"
GENERATOR = SCRIPT_DIR / "codex_mcp_generate_oneshot_scripts.py"
RUNNER = SCRIPT_DIR / "codex_mcp_freecad_runner.py"

ROUNDS = [
    {
        "round_dir": "Iteration1",
        "manifest": PROMPT_DIR / "open_loop_prompt_manifest_retained120_iteration1.jsonl",
        "protocol": "open_loop_iteration1",
    },
    {
        "round_dir": "Iteration2",
        "manifest": PROMPT_DIR / "open_loop_prompt_manifest_retained120_iteration2.jsonl",
        "protocol": "open_loop_iteration2",
    },
    {
        "round_dir": "Iteration3",
        "manifest": PROMPT_DIR / "open_loop_prompt_manifest_retained120_iteration3.jsonl",
        "protocol": "open_loop_iteration3",
    },
]


def run_command(args: list[str], log_file: Path) -> int:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as log:
        log.write("\n\n")
        log.write("=" * 80 + "\n")
        log.write(datetime.now(timezone.utc).isoformat() + "\n")
        log.write(" ".join(args) + "\n")
        log.flush()
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            log.write(line)
            log.flush()
        return proc.wait()


def count_outputs(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name in ["freecad_py", "wrapped_py", "step", "stl", "fcstd", "logs", "metadata", "prompts"]:
        path = root / name
        if not path.exists():
            counts[name] = 0
            continue
        if name == "fcstd":
            counts[name] = len(list(path.glob("*.FCStd")))
        else:
            counts[name] = len([p for p in path.iterdir() if p.is_file()])
    return counts


def main() -> int:
    overall = {
        "method": "Codex-MCP",
        "track": "Open-loop Workflow",
        "rounds": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    for item in ROUNDS:
        manifest = item["manifest"]
        output_root = RESULT_BASE / item["round_dir"] / "Codex-MCP"
        log_file = output_root / "metadata" / "codex_mcp_round_orchestration.log"
        output_root.mkdir(parents=True, exist_ok=True)

        if not manifest.exists():
            overall["rounds"].append(
                {
                    "round": item["round_dir"],
                    "status": "missing_manifest",
                    "manifest": str(manifest),
                    "output_root": str(output_root),
                }
            )
            break

        generate_rc = run_command(
            [
                sys.executable,
                str(GENERATOR),
                "--manifest-jsonl",
                str(manifest),
                "--output-root",
                str(output_root),
                "--protocol",
                item["protocol"],
            ],
            log_file,
        )
        if generate_rc != 0:
            overall["rounds"].append(
                {
                    "round": item["round_dir"],
                    "status": "generation_failed",
                    "returncode": generate_rc,
                    "manifest": str(manifest),
                    "output_root": str(output_root),
                }
            )
            break

        run_rc = run_command(
            [
                sys.executable,
                str(RUNNER),
                "--manifest-jsonl",
                str(manifest),
                "--output-root",
                str(output_root),
                "--execution-mode",
                "mcp",
                "--protocol",
                item["protocol"],
            ],
            log_file,
        )

        round_summary = {
            "round": item["round_dir"],
            "protocol": item["protocol"],
            "manifest": str(manifest),
            "output_root": str(output_root),
            "generation_returncode": generate_rc,
            "runner_returncode": run_rc,
            "counts": count_outputs(output_root),
            "status": "success" if run_rc == 0 else "runner_failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        overall["rounds"].append(round_summary)
        (output_root / "metadata" / "codex_mcp_round_orchestration_summary.json").write_text(
            json.dumps(round_summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        if run_rc != 0:
            break

    overall["completed_at"] = datetime.now(timezone.utc).isoformat()
    summary_path = RESULT_BASE / "codex_mcp_remaining_rounds_summary.json"
    summary_path.write_text(json.dumps(overall, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if all(round_item.get("status") == "success" for round_item in overall["rounds"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
