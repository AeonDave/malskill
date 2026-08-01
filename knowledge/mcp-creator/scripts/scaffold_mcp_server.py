#!/usr/bin/env python3
"""Scaffold a dependency-free stateless MCP 2026-07-28 server skeleton.

Generates a transport-agnostic core (server/discover, tools/list, tools/call,
MRTR input_required with signed requestState), stdio and Streamable HTTP
transports, domain adapters, and a real-transport smoke test.
"""
import argparse
import os
import sys

CORE = r"""
# Transport-agnostic MCP 2026-07-28 core.
# Stateless dispatcher, tool registry, and MRTR helpers. No third-party deps.
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Callable, Dict, List, Optional

PROTOCOL_VERSION = "2026-07-28"
SUPPORTED_VERSIONS = [PROTOCOL_VERSION]
SERVER_INFO = {"name": "__SERVER_NAME__", "version": "0.1.0"}

# JSON-RPC and MCP protocol error codes.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
HEADER_MISMATCH = -32020
UNSUPPORTED_PROTOCOL_VERSION = -32022

# Signing key for MRTR requestState. Set MCP_STATE_KEY so state survives restarts
# and is shared across horizontally scaled instances.
_STATE_KEY = os.environ.get("MCP_STATE_KEY", "").encode() or secrets.token_bytes(32)


class ProtocolError(Exception):
    def __init__(self, code: int, message: str, data: Optional[dict] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class CallContext:
    def __init__(self, params: dict):
        self.arguments = params.get("arguments") or {}
        self.input_responses = params.get("inputResponses")
        self.request_state = params.get("requestState")


class Tool:
    def __init__(self, name, description, input_schema, handler,
                 output_schema=None, annotations=None):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.annotations = annotations or {}
        self.handler = handler

    def describe(self) -> dict:
        entry = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }
        if self.output_schema is not None:
            entry["outputSchema"] = self.output_schema
        if self.annotations:
            entry["annotations"] = self.annotations
        return entry


REGISTRY: Dict[str, Tool] = {}


def register(tool: Tool) -> None:
    REGISTRY[tool.name] = tool


def complete(content_text=None, structured=None, is_error=False) -> dict:
    content: List[dict] = []
    if content_text is not None:
        content.append({"type": "text", "text": content_text})
    result = {"resultType": "complete", "content": content, "isError": is_error}
    if structured is not None:
        result["structuredContent"] = structured
    return result


def input_required(input_requests: dict, state_payload: dict) -> dict:
    return {
        "resultType": "input_required",
        "inputRequests": input_requests,
        "requestState": _sign_state(state_payload),
    }


def _sign_state(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    mac = hmac.new(_STATE_KEY, raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw).decode() + "." + base64.urlsafe_b64encode(mac).decode()


def verify_state(token: str) -> dict:
    # Treat requestState as attacker-controlled: verify signature, expiry, and
    # (in the caller) that it binds to the same principal and material arguments.
    try:
        raw_b64, mac_b64 = token.split(".", 1)
        raw = base64.urlsafe_b64decode(raw_b64)
        mac = base64.urlsafe_b64decode(mac_b64)
    except Exception:
        raise ProtocolError(INVALID_PARAMS, "malformed requestState")
    expected = hmac.new(_STATE_KEY, raw, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise ProtocolError(INVALID_PARAMS, "invalid requestState signature")
    payload = json.loads(raw)
    if float(payload.get("exp", 0)) < time.time():
        raise ProtocolError(INVALID_PARAMS, "expired requestState")
    return payload


def handle_discover(params: dict) -> dict:
    return {
        "resultType": "complete",
        "supportedVersions": SUPPORTED_VERSIONS,
        "capabilities": {"tools": {}},
        "instructions": "Stateless MCP 2026-07-28 server. Call tools/list, then tools/call.",
        "ttlMs": 60000,
        "cacheScope": "public",
        "_meta": {"io.modelcontextprotocol/serverInfo": SERVER_INFO},
    }


def handle_tools_list(params: dict) -> dict:
    tools = [REGISTRY[name].describe() for name in sorted(REGISTRY)]
    return {
        "resultType": "complete",
        "tools": tools,
        "ttlMs": 60000,
        "cacheScope": "public",
        "_meta": {"io.modelcontextprotocol/serverInfo": SERVER_INFO},
    }


def handle_tools_call(params: dict) -> dict:
    name = params.get("name")
    tool = REGISTRY.get(name)
    if tool is None:
        raise ProtocolError(INVALID_PARAMS, "unknown tool: " + str(name))
    return tool.handler(CallContext(params))


METHODS: Dict[str, Callable[[dict], dict]] = {
    "server/discover": handle_discover,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
}


def _error(msg_id, code, message, data=None) -> dict:
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": msg_id, "error": err}


def dispatch(message: dict) -> Optional[dict]:
    # Stateless: every request is self-contained. Returns a JSON-RPC response,
    # or None for a notification (no id).
    if message.get("jsonrpc") != "2.0":
        return _error(message.get("id"), INVALID_REQUEST, "jsonrpc must be '2.0'")
    msg_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}
    meta = params.get("_meta") or {}
    version = meta.get("io.modelcontextprotocol/protocolVersion")
    if version is not None and version not in SUPPORTED_VERSIONS:
        return _error(msg_id, UNSUPPORTED_PROTOCOL_VERSION,
                      "unsupported protocol version: " + str(version),
                      {"supportedVersions": SUPPORTED_VERSIONS})
    handler = METHODS.get(method)
    if handler is None:
        if msg_id is None:
            return None
        return _error(msg_id, METHOD_NOT_FOUND, "method not found: " + str(method))
    if msg_id is None:
        try:
            handler(params)
        except Exception:
            pass
        return None
    try:
        result = handler(params)
    except ProtocolError as exc:
        return _error(msg_id, exc.code, exc.message, exc.data)
    except Exception:
        return _error(msg_id, INTERNAL_ERROR, "internal error")
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}
"""

