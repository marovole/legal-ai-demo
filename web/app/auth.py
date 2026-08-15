from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from .config import Settings


def install_session(app, settings: Settings) -> None:
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        same_site="lax",
        https_only=False,
        max_age=60 * 60 * 12,
    )


def is_logged_in(request: Request, settings: Settings) -> bool:
    if not settings.auth_required:
        return True
    return bool(request.session.get("authed"))


def require_login(request: Request, settings: Settings):
    if is_logged_in(request, settings):
        return None
    return RedirectResponse(url="/login", status_code=303)


def try_login(request: Request, settings: Settings, password: str) -> bool:
    if not settings.auth_required:
        request.session["authed"] = True
        return True
    if password == settings.app_password:
        request.session["authed"] = True
        return True
    return False


def logout(request: Request) -> None:
    request.session.clear()
