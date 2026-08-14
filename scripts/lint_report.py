#!/usr/bin/env python3
"""Fail if report treats list-API Total as 类案 count."""
from __future__ import annotations

import re
import sys
from pathlib import Path

FOUND_RE = re.compile(r"共找到\s*\d+\s*条")
TOTAL_RE = re.compile(r"Total\s*[=:：]\s*(\d+)", re.I)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: lint_report.py <matter_dir>", file=sys.stderr)
        return 1
    matter = Path(argv[1])
    report_p = matter / "report.md"
    log_p = matter / "search-log.md"
    if not report_p.is_file():
        print(f"missing {report_p}", file=sys.stderr)
        return 1
    report = report_p.read_text(encoding="utf-8")
    failed = False
    if FOUND_RE.search(report):
        print("report.md matches 共找到 N 条", file=sys.stderr)
        failed = True
    if log_p.is_file():
        log = log_p.read_text(encoding="utf-8")
        totals = set(TOTAL_RE.findall(log))
        for n in totals:
            # same number used as 类案总数
            if re.search(rf"{n}\s*条\s*类案", report) or re.search(
                rf"类案[^\n]{{0,20}}{n}", report
            ):
                print(
                    f"search-log Total={n} reused in report as 类案总数",
                    file=sys.stderr,
                )
                failed = True
    if failed:
        return 1
    print("ok: no Total-as-count wording")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