ADAPTERS = r"""
# Domain adapters: business logic separated from the MCP protocol layer.
# Importing this module registers the example tools.
import time

from mcp_core import (
    INVALID_PARAMS,
    ProtocolError,
    Tool,
    complete,
    input_required,
    register,
    verify_state,
)


def _echo(ctx):
    text = ctx.arguments.get("text", "")
    return complete(content_text=text, structured={"ok": True, "result": {"text": text}})


def _delete_item(ctx):
    # Destructive operation guarded by an MRTR confirmation round-trip.
    item = ctx.arguments.get("item_id")
    if not item:
        return complete(
            content_text="item_id is required",
            structured={"ok": False, "error_type": "missing_required_input",
                        "error": "item_id is required"},
            is_error=True,
        )
    if not ctx.input_responses:
        state = {"op": "delete_item", "item_id": item, "exp": time.time() + 300}
        requests = {
            "confirm_delete": {
                "method": "elicitation/create",
                "params": {
                    "mode": "confirm",
                    "message": "Delete " + item + "?",
                    "requestedSchema": {
                        "type": "object",
                        "properties": {"confirm": {"type": "boolean"}},
                        "required": ["confirm"],
                    },
                },
            }
        }
        return input_required(requests, state)
    payload = verify_state(ctx.request_state or "")
    if payload.get("item_id") != item:
        raise ProtocolError(INVALID_PARAMS, "requestState does not match arguments")
    answer = ctx.input_responses.get("confirm_delete") or {}
    if not answer.get("confirm"):
        return complete(content_text="deletion declined",
                        structured={"ok": True, "result": {"deleted": False}})
    # Perform the real domain side effect here.
    return complete(content_text="deleted " + item,
                    structured={"ok": True, "result": {"deleted": True, "item_id": item}})


register(Tool(
    name="echo",
    description="Echo text back.",
    input_schema={"type": "object", "properties": {"text": {"type": "string"}},
                  "required": ["text"], "additionalProperties": False},
    output_schema={"type": "object", "properties": {"ok": {"type": "boolean"},
                   "result": {"type": "object"}}},
    handler=_echo,
    annotations={"readOnlyHint": True},
))

register(Tool(
    name="delete_item",
    description="Delete an item; requires confirmation via MRTR.",
    input_schema={"type": "object", "properties": {"item_id": {"type": "string"}},
                  "required": ["item_id"], "additionalProperties": False},
    handler=_delete_item,
    annotations={"destructiveHint": True},
))
"""

STDIO = r"""
# Stdio transport for the stateless MCP core. One JSON-RPC message per line.
# Never write logs to stdout on stdio; use stderr.
import json
import sys

import adapters  # noqa: F401  Registers tools on import.
from mcp_core import PARSE_ERROR, dispatch


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            err = {"jsonrpc": "2.0", "id": None,
                   "error": {"code": PARSE_ERROR, "message": "parse error"}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()
            continue
        response = dispatch(message)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
"""

