from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import Settings

MATTER_NAME_RE = re.compile(r"^[\w\u4e00-\u9fff-]{1,64}$")

MATTER_FILES = (
    "brief.md",
    "search-log.md",
    "report.md",
    "lawyer-delta.md",
    "audit.md",
    "signoff.md",
)


@dataclass
class Matter:
    name: str
    path: Path

    def read(self, filename: str) -> str:
        path = self.path / filename
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8")

    def write(self, filename: str, content: str) -> None:
        if filename not in MATTER_FILES:
            raise ValueError(f"不允许写入文件：{filename}")
        (self.path / filename).write_text(content, encoding="utf-8")


class MatterStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.matters_dir

    def list_matters(self) -> list[Matter]:
        if not self.root.is_dir():
            return []
        items: list[Matter] = []
        for p in sorted(self.root.iterdir()):
            if not p.is_dir():
                continue
            if p.name.startswith("_") or p.name.startswith("."):
                continue
            if p.name == "_template":
                continue
            items.append(Matter(name=p.name, path=p))
        return items

    def get(self, name: str) -> Matter:
        if not MATTER_NAME_RE.match(name) or name in ("_template", ".", ".."):
            raise ValueError("卷宗短名不合法")
        path = self.root / name
        if not path.is_dir():
            raise FileNotFoundError(name)
        return Matter(name=name, path=path)

    def create(self, name: str) -> Matter:
        name = name.strip()
        if not MATTER_NAME_RE.match(name) or name.startswith("_"):
            raise ValueError(
                "短名仅允许中文、字母、数字、下划线、连字符，长度 1–64，且不能以 _ 开头"
            )
        dest = self.root / name
        if dest.exists():
            raise FileExistsError(f"卷宗已存在：{name}")
        src = self.settings.template_matter
        if not src.is_dir():
            raise FileNotFoundError("缺少 matters/_template，无法开档")
        shutil.copytree(src, dest)
        return Matter(name=name, path=dest)


def run_gate_script(script_name: str, matter_path: Path, repo_root: Path) -> dict:
    script = repo_root / "scripts" / script_name
    proc = subprocess.run(
        [sys.executable, str(script), str(matter_path)],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    ok = proc.returncode == 0
    # check_signoff: 2 = 修正后可签发
    label = "通过" if ok else "未通过"
    if script_name == "check_signoff.py" and proc.returncode == 2:
        label = "修正后可签发（不可导出）"
    return {
        "script": script_name,
        "ok": ok,
        "returncode": proc.returncode,
        "label": label,
        "stdout": out,
        "stderr": err,
    }
