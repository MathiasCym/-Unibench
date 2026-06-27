#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "DEEPSEEK_API_KEY is not set. Set it in the current PowerShell window first."
        )
    return key


def get_base_url() -> str:
    return os.environ.get("DEEPSEEK_API_BASE", DEFAULT_BASE_URL).rstrip("/")


def request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{get_base_url()}{path}"
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Accept": "application/json",
    }
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"HTTP {exc.code} {exc.reason}\nURL: {url}\nResponse:\n{detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Network error while calling {url}: {exc}") from exc


def maybe_write_json(data: dict[str, Any], output_dir: str | None, filename: str) -> None:
    if not output_dir:
        return
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / filename).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def cmd_list_models(args: argparse.Namespace) -> int:
    data = request_json("GET", "/models")
    maybe_write_json(data, args.output_dir, "models.json")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def cmd_auth_check(args: argparse.Namespace) -> int:
    data = request_json("GET", "/models")
    maybe_write_json(data, args.output_dir, "auth_check_models.json")
    models = [m.get("id", "") for m in data.get("data", [])]
    print(json.dumps({
        "ok": True,
        "base_url": get_base_url(),
        "model_count": len(models),
        "models": models,
        "checked_at": utc_now(),
    }, indent=2, ensure_ascii=False))
    return 0


def extract_text(result: dict[str, Any]) -> str:
    choices = result.get("choices") or []
    if not choices:
        return ""
    first = choices[0] or {}
    message = first.get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(p for p in parts if p)
    return ""


def cmd_chat(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {
        "model": args.model,
        "messages": [],
        "stream": False,
    }
    if args.temperature is not None:
        payload["temperature"] = args.temperature
    if args.max_tokens is not None:
        payload["max_tokens"] = args.max_tokens
    if args.response_format == "json":
        payload["response_format"] = {"type": "json_object"}

    if args.system:
        payload["messages"].append({"role": "system", "content": args.system})
    payload["messages"].append({"role": "user", "content": args.prompt})

    result = request_json("POST", "/chat/completions", payload)
    maybe_write_json(result, args.output_dir, "chat_response.json")
    text = extract_text(result)
    if args.output_dir:
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "response.txt").write_text(text, encoding="utf-8")
    print(text if text else json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Zero-dependency DeepSeek API client")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_auth = sub.add_parser("auth-check", help="Verify API access by listing models")
    p_auth.add_argument("--output-dir")
    p_auth.set_defaults(func=cmd_auth_check)

    p_models = sub.add_parser("list-models", help="List available DeepSeek models")
    p_models.add_argument("--output-dir")
    p_models.set_defaults(func=cmd_list_models)

    p_chat = sub.add_parser("chat", help="Run one chat completion")
    p_chat.add_argument("--prompt", required=True)
    p_chat.add_argument("--system", default="You are a helpful assistant.")
    p_chat.add_argument("--model", default=DEFAULT_MODEL)
    p_chat.add_argument("--temperature", type=float)
    p_chat.add_argument("--max-tokens", type=int)
    p_chat.add_argument("--response-format", choices=["text", "json"], default="text")
    p_chat.add_argument("--output-dir")
    p_chat.set_defaults(func=cmd_chat)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