HTTP = r"""
# Streamable HTTP transport (stdlib only) for the stateless MCP core.
# Single POST endpoint /mcp. Validates routing headers and Origin; binds to 127.0.0.1.
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import adapters  # noqa: F401  Registers tools on import.
from mcp_core import HEADER_MISMATCH, METHOD_NOT_FOUND, PARSE_ERROR, dispatch

# Extend with the exact browser origins you trust. None = no Origin header (non-browser client).
ALLOWED_ORIGINS = {None}


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status, obj):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.rstrip("/") not in ("/mcp", ""):
            self._send_json(404, {"jsonrpc": "2.0", "id": None,
                            "error": {"code": METHOD_NOT_FOUND, "message": "not found"}})
            return
        # Reject cross-origin browser requests to prevent DNS rebinding.
        origin = self.headers.get("Origin")
        if origin is not None and origin not in ALLOWED_ORIGINS:
            self.send_response(403)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            message = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, ValueError):
            self._send_json(400, {"jsonrpc": "2.0", "id": None,
                            "error": {"code": PARSE_ERROR, "message": "parse error"}})
            return
        params = message.get("params") or {}
        # Header-body consistency: Mcp-Method and Mcp-Name must match the body.
        hdr_method = self.headers.get("Mcp-Method")
        if hdr_method is not None and hdr_method != message.get("method"):
            self._send_json(400, {"jsonrpc": "2.0", "id": message.get("id"),
                            "error": {"code": HEADER_MISMATCH,
                                      "message": "Mcp-Method header does not match body"}})
            return
        hdr_name = self.headers.get("Mcp-Name")
        body_name = params.get("name") or params.get("uri")
        if hdr_name is not None and body_name is not None and hdr_name != body_name:
            self._send_json(400, {"jsonrpc": "2.0", "id": message.get("id"),
                            "error": {"code": HEADER_MISMATCH,
                                      "message": "Mcp-Name header does not match body"}})
            return
        response = dispatch(message)
        if response is None:
            self.send_response(202)
            self.end_headers()
            return
        self._send_json(200, response)

    def log_message(self, *args):
        pass


def main(host="127.0.0.1", port=8000):
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    main(port=port)
"""

SMOKE = r"""
# Drives the stdio server through a real subprocess and asserts core contracts.
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
META = {"_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                  "io.modelcontextprotocol/clientCapabilities": {}}}


def _rpc(proc, message):
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


def main():
    proc = subprocess.Popen(
        [sys.executable, os.path.join(HERE, "stdio_server.py")],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )
    try:
        disc = _rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": META})
        assert disc["result"]["resultType"] == "complete", disc
        assert "2026-07-28" in disc["result"]["supportedVersions"], disc

        lst = _rpc(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": META})
        names = {t["name"] for t in lst["result"]["tools"]}
        assert {"echo", "delete_item"} <= names, lst
        assert "ttlMs" in lst["result"] and "cacheScope" in lst["result"], lst

        echo_params = {"name": "echo", "arguments": {"text": "hi"}}
        echo_params.update(META)
        echo = _rpc(proc, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": echo_params})
        assert echo["result"]["structuredContent"]["result"]["text"] == "hi", echo

        p1 = {"name": "delete_item", "arguments": {"item_id": "x1"}}
        p1.update(META)
        r1 = _rpc(proc, {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": p1})
        assert r1["result"]["resultType"] == "input_required", r1
        state = r1["result"]["requestState"]

        p2 = {"name": "delete_item", "arguments": {"item_id": "x1"},
              "inputResponses": {"confirm_delete": {"confirm": True}}, "requestState": state}
        p2.update(META)
        r2 = _rpc(proc, {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": p2})
        assert r2["result"]["structuredContent"]["result"]["deleted"] is True, r2

        print("smoke: OK")
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        proc.terminate()


if __name__ == "__main__":
    main()
"""

FILES_COMMON = {
    "mcp_core.py": CORE,
    "adapters.py": ADAPTERS,
    "stdio_server.py": STDIO,
    "smoke_test.py": SMOKE,
}
FILES_HTTP = {"http_server.py": HTTP}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Scaffold a stateless MCP 2026-07-28 server skeleton.")
    ap.add_argument("target", help="Directory to create the server in.")
    ap.add_argument("--name", default="example-mcp-server",
                    help="Server name reported in serverInfo.")
    ap.add_argument("--transport", choices=["stdio", "http", "both"], default="both",
                    help="Emit the HTTP transport in addition to stdio (default both).")
    ap.add_argument("--force", action="store_true",
                    help="Write into a non-empty directory.")
    args = ap.parse_args(argv)

    target = os.path.abspath(args.target)
    if os.path.isdir(target) and os.listdir(target) and not args.force:
        print("error: target exists and is not empty; use --force", file=sys.stderr)
        return 2
    os.makedirs(target, exist_ok=True)

    files = dict(FILES_COMMON)
    if args.transport in ("http", "both"):
        files.update(FILES_HTTP)

    for rel, content in files.items():
        if rel == "mcp_core.py":
            content = content.replace("__SERVER_NAME__", args.name)
        with open(os.path.join(target, rel), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content.lstrip("\n"))

    print("Scaffolded stateless MCP 2026-07-28 server in " + target)
    print("Files: " + ", ".join(sorted(files)))
    print("Run stdio:  python " + os.path.join(target, "stdio_server.py"))
    if args.transport in ("http", "both"):
        print("Run HTTP:   python " + os.path.join(target, "http_server.py") + " 8000")
    print("Smoke test: python " + os.path.join(target, "smoke_test.py"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
