from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import markdown as md
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .auth import install_session, is_logged_in, logout, require_login, try_login
from .config import load_settings
from .llm import LlmClient
from .matter_store import MatterStore, MATTER_FILES, run_gate_script
from .mcp_client import McpClient, McpError
from .workflows.case_report import run_case_research_report
from .workflows.citation_audit import run_citation_audit

BASE_DIR = Path(__file__).resolve().parent
settings = load_settings()
store = MatterStore(settings)
mcp = McpClient(settings)
llm = LlmClient(settings)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    print(f"listening on {settings.host}:{settings.port}", flush=True)
    yield


app = FastAPI(
    title="律师一案一档", docs_url=None, redoc_url=None, lifespan=_lifespan
)
install_session(app, settings)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _flash(request: Request, message: str, level: str = "info") -> None:
    request.session["flash"] = {"message": message, "level": level}


def _pop_flash(request: Request) -> dict | None:
    return request.session.pop("flash", None)


def _ctx(request: Request, **kwargs):
    return {
        "request": request,
        "settings": settings,
        "auth_required": settings.auth_required,
        "logged_in": is_logged_in(request, settings),
        "flash": _pop_flash(request),
        "pkulaw_ok": settings.pkulaw_ok,
        "llm_ok": settings.llm_ok,
        **kwargs,
    }


@app.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "pkulaw_configured": settings.pkulaw_ok,
        "llm_configured": settings.llm_ok,
    }


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if not settings.auth_required:
        return RedirectResponse("/", status_code=303)
    if is_logged_in(request, settings):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request, "login.html", _ctx(request, error=None)
    )


@app.post("/login")
async def login_submit(request: Request, password: str = Form(...)):
    if try_login(request, settings, password):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request,
        "login.html",
        _ctx(request, error="密码错误"),
        status_code=401,
    )


@app.post("/logout")
async def logout_post(request: Request):
    logout(request)
    return RedirectResponse("/login" if settings.auth_required else "/", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    redir = require_login(request, settings)
    if redir:
        return redir
    matters = store.list_matters()
    return templates.TemplateResponse(
        request, "home.html", _ctx(request, matters=matters)
    )


@app.post("/matters/create")
async def create_matter(request: Request, name: str = Form(...)):
    redir = require_login(request, settings)
    if redir:
        return redir
    try:
        m = store.create(name.strip())
        _flash(request, f"已开档：{m.name}", "ok")
        return RedirectResponse(f"/matters/{m.name}", status_code=303)
    except (ValueError, FileExistsError, FileNotFoundError) as e:
        _flash(request, str(e), "error")
        return RedirectResponse("/", status_code=303)


@app.get("/matters/{name}", response_class=HTMLResponse)
async def matter_page(request: Request, name: str):
    redir = require_login(request, settings)
    if redir:
        return redir
    try:
        matter = store.get(name)
    except (ValueError, FileNotFoundError):
        _flash(request, "卷宗不存在", "error")
        return RedirectResponse("/", status_code=303)

    files = {f: matter.read(f) for f in MATTER_FILES}
    gates = {
        "receipts": run_gate_script(
            "check_receipts.py", matter.path, settings.repo_root
        ),
        "signoff": run_gate_script(
            "check_signoff.py", matter.path, settings.repo_root
        ),
    }
    rendered = {
        k: md.markdown(v, extensions=["tables", "fenced_code"])
        for k, v in files.items()
        if k != "brief.md"
    }
    return templates.TemplateResponse(
        request,
        "matter.html",
        _ctx(
            request,
            matter=matter,
            files=files,
            rendered=rendered,
            gates=gates,
        ),
    )


@app.post("/matters/{name}/brief")
async def save_brief(request: Request, name: str, brief: str = Form(...)):
    redir = require_login(request, settings)
    if redir:
        return redir
    try:
        matter = store.get(name)
        matter.write("brief.md", brief.replace("\r\n", "\n"))
        _flash(request, "已保存 brief.md", "ok")
    except (ValueError, FileNotFoundError) as e:
        _flash(request, str(e), "error")
        return RedirectResponse("/", status_code=303)
    return RedirectResponse(f"/matters/{name}", status_code=303)


@app.post("/matters/{name}/lawyer-delta")
async def save_delta(request: Request, name: str, content: str = Form(...)):
    redir = require_login(request, settings)
    if redir:
        return redir
    try:
        matter = store.get(name)
        matter.write("lawyer-delta.md", content.replace("\r\n", "\n"))
        _flash(request, "已保存 lawyer-delta.md", "ok")
    except (ValueError, FileNotFoundError) as e:
        _flash(request, str(e), "error")
        return RedirectResponse("/", status_code=303)
    return RedirectResponse(f"/matters/{name}", status_code=303)


@app.post("/matters/{name}/run-report")
async def run_report(request: Request, name: str):
    redir = require_login(request, settings)
    if redir:
        return redir
    try:
        matter = store.get(name)
        result = await run_case_research_report(
            settings=settings, matter=matter, mcp=mcp, llm=llm
        )
        _flash(request, result["message"], "ok")
    except McpError as e:
        _flash(request, str(e), "error")
    except Exception as e:  # noqa: BLE001
        _flash(request, f"出报告失败：{e}", "error")
    return RedirectResponse(f"/matters/{name}", status_code=303)


@app.post("/matters/{name}/run-audit")
async def run_audit(request: Request, name: str):
    redir = require_login(request, settings)
    if redir:
        return redir
    try:
        matter = store.get(name)
        result = await run_citation_audit(
            settings=settings, matter=matter, mcp=mcp, llm=llm
        )
        _flash(request, result["message"], "ok")
    except McpError as e:
        _flash(request, str(e), "error")
    except Exception as e:  # noqa: BLE001
        _flash(request, f"引用核验失败：{e}", "error")
    return RedirectResponse(f"/matters/{name}", status_code=303)


@app.post("/matters/{name}/run-gates")
async def run_gates(request: Request, name: str):
    redir = require_login(request, settings)
    if redir:
        return redir
    try:
        matter = store.get(name)
        r1 = run_gate_script("check_receipts.py", matter.path, settings.repo_root)
        r2 = run_gate_script("check_signoff.py", matter.path, settings.repo_root)
        msg = (
            f"回执闸门：{r1['label']}；签发闸门：{r2['label']}。"
            f"详情见页面「闸门检查」。"
        )
        level = "ok" if r1["ok"] and r2["ok"] else "error"
        _flash(request, msg, level)
    except (ValueError, FileNotFoundError) as e:
        _flash(request, str(e), "error")
    return RedirectResponse(f"/matters/{name}", status_code=303)


@app.exception_handler(404)
async def not_found(request: Request, exc):  # noqa: ANN001
    return HTMLResponse("<h1>未找到</h1><p><a href='/'>返回卷宗列表</a></p>", status_code=404)
