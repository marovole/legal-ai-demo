from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _repo_root() -> Path:
    # web/app/config.py → web/app → web → repo
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    matters_dir: Path
    template_matter: Path
    skills_dir: Path
    pkulaw_token: str
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    app_password: str
    session_secret: str
    host: str
    port: int

    @property
    def pkulaw_ok(self) -> bool:
        return bool(self.pkulaw_token.strip())

    @property
    def llm_ok(self) -> bool:
        return bool(self.openai_api_key.strip())

    @property
    def auth_required(self) -> bool:
        return bool(self.app_password.strip())


MCP_URLS = {
    "pkulaw-law-search": "https://apim-gateway.pkulaw.com/mcp-law-search-service",
    "pkulaw-case-semantic-search": "https://apim-gateway.pkulaw.com/mcp-case-search-service",
    "pkulaw-law-item-keyword": "https://apim-gateway.pkulaw.com/mcp-fatiao",
    "pkulaw-citation-validator": "https://apim-gateway.pkulaw.com/pku_citation_validator",
}


def load_settings() -> Settings:
    root = Path(os.environ.get("REPO_ROOT", str(_repo_root()))).resolve()
    matters = Path(os.environ.get("MATTERS_DIR", str(root / "matters"))).resolve()
    return Settings(
        repo_root=root,
        matters_dir=matters,
        template_matter=matters / "_template",
        skills_dir=root / ".cursor" / "skills",
        pkulaw_token=os.environ.get("PKULAW_ACCESS_TOKEN", "").strip(),
        openai_api_key=os.environ.get("OPENAI_API_KEY", "").strip(),
        openai_base_url=os.environ.get(
            "OPENAI_BASE_URL", "https://api.deepseek.com"
        ).strip(),
        openai_model=os.environ.get("OPENAI_MODEL", "deepseek-chat").strip()
        or "deepseek-chat",
        app_password=os.environ.get("APP_PASSWORD", "").strip(),
        session_secret=os.environ.get("SESSION_SECRET", "").strip()
        or "dev-only-change-me",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8080")),
    )
