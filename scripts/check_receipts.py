#!/usr/bin/env python3
"""Require every 案号 and 《法》第X条 in report.md to appear in search-log.md."""
from __future__ import annotations

import re
import sys
from pathlib import Path

CASE_RE = re.compile(r"[（(]\d{4}[）)][^号\n]{0,40}号")
LAW_RE = re.compile(r"《[^》\n]{1,80}》第[零〇一二三四五六七八九十百千0-9]+条")


def extract(text: str) -> tuple[list[str], list[str]]:
    cases = []
    seen_c = set()
    for m in CASE_RE.finditer(text):
        s = m.group(0)
        if s not in seen_c:
            seen_c.add(s)
            cases.append(s)
    laws = []
    seen_l = set()
    for m in LAW_RE.finditer(text):
        s = m.group(0)
        if s not in seen_l:
            seen_l.add(s)
            laws.append(s)
    return cases, laws


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_receipts.py <matter_dir>", file=sys.stderr)
        return 1
    matter = Path(argv[1])
    report = matter / "report.md"
    log = matter / "search-log.md"
    if not report.is_file():
        print(f"missing {report}", file=sys.stderr)
        return 1
    if not log.is_file():
        print(f"missing {log}", file=sys.stderr)
        return 1
    report_text = report.read_text(encoding="utf-8")
    log_text = log.read_text(encoding="utf-8")
    cases, laws = extract(report_text)
    missing = []
    for item in cases + laws:
        if item not in log_text:
            missing.append(item)
    if missing:
        print("citations without search-log receipt:", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print(f"ok: {len(cases)} 案号, {len(laws)} 法条, all in search-log")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
