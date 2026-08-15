from __future__ import annotations

import json
import re
from typing import Any

from ..config import Settings
from ..llm import LlmClient
from ..matter_store import Matter
from ..mcp_client import McpClient, McpError, discover_tool_name
from . import (
    append_receipt,
    extract_items_from_law_result,
    now_iso,
    summarize_for_log,
)
from .case_report import _ensure_draft_footer, _load_skill_snip

CASE_RE = re.compile(r"[（(]\d{4}[）)][^号\n]{0,40}号")
LAW_RE = re.compile(r"《[^》\n]{1,80}》第[零〇一二三四五六七八九十百千0-9]+条")
SOURCELESS_RE = re.compile(
    r"(根据相关法律规定|依照有关司法解释|按照现行法律规定|法律要求)"
)

SYSTEM_PROMPT = """你是律师工作流助手，只做「签发前引用核验」底稿，不是法律意见。

硬性纪律：
1. 签发三态必须置顶三选一：可以签发 / 修正后可签发 / 不得签发。
2. 输出是底稿；不替代律师核验。文末标明底稿声明。
3. 废止 ≠ 自动错误；须先看法律事实时间锚定。
4. 必须抽出「根据相关法律规定」等无源命题。
5. 九维：存在性、版本与时效、条号、条文内容、整条引用、命题对应、可引性、上位法、格式。
6. 核验结论只能依据用户提供的「本次 MCP 核验结果」；MCP 不通或未检到的标 ⬜/不得签发相关项，禁止凭记忆补核。
7. 同时产出两份 Markdown：audit.md 正文，以及 signoff.md（含签发三态勾选、核验人可留空待填、核验时间可写本次时间或留空）。
8. 回复格式严格为：
===AUDIT===
（audit.md 全文）
===SIGNOFF===
（signoff.md 全文）
"""


async def run_citation_audit(
    *,
    settings: Settings,
    matter: Matter,
    mcp: McpClient,
    llm: LlmClient,
) -> dict[str, Any]:
    mcp.require_token()
    llm.require_key()

    report = matter.read("report.md")
    if not report.strip() or "（空）" in report[:80]:
        # template placeholder
        if len(report.strip()) < 80:
            raise McpError("report.md 几乎为空，请先出类案检索报告再核验。")

    brief = matter.read("brief.md")
    log = matter.read("search-log.md")
    skill_snip = _load_skill_snip(settings, "pkulaw-citation-audit")

    cases = _unique(CASE_RE.findall(report))
    laws = _unique(LAW_RE.findall(report))
    sourceless = _unique(SOURCELESS_RE.findall(report))

    bundle: dict[str, Any] = {
        "核验时间": now_iso(),
        "抽出案号": cases,
        "抽出法条": laws,
        "无源命题关键词命中": sourceless,
        "核验轮次": [],
        "既有search-log摘要": log[:4000],
    }

    # citation validator
    try:
        v = await _validate_citations(mcp, report=report, matter=matter)
        bundle["核验轮次"].append(v)
    except McpError as e:
        bundle["核验轮次"].append({"label": "citation-validator", "error": str(e)})

    # fatiao / law search for each law cite
    for law in laws[:12]:
        parsed = _parse_law_cite(law)
        if not parsed:
            continue
        title, num = parsed
        try:
            round_data = await _lookup_law(mcp, title=title, tiao_num=num, matter=matter)
            bundle["核验轮次"].append(round_data)
        except McpError as e:
            bundle["核验轮次"].append(
                {"label": f"法条核验 {law}", "error": str(e), "items": []}
            )

    # semantic law search on case foci leftover
    if laws:
        try:
            server = "pkulaw-law-search"
            tool = await discover_tool_name(
                mcp, server, ["search_article", "get_article"]
            )
            q = " ".join(laws[:5])
            data = await mcp.call_tool(server, tool, {"text": q})
            items = extract_items_from_law_result(data)
            for it in items:
                append_receipt(
                    matter,
                    tool=f"{server}/{tool}",
                    query=q[:200],
                    result_id=it["id"],
                    url=it["url"],
                )
            bundle["核验轮次"].append(
                {
                    "label": "法规语义复核",
                    "本次返回": len(items),
                    "items": items,
                }
            )
        except McpError as e:
            bundle["核验轮次"].append({"label": "法规语义复核", "error": str(e)})

    user_prompt = f"""请对下列类案报告做签发前引用核验。

## 文书类型与去向
所内/客户底稿

## 法律事实时间
见 brief；若不明，在 audit 中标 ⬜ 时间锚定不明。

## brief.md
{brief}

## report.md（待核）
{report}

## Skill 要点
{skill_snip}

## 本次 MCP 核验结果（唯一依据）
```json
{json.dumps(bundle, ensure_ascii=False, indent=2)[:100000]}
```

若 MCP 轮次大量 error，签发结论不得写成「可以签发」。
"""

    raw = await llm.complete(system=SYSTEM_PROMPT, user=user_prompt, max_tokens=8192)
    audit, signoff = _split_audit_signoff(raw)
    audit = _ensure_draft_footer(audit)
    matter.write("audit.md", audit + "\n")
    matter.write("signoff.md", signoff + "\n")
    return {
        "ok": True,
        "message": "已写入 audit.md 与 signoff.md，并追加 search-log 回执。请律师本人核验后再定签发。",
        "cases": len(cases),
        "laws": len(laws),
    }


