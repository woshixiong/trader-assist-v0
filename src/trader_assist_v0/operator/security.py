"""Single-operator HTTPS session, token, Origin and CSRF checks."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request
from starlette.responses import Response

from .contracts import OperatorConfig, OperatorCredential

COOKIE_NAME = "__Host-ts8-session"
SESSION_SECONDS = 1800


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass(frozen=True)
class Session:
    session_id: str
    csrf: str
    expires: int
    authenticated: bool


class OperatorSecurity:
    def __init__(self, config: OperatorConfig, credential: OperatorCredential) -> None:
        self.config = config
        self.credential = credential
        self._secret = credential.session_signing_secret.encode("utf-8")

    def issue(self, *, authenticated: bool) -> tuple[Session, str]:
        session = Session(
            session_id=secrets.token_urlsafe(32),
            csrf=secrets.token_urlsafe(32),
            expires=int(time.time()) + SESSION_SECONDS,
            authenticated=authenticated,
        )
        payload = json.dumps(
            {
                "sid": session.session_id,
                "csrf": session.csrf,
                "exp": session.expires,
                "auth": session.authenticated,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        message = _b64(payload)
        signature = _b64(hmac.digest(self._secret, message.encode("ascii"), "sha256"))
        return session, message + "." + signature

    def read(self, request: Request, *, authenticated: bool) -> Session:
        raw = request.cookies.get(COOKIE_NAME)
        if raw is None or len(raw) > 1024:
            raise HTTPException(401, "session required")
        try:
            message, signature = raw.split(".", 1)
            expected = _b64(hmac.digest(self._secret, message.encode("ascii"), "sha256"))
            if not hmac.compare_digest(signature, expected):
                raise ValueError("invalid signature")
            data = json.loads(_unb64(message))
            session = Session(
                session_id=str(data["sid"]),
                csrf=str(data["csrf"]),
                expires=int(data["exp"]),
                authenticated=data["auth"] is True,
            )
        except (ValueError, KeyError, TypeError, UnicodeError, binascii.Error) as exc:
            raise HTTPException(401, "invalid session") from exc
        if session.expires <= int(time.time()) or (authenticated and not session.authenticated):
            raise HTTPException(401, "expired or unauthorized session")
        return session

    def check_post(self, request: Request, session: Session) -> None:
        if request.headers.get("origin") != self.config.allowed_origin:
            raise HTTPException(403, "invalid origin")
        csrf = request.headers.get("x-csrf-token", "")
        if not csrf.isascii() or not hmac.compare_digest(csrf, session.csrf):
            raise HTTPException(403, "invalid CSRF token")
        if request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
            raise HTTPException(415, "JSON required")

    def verify_access_token(self, supplied: str) -> None:
        supplied_hash = hashlib.sha256(supplied.encode("utf-8")).digest()
        expected_hash = hashlib.sha256(self.credential.access_token.encode("utf-8")).digest()
        if not hmac.compare_digest(supplied_hash, expected_hash):
            raise HTTPException(401, "invalid access token")

    @staticmethod
    def set_cookie(response: Response, token: str) -> None:
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=SESSION_SECONDS,
            path="/",
            secure=True,
            httponly=True,
            samesite="strict",
        )
