from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from ..matter_store import Matter

RECEIPT_HEADER = (
    "| 时间 | 工具 | 查询式 | 返回id/案号或法条 | url | 回执ID |\n"
    "| --- | --- | --- | --- | --- | --- |"
)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_receipt(
    matter: Matter,
    *,
    tool: str,
    query: str,
    result_id: str,
    url: str,
    receipt_id: str | None = None,
) -> str:
    rid = receipt_id or f"R-{uuid.uuid4().hex[:10]}"
    text = matter.read("search-log.md")
    if RECEIPT_HEADER.splitlines()[0] not in text:
        text = "# 检索回执\n\n" + RECEIPT_HEADER + "\n"
    # 去掉末尾空行占位
    lines = text.rstrip().splitlines()
    row = (
        f"| {now_iso()} | {tool} | {_cell(query)} | {_cell(result_id)} | "
        f"{_cell(url)} | {rid} |"
    )
    lines.append(row)
    matter.write("search-log.md", "\n".join(lines) + "\n")
    return rid


def _cell(s: str) -> str:
    return (s or "").replace("|", "｜").replace("\n", " ").strip() or "—"


def summarize_for_log(payload: Any, limit: int = 400) -> str:
    try:
        s = json.dumps(payload, ensure_ascii=False)
    except TypeError:
        s = str(payload)
    return s[:limit]


def extract_items_from_case_result(data: Any) -> list[dict[str, str]]:
    """Normalize MCP case/law payloads into cite rows for logging."""
    items: list[dict[str, str]] = []
    rows = _as_list(data)
    for row in rows:
        if not isinstance(row, dict):
            continue
        case_no = str(
            row.get("CaseNumber")
            or row.get("case_number")
            or row.get("案号")
            or row.get("title")
            or row.get("Title")
            or row.get("gid")
            or row.get("id")
            or "—"
        )
        url = str(row.get("url") or row.get("Url") or row.get("URL") or "")
        url = _bare_url(url)
        items.append(
            {
                "id": case_no,
                "url": url,
                "title": str(row.get("Title") or row.get("title") or case_no),
                "raw": summarize_for_log(row, 1200),
            }
        )
    return items


def extract_items_from_law_result(data: Any) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    rows = _as_list(data)
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or row.get("Title") or row.get("law_title") or "—")
        number = str(
            row.get("number")
            or row.get("tiao_num")
            or row.get("article")
            or row.get("条号")
            or ""
        )
        label = f"《{title}》第{number}条" if number else title
        if number and not number.startswith("第"):
            # fatiao uses numeric tiao_num; keep readable
            label = f"《{_strip_book(title)}》第{number}条"
        url = _bare_url(str(row.get("url") or row.get("Url") or ""))
        items.append(
            {
                "id": label,
                "url": url,
                "title": label,
                "raw": summarize_for_log(row, 1200),
            }
        )
    return items


def _strip_book(title: str) -> str:
    t = title.strip()
    if t.startswith("《") and t.endswith("》"):
        return t[1:-1]
    return t


def _as_list(data: Any) -> list[Any]:
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("result"), list):
            return data["result"]
        if isinstance(data.get("Data"), list):
            return data["Data"]
        if isinstance(data.get("data"), list):
            return data["data"]
        # single article object
        if any(k in data for k in ("title", "Title", "content", "Content", "url", "Url")):
            return [data]
    return []


def _bare_url(url: str) -> str:
    m = re.search(r"\((https?://[^)\s]+)\)", url)
    if m:
        return m.group(1)
    return url.strip()


def brief_incomplete(brief: str) -> list[str]:
    missing = []
    for key in ("案由", "争议焦点", "关键事实", "初步定性"):
        if key not in brief:
            missing.append(key)
            continue
        # crude emptiness: section after heading until next ## has only placeholders
        m = re.search(rf"##\s*{key}\s*\n(.*?)(?=\n## |\Z)", brief, re.S)
        if not m:
            missing.append(key)
            continue
        body = m.group(1).strip()
        if not body or body in ("（填写）", "1.", "1.\n2.\n3."):
            missing.append(key)
            continue
        if re.fullmatch(r"[（(]?填写[）)]?|\s*", body):
            missing.append(key)
    return missing
