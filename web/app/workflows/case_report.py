from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..config import Settings
from ..llm import LlmClient
from ..matter_store import Matter
from ..mcp_client import McpClient, McpError, discover_tool_name
from . import (
    append_receipt,
    brief_incomplete,
    extract_items_from_case_result,
    extract_items_from_law_result,
    now_iso,
    summarize_for_log,
)


SYSTEM_PROMPT = """你是律师工作流助手，只出具「类案检索报告」底稿，不是法律意见。

硬性纪律（违反任一条即失败）：
1. 输出是底稿；文末必须标明「本文件为底稿，不构成法律意见；对外发出前须律师本人核验」。
2. 只能使用用户消息里「本次 MCP 检索结果」中出现的案号、法规、裁判要点、链接；禁止编造案号或法条。
3. 检索平台必须写「北大法宝案例库」，不得写成裁判文书网。
4. 禁止把列表 Total 写成「共找到 N 条类案」；写「本次返回 N 条 / 实读 M 条」。
5. 个位数样本不得写「法院普遍认为」。
6. 必须保留「指导性案例」专节；若检索结果标明该轮 0 命中，也要写明已单独检索、0 命中。
7. 每条引用须能在 search-log 回执中对应（用户会另行落盘）；正文引用须附法宝链接（结果里有的才写）。
8. 默认受众：所内/客户底稿（不是呈法官归档件），不利类案也要放。
9. 结构覆盖法发〔2020〕24 号第八条：检索主体、时间、平台、方法、结果，类案裁判要点，待决案件争议焦点，是否参照/参考的分析说明。
10. 短、少套话，先结论。不要输出除报告正文以外的解释。
"""


async def run_case_research_report(
    *,
    settings: Settings,
    matter: Matter,
    mcp: McpClient,
    llm: LlmClient,
) -> dict[str, Any]:
    mcp.require_token()
    llm.require_key()

    brief = matter.read("brief.md")
    missing = brief_incomplete(brief)
    if missing:
        raise McpError(f"brief.md 缺项，请先填写：{'、'.join(missing)}")

    delta = matter.read("lawyer-delta.md")
    skill_snip = _load_skill_snip(settings, "pkulaw-case-research-report")

    # --- MCP retrieval (4 core services only) ---
    foci = _extract_foci(brief)
    query_text = "；".join(foci) if foci else brief[:500]
    search_bundle: dict[str, Any] = {
        "检索时间": now_iso(),
        "检索平台": "北大法宝案例库",
        "核心服务": [
            "pkulaw-law-search",
            "pkulaw-case-semantic-search",
            "pkulaw-law-item-keyword",
            "pkulaw-citation-validator",
        ],
        "轮次": [],
        "说明": (
            "本 Web 部署仅接通 mcp.json 中 4 个核心服务；"
            "无 case-keyword/caseGrade 筛选，指导性案例轮次以语义检索 +「指导性案例」约束近似实现，"
            "0 命中也保留专节。"
        ),
    }

    # 顺位1：指导性案例（必检）
    guiding = await _search_cases(
        mcp,
        text=f"指导性案例 {query_text}",
        label="顺位1-指导性案例（语义近似）",
        matter=matter,
    )
    search_bundle["轮次"].append(guiding)

    # 顺位2+：近三年语义类案
    general = await _search_cases(
        mcp,
        text=query_text,
        label="语义类案-近三年优先（文本约束）",
        matter=matter,
        extra_args={"decision_date_start": _years_ago_iso(3)},
    )
    search_bundle["轮次"].append(general)

    # 法规语义：围绕焦点
    laws = await _search_laws(mcp, text=query_text, matter=matter)
    search_bundle["轮次"].append(laws)

    # 常见劳动解除相关法条点查（有结果才记；失败不编造）
    for title, tiao in (
        ("中华人民共和国劳动合同法", "39"),
        ("中华人民共和国劳动合同法", "40"),
        ("中华人民共和国劳动合同法", "87"),
    ):
        try:
            fatiao = await _fatiao(mcp, title=title, tiao_num=tiao, matter=matter)
            search_bundle["轮次"].append(fatiao)
        except McpError as e:
            search_bundle["轮次"].append(
                {
                    "label": f"法条点查《{title}》第{tiao}条",
                    "error": str(e),
                    "本次返回": 0,
                    "items": [],
                }
            )

    user_prompt = f"""请根据下列材料出具《类案检索报告》Markdown 底稿。

## 受众
所内/客户底稿（默认）

## 案件 brief.md
{brief}

## 律师改稿口径 lawyer-delta.md
{delta or "（空）"}

## Skill 要点（须遵守）
{skill_snip}

## 本次 MCP 检索结果（唯一允许引用的来源）
```json
{json.dumps(search_bundle, ensure_ascii=False, indent=2)[:100000]}
```

写作要求：
- 若指导性案例轮次 items 为空，专节写明已单独检索、0 命中。
- 只引用 JSON 里出现的案号/法条/链接。
- 不要写「共找到 Total 条」。
"""

    report = await llm.complete(system=SYSTEM_PROMPT, user=user_prompt)
    report = _ensure_draft_footer(report)
    matter.write("report.md", report + "\n")
    return {
        "ok": True,
        "message": "已写入 report.md，并追加 search-log.md 回执。请律师审阅后做签发前核验。",
        "rounds": len(search_bundle["轮次"]),
    }