async def _validate_citations(
    mcp: McpClient, *, report: str, matter: Matter
) -> dict[str, Any]:
    server = "pkulaw-citation-validator"
    tool = await discover_tool_name(
        mcp, server, ["adjust_provisions", "adjustProvisions", "validate"]
    )
    # try common argument shapes
    errors: list[str] = []
    data = None
    for args in (
        {"text": report[:12000]},
        {"content": report[:12000]},
        {"provisions": report[:12000]},
    ):
        try:
            data = await mcp.call_tool(server, tool, args)
            append_receipt(
                matter,
                tool=f"{server}/{tool}",
                query=summarize_for_log(args, 180),
                result_id="citation-validator-result",
                url="",
            )
            return {
                "label": "citation-validator",
                "tool": f"{server}/{tool}",
                "query": args,
                "result": summarize_for_log(data, 4000),
            }
        except McpError as e:
            errors.append(str(e))
    raise McpError("；".join(errors) or "citation-validator 调用失败")


async def _lookup_law(
    mcp: McpClient, *, title: str, tiao_num: str, matter: Matter
) -> dict[str, Any]:
    server = "pkulaw-law-item-keyword"
    tool = await discover_tool_name(
        mcp, server, ["get_law_item_content", "getLawItemContent"]
    )
    # tiao_num may be Chinese; try digit extract
    digit = _chinese_or_digit_to_num(tiao_num)
    args = {"title": title, "tiao_num": digit or tiao_num}
    data = await mcp.call_tool(server, tool, args)
    items = extract_items_from_law_result(data)
    if not items and data:
        items = [
            {
                "id": f"《{title}》第{tiao_num}条",
                "url": "",
                "title": f"《{title}》第{tiao_num}条",
                "raw": summarize_for_log(data, 1200),
            }
        ]
    for it in items:
        append_receipt(
            matter,
            tool=f"{server}/{tool}",
            query=summarize_for_log(args, 200),
            result_id=it["id"],
            url=it["url"],
        )
    return {
        "label": f"法条点查《{title}》第{tiao_num}条",
        "本次返回": len(items),
        "items": items,
        "raw_preview": summarize_for_log(data, 2000),
    }


def _parse_law_cite(cite: str) -> tuple[str, str] | None:
    m = re.match(r"《([^》]+)》第([零〇一二三四五六七八九十百千0-9]+)条", cite)
    if not m:
        return None
    return m.group(1), m.group(2)


def _chinese_or_digit_to_num(s: str) -> str:
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", s):
        return s
    mapping = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    if s == "十":
        return "10"
    if s.startswith("十"):
        rest = s[1:]
        return str(10 + (mapping.get(rest, 0) if rest else 0))
    if "十" in s:
        left, right = s.split("十", 1)
        return str(mapping.get(left, 0) * 10 + (mapping.get(right, 0) if right else 0))
    if s in mapping:
        return str(mapping[s])
    # 百
    return s


def _unique(items: list[str]) -> list[str]:
    out: list[str] = []
    seen = set()
    for i in items:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _split_audit_signoff(raw: str) -> tuple[str, str]:
    if "===AUDIT===" in raw and "===SIGNOFF===" in raw:
        a = raw.split("===AUDIT===", 1)[1]
        audit, signoff = a.split("===SIGNOFF===", 1)
        return audit.strip(), signoff.strip()
    # fallback: whole as audit, minimal signoff
    signoff = f"""# 签发

## 签发三态（三选一）

- [ ] 可以签发
- [x] 修正后可签发
- [ ] 不得签发
- [ ] 未核验

## 核验人

（空）

## 核验时间（ISO 8601）

{now_iso()}

## 导出勾选

- [ ] 已通过 `python3 scripts/check_receipts.py`（每条引用有回执）
- [ ] 已通过 `python3 scripts/check_signoff.py`（可以签发方可导出）
- [ ] 核验人与时间已填写

**可以签发必须有核验人 + ISO 时间。不得签发禁止导出。修正后可签发不可导出。**

> 模型未按分隔符返回，已降级写入；请律师重跑或手改。
"""
    return raw.strip(), signoff
