#!/usr/bin/env python3
"""LLM-assisted scanner for likely zero-day candidates.

The script performs three steps per file:
1. Generate concise security context
2. Ask for structured candidate findings
3. Optionally run one skeptical review pass per finding with local grep evidence

The implementation is intentionally compact and standard-library friendly.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_MODEL = "gpt-5.4-nano"
DEFAULT_MAX_CHARS = 160_000
DEFAULT_PARALLEL = 6
DEFAULT_EXTENSIONS = {
    ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hxx",
    ".go", ".rs", ".py", ".java", ".js", ".ts", ".php", ".cs",
}
SEVERITY_ORDER = ["critical", "high", "medium", "low", "informational"]
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

CONTEXT_PROMPT = """You are preparing a security-oriented briefing for a code reviewer.
Summarize:
- what the file appears to do
- likely trust boundaries and attacker-controlled inputs
- how any provided external project context changes the review focus
- buffers, lengths, counters, allocators, or deserializers worth auditing
- functions that look externally reachable
- bug classes most worth checking in this file
Keep the answer compact and evidence-focused. Do not claim a vulnerability yet."""

FINDINGS_PROMPT = """You are reviewing a single source file for plausible zero-day candidates.
Return JSON with this shape only:
{
  \"summary\": \"short analyst summary\",
  \"findings\": [
    {
      \"severity\": \"critical|high|medium|low\",
      \"title\": \"short finding title\",
      \"function\": \"function or region name\",
      \"category\": \"bug class\",
      \"description\": \"why the bug may be real and reachable\",
      \"evidence\": [\"bullet-sized evidence string\"],
      \"review_queries\": [\"up to three grep patterns to verify or refute this\"],
      \"confidence\": 0.0
    }
  ]
}
Prefer concrete, attacker-reachable issues over style or theoretical concerns.
If nothing convincing is present, return an empty findings list."""

REVIEW_PROMPT = """You are a skeptical vulnerability reviewer.
Decide whether the candidate is still interesting after local code-search evidence.
Respond with JSON only:
{
  \"verdict\": \"VALID|INVALID|UNCERTAIN\",
  \"reasoning\": \"concise explanation\",
  \"next_check\": \"optional follow-up check\"
}
A VALID result means the finding still looks worth manual review.
INVALID means the code or evidence materially refutes it.
UNCERTAIN means the path is incomplete or cross-file evidence is insufficient."""

_HTTP_LOCK = threading.Lock()
_HTTP_OPENER: urllib.request.OpenerDirector | None = None


@dataclass
class FileJob:
    path: Path
    display_name: str
    chars: int
    lines: int


@dataclass
class ScanResult:
    file: str
    status: str
    context: str
    summary: str
    findings: list[dict[str, Any]]
    error: str | None = None


def load_external_context(external_context_file: Path | None) -> str:
    if external_context_file is None:
        return ""
    return external_context_file.read_text(encoding="utf-8", errors="replace").strip()


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


def load_api_keys(root: Path) -> dict[str, str]:
    keys = dict(read_dotenv(root / ".env"))
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY"):
        value = os.environ.get(name)
        if value:
            keys[name] = value
    return keys


def get_http_opener() -> urllib.request.OpenerDirector:
    global _HTTP_OPENER
    if _HTTP_OPENER is None:
        with _HTTP_LOCK:
            if _HTTP_OPENER is None:
                _HTTP_OPENER = urllib.request.build_opener(
                    urllib.request.HTTPHandler(),
                    urllib.request.HTTPSHandler(),
                )
    return _HTTP_OPENER


def resolve_backend(model: str, keys: dict[str, str]) -> tuple[str, str, dict[str, str]]:
    if "/" in model:
        api_key = keys.get("OPENROUTER_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        headers = {
            "HTTP-Referer": "https://github.com/",
            "X-Title": "zero-day-hunter",
        }
        return OPENROUTER_API_URL, api_key, headers

    api_key = keys.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OPENAI_API_URL, api_key, {}


def call_llm(model: str, messages: list[dict[str, str]], keys: dict[str, str], *, json_mode: bool = False) -> tuple[str, dict[str, Any]]:
    api_url, api_key, extra_headers = resolve_backend(model, keys)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        **extra_headers,
    }
    payload: dict[str, Any] = {"model": model, "messages": messages}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(api_url, data=data, headers=headers, method="POST")
    opener = get_http_opener()

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with opener.open(request, timeout=120) as response:
                raw = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw)
            content = parsed["choices"][0]["message"].get("content") or ""
            usage = parsed.get("usage", {})
            return content, usage
        except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(1 + attempt)

    raise RuntimeError(f"LLM request failed: {last_error}")


def extract_json(text: str) -> Any:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for opening, closing in (("{", "}"), ("[", "]")):
        start = text.find(opening)
        if start == -1:
            continue
        depth = 0
        for index in range(start, len(text)):
            char = text[index]
            if char == opening:
                depth += 1
            elif char == closing:
                depth -= 1
                if depth == 0:
                    snippet = text[start:index + 1]
                    try:
                        return json.loads(snippet)
                    except json.JSONDecodeError:
                        break
    return None


def discover_files(target: Path, max_chars: int) -> tuple[list[FileJob], list[str]]:
    candidates = [target] if target.is_file() else sorted(path for path in target.rglob("*") if path.is_file())
    jobs: list[FileJob] = []
    skipped: list[str] = []

    for path in candidates:
        if path.suffix.lower() not in DEFAULT_EXTENSIONS:
            skipped.append(f"{path}: wrong extension")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            skipped.append(f"{path}: unreadable or binary")
            continue
        if len(text) > max_chars:
            skipped.append(f"{path}: too large ({len(text):,} chars)")
            continue
        jobs.append(
            FileJob(
                path=path,
                display_name=str(path.relative_to(target if target.is_dir() else target.parent)),
                chars=len(text),
                lines=text.count("\n") + 1,
            )
        )
    return jobs, skipped


def run_source_grep(repo_root: Path, query: str, limit: int = 20) -> str:
    script_path = SCRIPT_DIR / "source_grep.py"
    if not query.strip():
        return ""
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path), str(repo_root), query, "--limit", str(limit)],
            capture_output=True,
            text=True,
            timeout=30,
            errors="replace",
        )
        return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def normalize_findings(payload: Any) -> tuple[str, list[dict[str, Any]]]:
    if isinstance(payload, dict):
        summary = str(payload.get("summary", "")).strip()
        findings = payload.get("findings", [])
    elif isinstance(payload, list):
        summary = ""
        findings = payload
    else:
        return "", []

    normalized: list[dict[str, Any]] = []
    if not isinstance(findings, list):
        return summary, []

    for item in findings:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity", "medium")).lower()
        if severity not in SEVERITY_ORDER:
            severity = "medium"
        normalized.append(
            {
                "severity": severity,
                "title": str(item.get("title", "Untitled finding")).strip(),
                "function": str(item.get("function", "unknown")).strip(),
                "category": str(item.get("category", "unspecified")).strip(),
                "description": str(item.get("description", "")).strip(),
                "evidence": [str(v).strip() for v in item.get("evidence", []) if str(v).strip()],
                "review_queries": [str(v).strip() for v in item.get("review_queries", []) if str(v).strip()][:3],
                "confidence": float(item.get("confidence", 0.0) or 0.0),
            }
        )

    normalized.sort(key=lambda row: SEVERITY_ORDER.index(row["severity"]))
    return summary, normalized


def review_finding(model: str, keys: dict[str, str], finding: dict[str, Any], file_code: str, repo_root: Path | None, external_context: str = "") -> dict[str, Any] | None:
    queries = finding.get("review_queries", [])
    grep_sections: list[str] = []
    if repo_root:
        for query in queries:
            output = run_source_grep(repo_root, query)
            if output:
                grep_sections.append(f"Query: {query}\n{output}")

    evidence_text = "\n\n".join(grep_sections) if grep_sections else "No local grep evidence collected."
    messages = [
        {"role": "system", "content": REVIEW_PROMPT},
        {
            "role": "user",
            "content": (
                f"Finding candidate:\n{json.dumps(finding, indent=2)}\n\n"
                f"External context:\n{external_context[:3000] if external_context else 'None provided'}\n\n"
                f"Code:\n```\n{file_code[:12000]}\n```\n\n"
                f"Local search evidence:\n{evidence_text}"
            ),
        },
    ]
    response, _ = call_llm(model, messages, keys, json_mode=True)
    parsed = extract_json(response)
    if not isinstance(parsed, dict):
        return None
    verdict = str(parsed.get("verdict", "UNCERTAIN")).upper()
    if verdict not in {"VALID", "INVALID", "UNCERTAIN"}:
        verdict = "UNCERTAIN"
    return {
        "verdict": verdict,
        "reasoning": str(parsed.get("reasoning", "")).strip(),
        "next_check": str(parsed.get("next_check", "")).strip(),
        "grep_evidence": grep_sections,
    }


def analyze_file(job: FileJob, target_root: Path, repo_root: Path | None, model: str, keys: dict[str, str], review: bool, external_context: str = "") -> ScanResult:
    try:
        code = job.path.read_text(encoding="utf-8")
        context_messages = [
            {"role": "system", "content": CONTEXT_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Repository root: {repo_root if repo_root else 'not provided'}\n"
                    f"External project context:\n{external_context[:4000] if external_context else 'None provided'}\n\n"
                    f"File: {job.display_name}\n\n```\n{code[:20000]}\n```"
                ),
            },
        ]
        context_text, _ = call_llm(model, context_messages, keys)

        finding_messages = [
            {"role": "system", "content": FINDINGS_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Repository root: {repo_root if repo_root else 'not provided'}\n"
                    f"External project context:\n{external_context[:4000] if external_context else 'None provided'}\n\n"
                    f"File: {job.display_name}\n\n"
                    f"Security context:\n{context_text}\n\n"
                    f"Code:\n```\n{code[:20000]}\n```"
                ),
            },
        ]
        findings_text, _ = call_llm(model, finding_messages, keys, json_mode=True)
        parsed = extract_json(findings_text)
        summary, findings = normalize_findings(parsed)

        if review:
            for finding in findings:
                review_result = review_finding(model, keys, finding, code, repo_root, external_context)
                if review_result:
                    finding["review"] = review_result

        return ScanResult(
            file=job.display_name,
            status="ok",
            context=context_text.strip(),
            summary=summary,
            findings=findings,
        )
    except Exception as exc:
        return ScanResult(
            file=job.display_name,
            status="error",
            context="",
            summary="",
            findings=[],
            error=str(exc),
        )


def write_result(out_dir: Path, result: ScanResult) -> None:
    stem = result.file.replace("/", "_").replace("\\", "_")
    context_path = out_dir / f"{stem}.context.md"
    json_path = out_dir / f"{stem}.json"
    markdown_path = out_dir / f"{stem}.md"

    context_path.write_text(f"# Context for {result.file}\n\n{result.context}\n", encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "file": result.file,
                "status": result.status,
                "summary": result.summary,
                "findings": result.findings,
                "error": result.error,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = [f"# Scan for {result.file}", ""]
    if result.status != "ok":
        lines.extend([f"- Status: error", f"- Error: {result.error or 'unknown'}"])
    else:
        if result.summary:
            lines.extend(["## Summary", "", result.summary, ""])
        if not result.findings:
            lines.extend(["## Findings", "", "No convincing candidates found.", ""])
        for index, finding in enumerate(result.findings, start=1):
            lines.extend([
                f"## Finding {index}: {finding['title']}",
                "",
                f"- Severity: {finding['severity']}",
                f"- Function: {finding['function']}",
                f"- Category: {finding['category']}",
                f"- Confidence: {finding['confidence']}",
                "",
                finding["description"],
                "",
            ])
            if finding.get("evidence"):
                lines.append("### Evidence")
                lines.append("")
                for item in finding["evidence"]:
                    lines.append(f"- {item}")
                lines.append("")
            if finding.get("review"):
                review = finding["review"]
                lines.extend([
                    "### Skeptical review",
                    "",
                    f"- Verdict: {review.get('verdict', 'UNCERTAIN')}",
                    f"- Reasoning: {review.get('reasoning', '')}",
                ])
                next_check = review.get("next_check")
                if next_check:
                    lines.append(f"- Next check: {next_check}")
                if review.get("grep_evidence"):
                    lines.extend(["", "### Local search evidence", ""])
                    for section in review["grep_evidence"]:
                        lines.extend(["```text", section, "```", ""])
    markdown_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_summary(out_dir: Path, target: Path, results: list[ScanResult], skipped: list[str], model: str) -> None:
    summary_rows: list[dict[str, Any]] = []
    for result in results:
        counts = {level: 0 for level in SEVERITY_ORDER}
        valid_reviews = 0
        for finding in result.findings:
            counts[finding["severity"]] += 1
            if finding.get("review", {}).get("verdict") == "VALID":
                valid_reviews += 1
        summary_rows.append(
            {
                "file": result.file,
                "status": result.status,
                "findings": counts,
                "valid_reviews": valid_reviews,
                "error": result.error,
            }
        )

    payload = {
        "target": str(target),
        "model": model,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "files_scanned": len(results),
        "files_skipped": len(skipped),
        "results": summary_rows,
        "skipped": skipped,
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Zero Day Hunter Summary",
        "",
        f"- Target: `{target}`",
        f"- Model: {model}",
        f"- Files scanned: {len(results)}",
        f"- Files skipped: {len(skipped)}",
        "",
        "| File | Status | Critical | High | Medium | Low | Valid reviews |",
        "|------|--------|----------|------|--------|-----|---------------|",
    ]
    for row in summary_rows:
        counts = row["findings"]
        lines.append(
            f"| {row['file']} | {row['status']} | {counts['critical']} | {counts['high']} | {counts['medium']} | {counts['low']} | {row['valid_reviews']} |"
        )
    if skipped:
        lines.extend(["", "## Skipped", ""])
        for item in skipped[:100]:
            lines.append(f"- {item}")
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Hunt for likely zero-day candidates in a file or repository.")
    parser.add_argument("target", help="File or directory to scan")
    parser.add_argument("--repo-root", default=None, help="Repository root for grep-backed review")
    parser.add_argument("--output-dir", default=None, help="Directory for Markdown and JSON results")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--parallel", type=int, default=DEFAULT_PARALLEL, help=f"Concurrent file scans (default: {DEFAULT_PARALLEL})")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS, help=f"Skip files larger than this many characters (default: {DEFAULT_MAX_CHARS})")
    parser.add_argument("--external-context-file", default=None, help="Markdown or JSON file containing external project context, for example from build_external_context.py")
    parser.add_argument("--no-review", action="store_true", help="Skip skeptical review pass")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if not target.exists():
        print(f"Failure: target not found: {target}", file=sys.stderr)
        return 1

    repo_root = Path(args.repo_root).resolve() if args.repo_root else (target if target.is_dir() else target.parent)
    workspace_root = repo_root if repo_root.exists() else target.parent
    external_context_file = Path(args.external_context_file).resolve() if args.external_context_file else None
    if external_context_file and not external_context_file.exists():
        print(f"Failure: external context file not found: {external_context_file}", file=sys.stderr)
        return 1
    keys = load_api_keys(workspace_root)
    if "/" in args.model and not keys.get("OPENROUTER_API_KEY"):
        print("Failure: OPENROUTER_API_KEY is required for provider/model names.", file=sys.stderr)
        return 1
    if "/" not in args.model and not keys.get("OPENAI_API_KEY"):
        print("Failure: OPENAI_API_KEY is required for OpenAI model names.", file=sys.stderr)
        return 1

    jobs, skipped = discover_files(target, args.max_chars)
    if not jobs:
        print("Failure: no scannable files found.", file=sys.stderr)
        return 1

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_dir = Path(args.output_dir).resolve() if args.output_dir else (workspace_root / "zero-day-results" / timestamp)
    out_dir.mkdir(parents=True, exist_ok=True)
    external_context = load_external_context(external_context_file)
    if external_context:
        (out_dir / "_external_context.md").write_text(external_context + "\n", encoding="utf-8")

    print(f"Scanning {len(jobs)} file(s) with model {args.model}...")
    results: list[ScanResult] = []
    with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as executor:
        futures = {
            executor.submit(analyze_file, job, target, repo_root, args.model, keys, not args.no_review, external_context): job
            for job in jobs
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            write_result(out_dir, result)
            marker = "OK" if result.status == "ok" else "ERROR"
            print(f"[{marker}] {result.file} ({len(result.findings)} finding(s))")

    results.sort(key=lambda item: item.file)
    write_summary(out_dir, target, results, skipped, args.model)
    print(f"Results written to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
