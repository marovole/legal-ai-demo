#!/usr/bin/env python3
"""Detect BAD audits that treat 合同法废止 as automatic 不得签发 without time-anchor.

Default: exit 1 if the audit is bad.
--expect-bad-audit: exit 0 if the audit IS bad (eval fixture).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ANCHOR_TERMS = ("时间锚定", "法律事实时间")
REPEAL_TERMS = ("废止", "失效")


def contract_law_windows(text: str) -> list[str]:
    windows = []
    for m in re.finditer(r"合同法", text):
        start = max(0, m.start() - 80)
        end = min(len(text), m.end() + 160)
        windows.append(text[start:end])
    return windows


def is_bad_audit(text: str) -> bool:
    windows = contract_law_windows(text)
    if not windows:
        return False
    saw_ban = False
    saw_repeal_reason = False
    saw_anchor = False
    for w in windows:
        if "不得签发" in w:
            saw_ban = True
        if any(t in w for t in REPEAL_TERMS):
            saw_repeal_reason = True
        if any(t in w for t in ANCHOR_TERMS):
            saw_anchor = True
    return saw_ban and saw_repeal_reason and not saw_anchor


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("matter_dir")
    p.add_argument(
        "--expect-bad-audit",
        action="store_true",
        help="exit 0 when the audit IS bad",
    )
    args = p.parse_args(argv[1:])
    path = Path(args.matter_dir) / "audit.md"
    if not path.is_file():
        print(f"missing {path}", file=sys.stderr)
        return 1 if args.expect_bad_audit else 0
    text = path.read_text(encoding="utf-8")
    bad = is_bad_audit(text)
    if args.expect_bad_audit:
        if bad:
            print("ok: detected bad audit (废止 without time-anchor)")
            return 0
        print("expected a bad 合同法/废止 audit, did not detect one", file=sys.stderr)
        return 1
    if bad:
        print(
            "bad audit: 《合同法》标不得签发, reason only 废止/失效, no 时间锚定/法律事实时间",
            file=sys.stderr,
        )
        return 1
    print("ok: no naive 废止-as-error audit")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
