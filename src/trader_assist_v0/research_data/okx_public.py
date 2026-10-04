"""One-shot official OKX SWAP OI translation. No transport lifecycle or persistence."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from typing import Any, Literal, Protocol, Self
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from pydantic import Field, model_validator

from trader_assist_v0.contracts.common import sha256_hex

from .contracts import (
    BoundRecord,
    DatasetManifest,
    ExternalReferenceEvent,
    OpenInterestPayload,
    TimestampProvenance,
)


class OKXPublicOIProfile(BoundRecord):
    profile: Literal["OKX_GLOBAL_PUBLIC"]
    base_url: Literal["https://www.okx.com"]
    source_locator: Literal[
        "https://www.okx.com/docs-v5/en/#public-data-rest-api-get-open-interest"
    ]
    source_document_hash: str = Field(min_length=64, max_length=64)
    observed_date: str = Field(min_length=1)


class OKXOpenInterestRequest(BoundRecord):
    profile: OKXPublicOIProfile
    inst_type: Literal["SWAP"] = "SWAP"
    inst_id: str
    base_currency: str = Field(min_length=1)
    timeout_seconds: float = Field(gt=0, le=30)
    max_bytes: int = Field(gt=0, le=65536)
    max_records: Literal[1] = 1

    @model_validator(mode="after")
    def validate_request(self) -> Self:
        if not math.isfinite(self.timeout_seconds):
            raise ValueError("finite timeout required")
        if not re.fullmatch(r"[A-Z0-9]+-[A-Z0-9]+-SWAP", self.inst_id):
            raise ValueError("invalid SWAP instrument")
        if self.inst_id.split("-")[0] != self.base_currency:
            raise ValueError("base-currency identity mismatch")
        return self

    @property
    def url(self) -> str:
        return (
            self.profile.base_url
            + "/api/v5/public/open-interest?"
            + urlencode({"instType": self.inst_type, "instId": self.inst_id})
        )


class Response(Protocol):
    status: int

    def read(self, size: int) -> bytes: ...
    def geturl(self) -> str: ...
    def close(self) -> None: ...


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        raise ValueError("redirect prohibited")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def fetch_okx_open_interest(
    spec: OKXOpenInterestRequest,
    dataset: DatasetManifest,
    *,
    capability_hash: str,
    observed_at: Callable[[], int],
    use: str,
    satisfied_constraints: frozenset[str] = frozenset(),
    opener: Callable[..., Response] | None = None,
) -> ExternalReferenceEvent:
    """One invocation; caller must separately authorize actual connectivity."""
    # Revalidate supplied objects: model_construct/model_copy must not bypass admission.
    spec = OKXOpenInterestRequest.model_validate_json(spec.model_dump_json())
    dataset = DatasetManifest.model_validate_json(dataset.model_dump_json())
    dataset.require_access(use, satisfied_constraints)
    if dataset.source != "OKX" or dataset.venue != "OKX" or spec.inst_id not in dataset.instruments:
        raise ValueError("dataset identity mismatch")
    if "OI" not in dataset.datatypes:
        raise ValueError("dataset does not admit OI")
    assert dataset.rights is not None  # established by require_access, before any opener
    request = Request(spec.url, method="GET", headers={"Accept": "application/json"})
    # Explicit empty proxy mapping prevents ambient proxy environment reads.
    open_once = opener or build_opener(ProxyHandler({}), _NoRedirect()).open
    response = open_once(request, timeout=spec.timeout_seconds)
    try:
        if response.status != 200 or response.geturl() != spec.url:
            raise ValueError("HTTP response/redirect rejected")
        if urlsplit(response.geturl()).hostname != "www.okx.com":
            raise ValueError("unapproved host")
        raw = response.read(spec.max_bytes + 1)
        observation = observed_at()
    finally:
        response.close()
    if len(raw) > spec.max_bytes:
        raise ValueError("oversized response")
    body = json.loads(raw, object_pairs_hook=_unique_object)
    if not isinstance(body, dict) or body.get("code") != "0":
        raise ValueError("OKX code must be string zero")
    records = body.get("data")
    if not isinstance(records, list) or len(records) != spec.max_records:
        raise ValueError("exactly one identity record required")
    item = records[0]
    if (
        not isinstance(item, dict)
        or item.get("instType") != "SWAP"
        or item.get("instId") != spec.inst_id
    ):
        raise ValueError("unexpected instrument identity")
    timestamp = item.get("ts")
    if not isinstance(timestamp, str) or not timestamp.isascii() or not timestamp.isdecimal():
        raise ValueError("missing/invalid source ts")
    payload = OpenInterestPayload(
        oi=item["oi"],
        oi_ccy=item["oiCcy"],
        oi_usd=item["oiUsd"],
        oi_ccy_unit=spec.base_currency,
    )
    return ExternalReferenceEvent.create(
        version="EXTERNAL_REFERENCE_V1",
        provider="OKX_OFFICIAL_PUBLIC",
        venue="OKX",
        product="SWAP",
        instrument_id=spec.inst_id,
        mapping_hash=dataset.mapping_hash,
        dataset_hash=dataset.record_hash,
        capability_hash=capability_hash,
        rights_hash=dataset.rights.record_hash,
        source_mode="LIVE",
        native_id=f"{spec.inst_id}:OI:{timestamp}:{sha256_hex(raw)}",
        timestamps=TimestampProvenance(
            source_ts=timestamp,
            source_unit="ms",
            ts_event=int(timestamp) * 1_000_000,
            observed_at_ns=observation,
            receive_provenance="NOT_EXPOSED",
        ),
        payload=payload,
    )
