"""Private zero-write FastAPI operator; HTTP clients never own transitions."""

from __future__ import annotations

import asyncio
import contextlib
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from .approval import OperatorBlocked, OperatorEngine
from .contracts import OperatorConfig, OperatorCredential
from .dashboard import build_dashboard
from .security import OperatorSecurity

ROOT = Path(__file__).resolve().parent


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    access_token: str = Field(min_length=1, max_length=1024)


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    shadow_id: str = Field(min_length=64, max_length=64)
    package_id: str = Field(min_length=64, max_length=64)
    package_hash: str = Field(min_length=64, max_length=64)
    action_key: str = Field(min_length=16, max_length=160)
    action: str


def create_app(
    config: OperatorConfig,
    credential: OperatorCredential,
    *,
    engine: OperatorEngine | None = None,
) -> FastAPI:
    security = OperatorSecurity(config, credential)
    operator = engine or OperatorEngine(config)
    templates = Jinja2Templates(directory=str(ROOT / "templates"))

    async def reconcile_loop() -> None:
        while True:
            try:
                await asyncio.to_thread(operator.reconcile_once)
            except Exception:
                # Only the operator loop is affected; the next bounded wake
                # re-reads durable pending rows. Never signal Nautilus control.
                pass
            await asyncio.sleep(config.reconcile_interval_ms / 1000)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        task = asyncio.create_task(reconcile_loop(), name="ts8-approval-reconciler")
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(config.allowed_hosts))
    app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

    @app.middleware("http")
    async def secure_response(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        blocked = request.url.scheme != "https" or any(
            name in request.headers
            for name in ("forwarded", "x-forwarded-proto", "x-forwarded-host", "x-forwarded-for")
        )
        if blocked:
            response: Response = JSONResponse(
                {"detail": "HTTPS authority required"}, status_code=403
            )
        else:
            response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
            "connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path != "/static/operator.css" and (
            request.url.path != "/static/operator.js"
        ):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request) -> HTMLResponse:
        session, token = security.issue(authenticated=False)
        response = templates.TemplateResponse(
            request, "login.html", {"csrf": session.csrf, "origin": config.allowed_origin}
        )
        security.set_cookie(response, token)
        return response

    @app.post("/api/login")
    async def login(request: Request) -> JSONResponse:
        session = security.read(request, authenticated=False)
        security.check_post(request, session)
        try:
            body = LoginRequest.model_validate(await request.json())
        except (ValidationError, ValueError) as exc:
            raise HTTPException(422, "invalid login body") from exc
        security.verify_access_token(body.access_token)
        authenticated, token = security.issue(authenticated=True)
        response = JSONResponse({"ok": True, "csrf": authenticated.csrf})
        security.set_cookie(response, token)
        return response

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        session = security.read(request, authenticated=True)
        return templates.TemplateResponse(
            request, "dashboard.html", dashboard_context(session.csrf)
        )

    def dashboard_context(csrf: str, *, notice: str = "") -> dict[str, object]:
        model = build_dashboard(operator, config)
        package = model.package
        blocked = model.package_gate != "PASS"
        reason = (
            "Old package consumed. A fresh causal trigger, package and Human "
            "approval are required."
            if model.state == "WAITING_FRESH_TRIGGER"
            else "Package is terminal or unavailable for Human action."
        ) if blocked else ""
        try:
            revision = operator.revision()
            recent_terminal = operator.recent_terminal()
        except Exception:
            revision, recent_terminal = -1, None
        return {
            "model": model, "package": package, "details": model.details,
            "state": model.state, "blocked": blocked, "reason": reason,
            "csrf": csrf, "revision": revision, "recent_terminal": recent_terminal,
            "configured_mode": config.approval_mode, "action_key": secrets.token_urlsafe(24),
            "notice": notice,
        }

    @app.post("/action", response_class=HTMLResponse)
    async def form_action(request: Request) -> Response:
        session = security.read(request, authenticated=True)
        fields = await security.check_action_form(request, session)
        try:
            body = ActionRequest.model_validate(fields)
        except ValidationError as exc:
            raise HTTPException(422, "invalid action body") from exc
        try:
            operator.human_action_record(
                shadow_id=body.shadow_id, package_id=body.package_id,
                package_hash=body.package_hash, action_key=body.action_key,
                action=body.action, session_id=session.session_id,
            )
        except OperatorBlocked as exc:
            return templates.TemplateResponse(
                request, "dashboard.html", dashboard_context(session.csrf, notice=str(exc)),
                status_code=409,
            )
        return RedirectResponse("/", status_code=303)

    @app.post("/api/action")
    async def action(request: Request) -> JSONResponse:
        session = security.read(request, authenticated=True)
        security.check_post(request, session)
        try:
            body = ActionRequest.model_validate(await request.json())
        except (ValidationError, ValueError) as exc:
            raise HTTPException(422, "invalid action body") from exc
        try:
            result = operator.human_action_record(
                shadow_id=body.shadow_id,
                package_id=body.package_id,
                package_hash=body.package_hash,
                action_key=body.action_key,
                action=body.action,
                session_id=session.session_id,
            )
        except OperatorBlocked as exc:
            raise HTTPException(409, str(exc)) from exc
        return JSONResponse({
            "state": result.state,
            "observed_server_ms": result.observed_server_ms,
            "submission_status": "NOT_SUBMITTED",
        })

    @app.get("/events")
    async def events(request: Request) -> StreamingResponse:
        security.read(request, authenticated=True)

        async def revisions() -> AsyncIterator[str]:
            last = -1
            while not await request.is_disconnected():
                try:
                    current = operator.revision()
                except Exception:
                    current = last
                if current != last:
                    yield f"event: revision\ndata: {current}\n\n"
                    last = current
                await asyncio.sleep(1)

        return StreamingResponse(revisions(), media_type="text/event-stream")

    return app
