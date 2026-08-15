from __future__ import annotations

from openai import AsyncOpenAI

from .config import Settings
from .mcp_client import McpError


class LlmClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def require_key(self) -> None:
        if not self.settings.llm_ok:
            raise McpError(
                "未配置 OPENAI_API_KEY，无法调用大模型生成底稿。请设置 OPENAI_API_KEY（及可选 OPENAI_BASE_URL / OPENAI_MODEL）。",
                missing_env="OPENAI_API_KEY",
            )

    def _client(self) -> AsyncOpenAI:
        self.require_key()
        return AsyncOpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url or None,
        )

    async def complete(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> str:
        client = self._client()
        resp = await client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        choice = resp.choices[0].message.content or ""
        return choice.strip()
