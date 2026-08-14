#!/usr/bin/env python3
"""mcp.json must have exactly the 4 core servers and no real tokens."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED = {
    "pkulaw-law-search",
    "pkulaw-case-semantic-search",
    "pkulaw-law-item-keyword",
    "pkulaw-citation-validator",
}

TOKENISH = re.compile(
    r"(?:ghp_[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]{10,})"
)
LONG_BEARER = re.compile(
    r"Bearer\s+(?!YOUR_ACCESS_TOKEN\b)(?!\$\{env:PKULAW_ACCESS_TOKEN\})[A-Za-z0-9._\-]{20,}"
)
OK_AUTH = ("YOUR_ACCESS_TOKEN", "${env:PKULAW_ACCESS_TOKEN}")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> int:
    path = repo_root() / ".cursor" / "mcp.json"
    if not path.is_file():
        print(f"missing {path}", file=sys.stderr)
        return 1
    raw = path.read_text(encoding="utf-8")
    if TOKENISH.search(raw) or LONG_BEARER.search(raw):
        print("mcp.json looks like it contains a real token", file=sys.stderr)
        return 1
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"invalid json: {e}", file=sys.stderr)
        return 1
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        print("mcpServers missing", file=sys.stderr)
        return 1
    keys = set(servers)
    if keys != REQUIRED:
        print(f"expected exactly {sorted(REQUIRED)}, got {sorted(keys)}", file=sys.stderr)
        return 1
    for name, cfg in servers.items():
        headers = (cfg or {}).get("headers") or {}
        auth = headers.get("Authorization", "")
        if not any(ok in str(auth) for ok in OK_AUTH):
            print(
                f"{name}: Authorization must contain YOUR_ACCESS_TOKEN or "
                "${env:PKULAW_ACCESS_TOKEN}",
                file=sys.stderr,
            )
            return 1
    print("ok: 4 core MCP servers, token via env/placeholder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
