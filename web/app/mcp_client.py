from __future__ import annotations

import json
import uuid
from typing import Any

import httpx

from .config import MCP_URLS, Settings


class McpError(Exception):
    def __init__(self, message: str, *, missing_env: str | None = None):
        super().__init__(message)
        self.missing_env = missing_env


class McpClient:
    """Minimal MCP Streamable-HTTP / JSON-RPC client for 北大法宝."""

    def __init__(self, settings: Settings, timeout: float = 90.0):
        self.settings = settings
        self.timeout = timeout
        self._sessions: dict[str, str | None] = {}

    def require_token(self) -> None:
        if not self.settings.pkulaw_ok:
            raise McpError(
                "未配置 PKULAW_ACCESS_TOKEN，无法调用北大法宝 MCP。请在环境变量中设置后重试。",
                missing_env="PKULAW_ACCESS_TOKEN",
            )

    def _headers(self, server: str, *, session_id: str | None = None) -> dict[str, str]:
        self.require_token()
        h = {
            "Authorization": f"Bearer {self.settings.pkulaw_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2025-03-26",
        }
        if session_id:
            h["Mcp-Session-Id"] = session_id
        return h

    @staticmethod
    def _parse_body(content_type: str, text: str) -> Any:
        if "text/event-stream" in content_type:
            data_chunks: list[str] = []
            for line in text.splitlines():
                if line.startswith("data:"):
                    data_chunks.append(line[5:].lstrip())
            if not data_chunks:
                raise McpError(f"MCP SSE 响应无 data 行：{text[:400]}")
            # 通常最后一条是完整 JSON-RPC 结果
            last = data_chunks[-1]
            return json.loads(last)
        if not text.strip():
            return None
        return json.loads(text)

    async def _post(self, server: str, payload: dict[str, Any]) -> Any:
        if server not in MCP_URLS:
            raise McpError(f"未知 MCP 服务：{server}")
        url = MCP_URLS[server]
        session_id = self._sessions.get(server)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                url, headers=self._headers(server, session_id=session_id), json=payload
            )
            new_sid = resp.headers.get("mcp-session-id") or resp.headers.get(
                "Mcp-Session-Id"
            )
            if new_sid:
                self._sessions[server] = new_sid
            if resp.status_code in (401, 403):
                raise McpError(
                    f"北大法宝 MCP 鉴权失败（HTTP {resp.status_code}）。请检查 PKULAW_ACCESS_TOKEN 是否有效、是否已订阅该服务。"
                )
            if resp.status_code >= 400:
                raise McpError(
                    f"MCP 调用失败 {server} HTTP {resp.status_code}: {resp.text[:800]}"
                )
            body = self._parse_body(resp.headers.get("content-type", ""), resp.text)
            if isinstance(body, dict) and body.get("error"):
                err = body["error"]
                raise McpError(f"MCP JSON-RPC 错误：{err}")
            return body

    async def initialize(self, server: str) -> None:
        req_id = str(uuid.uuid4())
        body = await self._post(
            server,
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "legal-ai-demo-web", "version": "0.1.0"},
                },
            },
        )
        # notifications/initialized（无 id）
        try:
            await self._post(
                server,
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
            )
        except McpError:
            # 部分网关对 notification 返回非标准状态，忽略
            pass
        if body is None:
            return

    async def list_tools(self, server: str) -> list[dict[str, Any]]:
        await self.initialize(server)
        req_id = str(uuid.uuid4())
        body = await self._post(
            server,
            {"jsonrpc": "2.0", "id": req_id, "method": "tools/list", "params": {}},
        )
        if not isinstance(body, dict):
            return []
        result = body.get("result") or {}
        tools = result.get("tools") or []
        return tools if isinstance(tools, list) else []

    async def call_tool(
        self, server: str, name: str, arguments: dict[str, Any]
    ) -> Any:
        await self.initialize(server)
        req_id = str(uuid.uuid4())
        body = await self._post(
            server,
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
        )
        if not isinstance(body, dict):
            return body
        result = body.get("result")
        return self._unwrap_tool_result(result)

    @staticmethod
    def _unwrap_tool_result(result: Any) -> Any:
        if result is None:
            return None
        if isinstance(result, dict) and "content" in result:
            parts = result.get("content") or []
            texts: list[str] = []
            for p in parts:
                if isinstance(p, dict) and p.get("type") == "text":
                    texts.append(str(p.get("text", "")))
            joined = "\n".join(texts).strip()
            if not joined:
                return result
            try:
                return json.loads(joined)
            except json.JSONDecodeError:
                return joined
        return result


async def discover_tool_name(client: McpClient, server: str, candidates: list[str]) -> str:
    tools = await client.list_tools(server)
    names = [t.get("name") for t in tools if isinstance(t, dict)]
    for c in candidates:
        if c in names:
            return c
    # 模糊：下划线/点号
    normalized = {n.replace(".", "_"): n for n in names if isinstance(n, str)}
    for c in candidates:
        key = c.replace(".", "_")
        if key in normalized:
            return normalized[key]
    raise McpError(
        f"服务 {server} 未找到工具 {candidates}；实际工具：{names or '（空，可能未授权）'}"
    )
