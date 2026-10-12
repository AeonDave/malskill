"""HTTP helpers shared by service clients."""
from __future__ import annotations

import os
import subprocess

PROXY_HELP = "proxy URL or 'direct'"


def resolve_proxy(proxy: str | None = None) -> str | None:
    value = (os.environ.get("GEO_PROXY", "") if proxy is None else proxy).strip()
    return None if value.lower() in ("", "direct") else value


def curl_args(proxy: str | None = None) -> list[str]:
    value = resolve_proxy(proxy)
    # Clear NO_PROXY for an explicit proxy; ignore ambient proxies for direct mode.
    return ["--proxy", value, "--noproxy", ""] if value else ["--noproxy", "*"]


def fetch_bytes(url: str, proxy: str | None = None, timeout: int = 20,
                headers: dict[str, str] | None = None) -> bytes:
    cmd = ["curl", "-q", "-fsSL", "--max-time", str(timeout), *curl_args(proxy)]
    for name, value in (headers or {}).items():
        cmd += ["-H", f"{name}: {value}"]
    result = subprocess.run(cmd + [url], capture_output=True, timeout=timeout + 5)
    if result.returncode:
        raise RuntimeError(f"Request failed (curl exit {result.returncode}); run doctor.py --network to check connectivity.")
    return result.stdout


def model_proxy_env(proxy: str | None = None) -> None:
    """Set the model downloader's process environment before importing its HTTP client."""
    value = resolve_proxy(proxy)
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
                "http_proxy", "https_proxy", "all_proxy", "no_proxy"):
        os.environ.pop(key, None)
    if value:
        os.environ.update(HTTP_PROXY=value, HTTPS_PROXY=value, ALL_PROXY=value)
    else:
        os.environ["NO_PROXY"] = "*"


_STATUS_MARK = b"\n__GEOINT_HTTP_STATUS__"


def request(url: str, proxy: str | None = None, timeout: int = 20, headers: dict[str, str] | None = None,
            head: bool = False, form: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
    """(final HTTP status, lower-case headers of a HEAD, body) without failing on HTTP errors; raises on transport errors."""
    cmd = ["curl", "-q", "-sS", "-L", "--max-time", str(timeout), *curl_args(proxy)]
    for name, value in (headers or {}).items():
        cmd += ["-H", f"{name}: {value}"]
    for name, value in (form or {}).items():
        cmd += ["--data-urlencode", f"{name}={value}"]
    if head:
        cmd.append("-I")
    cmd += ["-w", _STATUS_MARK.decode() + "%{http_code}", url]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout + 5)
    if result.returncode:
        raise RuntimeError(f"curl exit {result.returncode}: {result.stderr.decode('utf-8', 'replace').strip()[:200]}")
    body, _, code = result.stdout.rpartition(_STATUS_MARK)
    hdrs: dict[str, str] = {}
    if head:
        block = body.replace(b"\r\n", b"\n").strip().split(b"\n\n")[-1]   # last block after redirects
        for line in block.split(b"\n")[1:]:
            k, _, v = line.decode("latin-1").partition(":")
            hdrs[k.strip().lower()] = v.strip()
        body = b""
    return (int(code) if code.isdigit() else 0), hdrs, body
