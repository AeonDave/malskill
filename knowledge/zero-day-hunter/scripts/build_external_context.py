#!/usr/bin/env python3
"""Build a compact external context pack for zero-day hunting.

Queries Tavily for public context about a project, framework, or component and
writes a concise Markdown or JSON bundle that can be passed into scan_zero_day.py.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

TAVILY_API_URL = "https://api.tavily.com/search"
DEFAULT_MAX_RESULTS = 5


def read_dotenv(dotenv_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not dotenv_path.exists():
        return values
    for raw_line in dotenv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_tavily_key(workspace_root: Path) -> str:
    env_values = read_dotenv(workspace_root / ".env")
    return os.environ.get("TAVILY_API_KEY") or env_values.get("TAVILY_API_KEY", "")


def search_tavily(api_key: str, query: str, max_results: int) -> dict[str, Any]:
    payload = {
        "api_key": api_key,
        "query": query,
        "topic": "general",
        "search_depth": "advanced",
        "max_results": max_results,
        "include_raw_content": True,
        "include_images": False,
    }
    request = urllib.request.Request(
        TAVILY_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def compact_results(query: str, data: dict[str, Any]) -> dict[str, Any]:
    raw_results = data.get("results", [])
    compact: list[dict[str, Any]] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        compact.append(
            {
                "title": str(item.get("title", "")).strip(),
                "url": str(item.get("url", "")).strip(),
                "score": item.get("score", 0),
                "content": str(item.get("content", "")).strip(),
                "raw_excerpt": str(item.get("raw_content", "")).strip()[:1500],
            }
        )
    return {"query": query, "results": compact}


def render_markdown(bundle: dict[str, Any]) -> str:
    lines = [
        "# External Context Pack",
        "",
        f"- Query: {bundle.get('query', '')}",
        f"- Results: {len(bundle.get('results', []))}",
        "",
        "Use this context only to improve local review hypotheses. Verify everything against source code.",
        "",
    ]
    for index, item in enumerate(bundle.get("results", []), start=1):
        lines.extend(
            [
                f"## Result {index}: {item.get('title', 'Untitled')}",
                "",
                f"- URL: {item.get('url', '')}",
                f"- Score: {item.get('score', 0)}",
                "",
                "### Summary",
                "",
                item.get("content", "") or "(no summary)",
                "",
            ]
        )
        excerpt = item.get("raw_excerpt", "")
        if excerpt:
            lines.extend(["### Raw excerpt", "", excerpt, ""])
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a compact external context pack using Tavily.")
    parser.add_argument("query", help="Project, framework, or component query")
    parser.add_argument("--workspace-root", default=".", help="Workspace root used to load .env")
    parser.add_argument("--output", default=None, help="Output file (.md or .json)")
    parser.add_argument("--max-results", type=int, default=DEFAULT_MAX_RESULTS, help=f"Max Tavily results (default: {DEFAULT_MAX_RESULTS})")
    args = parser.parse_args()

    workspace_root = Path(args.workspace_root).resolve()
    api_key = load_tavily_key(workspace_root)
    if not api_key:
        print("Failure: TAVILY_API_KEY is not set.", file=sys.stderr)
        return 1

    try:
        data = search_tavily(api_key, args.query, args.max_results)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        print(f"Failure: Tavily request failed: {exc}", file=sys.stderr)
        return 1

    bundle = compact_results(args.query, data)
    output_path = Path(args.output).resolve() if args.output else (workspace_root / "external-context.md")

    if output_path.suffix.lower() == ".json":
        output_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    else:
        output_path.write_text(render_markdown(bundle), encoding="utf-8")

    print(f"Success: wrote external context to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