async def _search_cases(
    mcp: McpClient,
    *,
    text: str,
    label: str,
    matter: Matter,
    extra_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    server = "pkulaw-case-semantic-search"
    try:
        tool = await discover_tool_name(mcp, server, ["search_case", "searchCase"])
        args = {"text": text, **(extra_args or {})}
        # size 若被拒会在下方降级
        args.setdefault("size", 8)
        try:
            data = await mcp.call_tool(server, tool, args)
        except McpError:
            # schema drift：去掉筛选只留 text
            data = await mcp.call_tool(server, tool, {"text": text})
            args = {"text": text}
        items = extract_items_from_case_result(data)
        for it in items:
            append_receipt(
                matter,
                tool=f"{server}/{tool}",
                query=summarize_for_log(args, 200),
                result_id=it["id"],
                url=it["url"],
            )
        return {
            "label": label,
            "tool": f"{server}/{tool}",
            "query": args,
            "本次返回": len(items),
            "items": items,
            "raw_preview": summarize_for_log(data, 2000),
        }
    except McpError as e:
        return {
            "label": label,
            "error": str(e),
            "本次返回": 0,
            "items": [],
        }


async def _search_laws(
    mcp: McpClient, *, text: str, matter: Matter
) -> dict[str, Any]:
    server = "pkulaw-law-search"
    label = "法规语义检索"
    try:
        tool = await discover_tool_name(
            mcp, server, ["search_article", "searchArticle", "get_article"]
        )
        # prefer search_article
        tools = await mcp.list_tools(server)
        names = [t.get("name") for t in tools if isinstance(t, dict)]
        if "search_article" in names:
            tool = "search_article"
        args = {"text": text, "size": 5}
        try:
            data = await mcp.call_tool(server, tool, args)
        except McpError:
            data = await mcp.call_tool(server, tool, {"text": text})
            args = {"text": text}
        items = extract_items_from_law_result(data)
        for it in items:
            append_receipt(
                matter,
                tool=f"{server}/{tool}",
                query=summarize_for_log(args, 200),
                result_id=it["id"],
                url=it["url"],
            )
        return {
            "label": label,
            "tool": f"{server}/{tool}",
            "query": args,
            "本次返回": len(items),
            "items": items,
            "raw_preview": summarize_for_log(data, 2000),
        }
    except McpError as e:
        return {"label": label, "error": str(e), "本次返回": 0, "items": []}


async def _fatiao(
    mcp: McpClient, *, title: str, tiao_num: str, matter: Matter
) -> dict[str, Any]:
    server = "pkulaw-law-item-keyword"
    tool = await discover_tool_name(
        mcp, server, ["get_law_item_content", "getLawItemContent"]
    )
    args = {"title": title, "tiao_num": tiao_num}
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
        "tool": f"{server}/{tool}",
        "query": args,
        "本次返回": len(items),
        "items": items,
        "raw_preview": summarize_for_log(data, 2000),
    }


def _extract_foci(brief: str) -> list[str]:
    m = re.search(r"##\s*争议焦点\s*\n(.*?)(?=\n## |\Z)", brief, re.S)
    if not m:
        return []
    foci = []
    for line in m.group(1).splitlines():
        line = re.sub(r"^\d+[\.、)\]]\s*", "", line.strip())
        if line and line not in ("1.", "2.", "3."):
            foci.append(line)
    return foci


def _years_ago_iso(years: int) -> str:
    from datetime import datetime, timezone

    y = datetime.now(timezone.utc).year - years
    return f"{y}-01-01"


def _load_skill_snip(settings: Settings, skill: str) -> str:
    path = settings.skills_dir / skill / "SKILL.md"
    if not path.is_file():
        return f"（未找到 {skill} SKILL.md，仍须遵守仓库签发纪律）"
    text = path.read_text(encoding="utf-8")
    return text[:12000]


def _ensure_draft_footer(report: str) -> str:
    footer = "本文件为底稿，不构成法律意见；对外发出前须律师本人核验。"
    if footer not in report:
        report = report.rstrip() + "\n\n---\n\n*" + footer + "*\n"
    return report
