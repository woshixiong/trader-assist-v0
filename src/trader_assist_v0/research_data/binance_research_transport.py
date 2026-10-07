"""Opt-in, pinned Binance Vision transport; real network is CLOSED in this phase.

No provider requests are permitted by G0_R3_BINANCE_REAL_DEV_RESEARCH_ADMISSION_1.
The implementation of HTTPS is deliberately unreachable until a separately
reviewed, independently verifiable runtime issuer is installed by Control.
"""
from __future__ import annotations

import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlsplit

from trader_assist_v0.research_data.binance_archive import (
    HOST, MAX_CHECKSUM_BYTES, MAX_ZIP_BYTES, ArchiveObject, ChecksumReceipt,
    HttpResponse, checked_http_response, checksum_receipt, require_frozen_object,
)
from trader_assist_v0.research_data.contracts import (
    IntendedUseEligibility, SourceRightsProvenance,
)

TERMS_URL = (
    "https://github.com/binance/binance-public-data/blob/"
    "f446ce3812bd4e5521f21faecd4ae3c6460e49fc/TERMS_AND_CONDITIONS.md"
)
TERMS_SHA256 = "dcf358e9d18f598a7a635fac80f6e643fa24a0e111a4d39bda47f1e246b31eb1"
DECISION_URL = (
    "https://github.com/woshixiong/trader-assist-v0/issues/161"
    "#issuecomment-6031272423"
)
# No authorization issuer or pinned final-review/run decision exists in this
# package. A caller-supplied "ALLOWED" record, booleans, or fake review URL
# MUST NEVER turn on provider I/O.
REAL_NETWORK_ISSUER = None


def require_candidate_rights(
    rights: SourceRightsProvenance,
    satisfied: frozenset[str],
) -> SourceRightsProvenance:
    """Validate the *shape* of a future rights decision, not its authenticity."""
    if type(rights) is not SourceRightsProvenance or type(satisfied) is not frozenset:
        raise TypeError("exact immutable rights contract/constraint set required")
    r = SourceRightsProvenance.model_validate_json(rights.model_dump_json())
    if (
        r.synthetic
        or r.eligibility != IntendedUseEligibility.ALLOWED
        or r.intended_use != "STRATEGY_DEV_RESEARCH"
        or r.terms_locator != TERMS_URL
        or r.terms_hash != TERMS_SHA256
        or r.observed_version != "1.0"
        or r.observed_date != "2026-08-26"
        or r.decision_locator != DECISION_URL
        or not r.attribution_constraints
        or not r.retention_constraints
        or any(
            not item or item.strip().upper().startswith(("UNKNOWN", "UNVERIFIED"))
            for item in (*r.attribution_constraints, *r.retention_constraints)
        )
    ):
        raise PermissionError("real research rights not pinned or not independently eligible")
    r.require_allowed("STRATEGY_DEV_RESEARCH", satisfied)
    return r


def _exact_url(obj: ArchiveObject, kind: str) -> tuple[str, int]:
    require_frozen_object(obj)
    if kind not in {"CHECKSUM", "ZIP"}:
        raise ValueError("only frozen .CHECKSUM/ZIP objects are supported")
    if kind == "ZIP" and obj.role_intent != "CURRENT_DEV":
        raise PermissionError("reserve ZIP/CSV access forbidden")
    url = obj.checksum_url if kind == "CHECKSUM" else obj.zip_url
    parts = urlsplit(url)
    if (
        parts.scheme != "https" or parts.netloc != "data.binance.vision"
        or parts.username is not None or parts.password is not None
        or parts.query or parts.fragment or parts.port is not None
        or not parts.path.startswith("/data/futures/um/")
        or url != (obj.zip_url + ".CHECKSUM" if kind == "CHECKSUM" else obj.zip_url)
        or not url.startswith(HOST + "/")
    ):
        raise PermissionError("unfrozen host/path or unsafe URL")
    return url, MAX_CHECKSUM_BYTES if kind == "CHECKSUM" else MAX_ZIP_BYTES


class _RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect prohibited for Binance archive transport")


def _bounded_stdlib_https(url: str, limit: int, timeout_seconds: float) -> HttpResponse:
    """Single TLS-verified GET, no proxy, redirect, auth, retries, or disk output.

    This private primitive is not a grant to call Binance: callers must pass
    the runtime issuer check in PinnedHttpsResearchTransport first.
    """
    if urlsplit(url).netloc != "data.binance.vision" or not url.startswith(HOST + "/"):
        raise PermissionError("unapproved provider")
    if not 0 < timeout_seconds <= 15 or limit not in {MAX_CHECKSUM_BYTES, MAX_ZIP_BYTES}:
        raise ValueError("unbounded transport configuration")
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _RejectRedirect(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
    )
    request = urllib.request.Request(
        url, method="GET",
        headers={"Accept-Encoding": "identity", "User-Agent": "TradeOS-research-admission/1"},
    )
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            body = response.read(limit + 1)
            headers = tuple(response.headers.items())
            result = HttpResponse(
                response.geturl(), response.status, headers, body,
                redirected=response.geturl() != url,
            )
    except urllib.error.HTTPError as exc:
        raise ValueError("non-200 Binance archive response") from exc
    return HttpResponse(
        url, 200, result.headers,
        checked_http_response(result, expected_url=url, limit=limit),
    )


@dataclass(frozen=True, slots=True)
class PinnedHttpsResearchTransport:
    """REAL I/O is fail-closed pending a new independently reviewed issuer."""

    timeout_seconds: float = 10.0

    def request(
        self, obj: ArchiveObject, kind: str, *,
        rights: SourceRightsProvenance, satisfied: frozenset[str],
    ) -> HttpResponse:
        _exact_url(obj, kind)
        require_candidate_rights(rights, satisfied)
        if REAL_NETWORK_ISSUER is None:
            raise PermissionError(
                "REAL_PROVIDER_IO_NOT_AUTHORIZED: independent ToU, jurisdiction, "
                "third-party, final-review and hash-bound run gate not issued"
            )
        # Never accept a caller-created permit: a future independently audited
        # control change must replace the unconfigured issuer and add tests.
        raise PermissionError("REAL_PROVIDER_IO_NOT_AUTHORIZED")


@dataclass(frozen=True, slots=True)
class MockOnlyResearchTransport:
    """In-memory fixture responses only; does not perform provider/network I/O."""

    responses: tuple[HttpResponse, ...]

    def request(self, obj: ArchiveObject, kind: str) -> HttpResponse:
        url, bound = _exact_url(obj, kind)
        matches = [r for r in self.responses if type(r) is HttpResponse and r.url == url]
        if len(matches) != 1:
            raise ValueError("missing/duplicate exact mock response")
        response = matches[0]
        checked_http_response(response, expected_url=url, limit=bound)
        return response


def mock_checksum_receipt(
    obj: ArchiveObject,
    mock: MockOnlyResearchTransport,
    *,
    retrieved_at_ns: int,
    retrieval_identity: str = "synthetic://offline-fixture",
) -> ChecksumReceipt:
    if (
        type(mock) is not MockOnlyResearchTransport
        or not retrieval_identity.startswith("synthetic://")
    ):
        raise PermissionError("fake-only checksum path")
    response = mock.request(obj, "CHECKSUM")
    raw = checked_http_response(
        response, expected_url=obj.checksum_url, limit=MAX_CHECKSUM_BYTES
    )
    return checksum_receipt(
        obj, raw, retrieved_at_ns=retrieved_at_ns, retrieval_identity=retrieval_identity,
    )
