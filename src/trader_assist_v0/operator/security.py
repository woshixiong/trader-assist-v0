"""Single-operator HTTPS session, token, Origin and CSRF checks."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
import secrets
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

from fastapi import HTTPException, Request
from starlette.responses import Response

from .contracts import OperatorConfig, OperatorCredential

COOKIE_NAME = "__Host-ts8-session"
SESSION_SECONDS = 1800
FORM_BODY_LIMIT = 4096
FORM_FIELDS = frozenset({
    "csrf_token", "shadow_id", "package_id", "package_hash", "action_key", "action",
})


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

    async def check_action_form(self, request: Request, session: Session) -> dict[str, str]:
        """Verify the one bounded HTML mutation transport in the security owner."""
        origins = request.headers.getlist("origin")
        if len(origins) != 1 or origins[0] != self.config.allowed_origin:
            raise HTTPException(403, "invalid origin")
        media_types = request.headers.getlist("content-type")
        if media_types != ["application/x-www-form-urlencoded"]:
            raise HTTPException(415, "form media type required")
        if request.headers.get("content-encoding") not in (None, "identity"):
            raise HTTPException(415, "encoded form body unsupported")
        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) < 0 or int(declared) > FORM_BODY_LIMIT:
                    raise HTTPException(413, "form body too large")
            except ValueError as exc:
                raise HTTPException(400, "invalid content length") from exc
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > FORM_BODY_LIMIT:
                raise HTTPException(413, "form body too large")
            body.extend(chunk)
        try:
            encoded = body.decode("ascii")
            if re.search(r"%(?![0-9A-Fa-f]{2})", encoded):
                raise ValueError("malformed percent escape")
            pairs = parse_qsl(
                encoded, keep_blank_values=True, strict_parsing=True,
                encoding="utf-8", errors="strict", max_num_fields=len(FORM_FIELDS),
            )
        except (UnicodeError, ValueError) as exc:
            raise HTTPException(400, "malformed form body") from exc
        fields: dict[str, str] = {}
        for name, value in pairs:
            if name not in FORM_FIELDS or name in fields or not value.isascii() or (
                not value.isprintable()
            ):
                raise HTTPException(400, "invalid form fields")
            fields[name] = value
        if set(fields) != FORM_FIELDS:
            raise HTTPException(400, "incomplete form fields")
        csrf = fields.pop("csrf_token")
        if not hmac.compare_digest(csrf, session.csrf):
            raise HTTPException(403, "invalid CSRF token")
        return fields

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
