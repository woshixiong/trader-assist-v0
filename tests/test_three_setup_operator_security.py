from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from test_three_setup_operator_contracts import make_config, make_credential, make_source

from trader_assist_v0.operator.service import create_app


def _login(client: TestClient) -> str:
    page = client.get("/login")
    csrf = re.search(r'data-csrf="([^"]+)', page.text)
    assert csrf is not None
    response = client.post(
        "/api/login",
        json={"access_token": "A" * 48},
        headers={"Origin": "https://operator.test", "X-CSRF-Token": csrf.group(1)},
    )
    assert response.status_code == 200
    return str(response.json()["csrf"])


def test_https_host_origin_session_csrf_and_headers(tmp_path: Path) -> None:
    make_source(tmp_path / "runtime.sqlite", created_ms=time.time_ns() // 1_000_000)
    app = create_app(make_config(tmp_path), make_credential())
    with TestClient(app, base_url="https://operator.test") as client:
        assert client.get("/login", headers={"Host": "wrong.test"}).status_code == 400
        login = client.get("/login")
        cookie = login.headers["set-cookie"]
        assert "__Host-ts8-session=" in cookie
        assert "secure" in cookie.lower() and "httponly" in cookie.lower()
        assert "samesite=strict" in cookie.lower() and "path=/" in cookie.lower()
        for header in (
            "content-security-policy",
            "x-frame-options",
            "x-content-type-options",
            "referrer-policy",
            "cache-control",
        ):
            assert header in login.headers
        assert "frame-ancestors 'none'" in login.headers["content-security-policy"]
        csrf = re.search(r'data-csrf="([^"]+)', login.text)
        assert csrf is not None
        assert (
            client.post(
                "/api/login",
                json={"access_token": "A" * 48},
                headers={"Origin": "https://evil.test", "X-CSRF-Token": csrf.group(1)},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/login",
                json={"access_token": "A" * 48},
                headers={"Origin": "https://operator.test", "X-CSRF-Token": "wrong"},
            ).status_code
            == 403
        )
        auth_csrf = _login(client)
        assert client.get("/").status_code == 200
        assert client.post(
            "/api/action", json={}, headers={"Origin": "https://operator.test"}
        ).status_code in {403, 422}
        assert auth_csrf
        assert client.get("/", headers={"X-Forwarded-Proto": "https"}).status_code == 403
        assert client.get("/static/../security.py").status_code == 404
        assert "access-control-allow-origin" not in client.get("/").headers


def test_plaintext_and_field_injection_fail_closed(tmp_path: Path) -> None:
    make_source(tmp_path / "runtime.sqlite", created_ms=time.time_ns() // 1_000_000)
    app = create_app(make_config(tmp_path), make_credential())
    with TestClient(app, base_url="http://operator.test") as client:
        assert client.get("/login").status_code == 403
    with TestClient(app, base_url="https://operator.test") as client:
        csrf = _login(client)
        response = client.post(
            "/api/action",
            json={
                "shadow_id": "s" * 64,
                "package_id": "p" * 64,
                "package_hash": "h" * 64,
                "action_key": "action-key-12345678",
                "action": "APPROVE",
                "quantity": "999999",
            },
            headers={"Origin": "https://operator.test", "X-CSRF-Token": csrf},
        )
        assert response.status_code == 422


def test_sse_connection_only_reads_committed_revision(tmp_path: Path) -> None:
    make_source(tmp_path / "runtime.sqlite", created_ms=time.time_ns() // 1_000_000)
    app = create_app(make_config(tmp_path), make_credential())
    endpoint = next(
        route.endpoint for route in app.routes if getattr(route, "path", "") == "/events"
    )
    from trader_assist_v0.operator.security import OperatorSecurity

    _, cookie = OperatorSecurity(make_config(tmp_path), make_credential()).issue(authenticated=True)

    class RequestStub:
        def __init__(self) -> None:
            self.cookies = {"__Host-ts8-session": cookie}

        async def is_disconnected(self) -> bool:
            return False

    async def connect_twice() -> tuple[str, str]:
        first = await endpoint(RequestStub())
        first_chunk = await anext(first.body_iterator)
        await first.body_iterator.aclose()
        second = await endpoint(RequestStub())
        second_chunk = await anext(second.body_iterator)
        await second.body_iterator.aclose()
        return first_chunk, second_chunk

    first, second = asyncio.run(connect_twice())
    assert first == second == "event: revision\ndata: 0\n\n"


def test_session_expiry_and_template_escape(tmp_path: Path) -> None:
    make_source(
        tmp_path / "runtime.sqlite", created_ms=time.time_ns() // 1_000_000,
        instrument="<script>alert(1)</script>",
    )
    app = create_app(make_config(tmp_path), make_credential())
    with TestClient(app, base_url="https://operator.test") as client:
        _login(client)
        dashboard = client.get("/")
        assert "&lt;script&gt;" in dashboard.text
        assert "<script>alert(1)</script>" not in dashboard.text
        future = time.time() + 4000
        with patch("trader_assist_v0.operator.security.time.time", return_value=future):
            assert client.get("/").status_code == 401
