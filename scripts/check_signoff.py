#!/usr/bin/env python3
"""Parse signoff.md. 可以签发=0, 修正后可签发=2, else=1."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ISO_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}"
    r"(?:T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?"
)

EMPTY_VERIFIER = re.compile(
    r"^(?:（空）|\(空\)|空|待填|未填|n/?a|none|todo)?$",
    re.I,
)

STATES = ("修正后可签发", "可以签发", "不得签发", "未核验")


def checked_states(text: str) -> list[str]:
    found = []
    for m in re.finditer(r"- \[[xX]\]\s*(\S+)", text):
        label = m.group(1).strip()
        for s in STATES:
            if label.startswith(s) or s in label:
                if s not in found:
                    found.append(s)
    return found


def first_state(text: str) -> str | None:
    checked = checked_states(text)
    if checked:
        return checked[0]
    # heading / bold / 签发三态 line
    for pat in (
        r"签发三态[^\n]{0,20}[:：]\s*(修正后可签发|可以签发|不得签发|未核验)",
        r"\*\*(修正后可签发|可以签发|不得签发|未核验)\*\*",
        r"^#{1,3}\s*(修正后可签发|可以签发|不得签发|未核验)\s*$",
    ):
        m = re.search(pat, text, re.M)
        if m:
            return m.group(1)
    # first standalone occurrence, 修正后 before 可以
    for s in STATES:
        if s in text:
            return s
    return None


def verifier(text: str) -> str:
    m = re.search(r"核验人\s*[:：]\s*(\S+)", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"^#{1,3}\s*核验人\s*$", text, re.M)
    if m:
        after = text[m.end():]
        for line in after.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("- ["):
                if line.startswith("#"):
                    break
                continue
            return line
    return ""


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_signoff.py <matter_dir>", file=sys.stderr)
        return 1
    path = Path(argv[1]) / "signoff.md"
    if not path.is_file():
        print(f"missing {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8")
    state = first_state(text)
    if state is None:
        print("signoff state missing", file=sys.stderr)
        return 1
    if state == "修正后可签发":
        print("修正后可签发 (not exportable)")
        return 2
    if state in ("不得签发", "未核验"):
        print(state, file=sys.stderr)
        return 1
    if state == "可以签发":
        who = verifier(text)
        if not who or EMPTY_VERIFIER.match(who):
            print("可以签发 requires non-empty 核验人", file=sys.stderr)
            return 1
        if not ISO_RE.search(text):
            print("可以签发 requires ISO-like timestamp", file=sys.stderr)
            return 1
        print(f"可以签发 核验人={who}")
        return 0
    print(f"unrecognized state: {state}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
