# mypy: disable-error-code="import-not-found"
"""Causal research reader over official native HL records; never an archiver/strategy."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

CONTEXT_AGES = {"mark": 30, "index": 30, "funding": 60, "oi": 60}
CONTEXT_TYPES = {
    "MarkPriceUpdate": "mark",
    "IndexPriceUpdate": "index",
    "FundingRateUpdate": "funding",
    "HyperliquidOpenInterest": "oi",
}


def context_identity(value: Any) -> tuple[Any, str, str]:
    event = getattr(value, "data", value)
    kind = CONTEXT_TYPES.get(type(event).__name__)
    if kind is None:
        raise ValueError("UNSUPPORTED_CONTEXT_TYPE")
    raw = event.to_json() if kind == "oi" else json.dumps(event.to_dict(), sort_keys=True)
    return event, kind, hashlib.sha256(raw.encode()).hexdigest()


class ContextResearchReader:
    """One latest typed input per resolved instrument/family; hash references only in proof."""

    def __init__(self, instrument_ids: set[str]) -> None:
        self.instrument_ids = instrument_ids
        self.latest: dict[str, Any] = {}
        self.hashes: dict[str, str] = {}
        self.rejects: dict[str, int] = {}

    def consume(self, value: Any, *, now_ns: int) -> bool:
        event, kind, digest = context_identity(value)
        key = f"{event.instrument_id}:{kind}"
        reason = None
        prior = self.latest.get(key)
        if str(event.instrument_id) not in self.instrument_ids:
            reason = "UNRESOLVED_IDENTITY"
        elif not 0 < event.ts_event <= event.ts_init <= now_ns:
            reason = "NONCAUSAL_CLOCK"
        elif (
            now_ns - event.ts_event > CONTEXT_AGES[kind] * 1_000_000_000
            or now_ns - event.ts_init > CONTEXT_AGES[kind] * 1_000_000_000
        ):
            reason = "STALE"
        elif prior is not None and digest == self.hashes[key]:
            reason = "DUPLICATE"
        elif prior is not None and (event.ts_event, event.ts_init) < (
            prior.ts_event,
            prior.ts_init,
        ):
            reason = "OUT_OF_ORDER"
        if reason is not None:
            self.rejects[reason] = self.rejects.get(reason, 0) + 1
            return False
        self.latest[key], self.hashes[key] = event, digest
        return True


def read_context_run(root: Path, instance_id: str) -> list[Any]:
    """Bounded closed-run proof using native custom conversion; never rolling promotion."""
    from nautilus_trader.adapters.hyperliquid import HyperliquidOpenInterest  # noqa: F401
    from nautilus_trader.common import Environment
    from nautilus_trader.model import NautilusDataType
    from nautilus_trader.persistence import ParquetDataCatalog

    stage = root / "live" / instance_id
    if list(stage.rglob("*.feather.partial")):
        raise ValueError("CONTEXT_REQUIRES_SEALED_NATIVE_RUN")
    # Do not pretend the known cross-file equal-ts_init boundary is fixed.
    if (
        sum(
            "hyperliquidopeninterest" in str(p).replace("_", "").lower()
            for p in stage.rglob("*.feather")
        )
        > 1
    ):
        raise ValueError("OI_MULTIPLE_SOURCE_BOUNDARIES_UNQUALIFIED")
    catalog = ParquetDataCatalog(str(root))
    data = [x for x in catalog.read_live_run(instance_id) if type(x).__name__ in CONTEXT_TYPES]
    custom = NautilusDataType.Custom("HyperliquidOpenInterest")
    catalog.convert_stream_to_data(instance_id, custom, environment=Environment.LIVE)
    data.extend(catalog.query_custom_data(custom))
    return sorted(data, key=lambda x: (x.ts_init, x.ts_event))


def context_proof(
    root: Path, instance_id: str, resolved_ids: set[str], expected: dict[str, str]
) -> dict[str, Any]:
    """Source callback hash must actually occur in sealed native readback; no subscription PASS."""
    data = read_context_run(root, instance_id)
    reader = ContextResearchReader(resolved_ids)
    seen = set()
    for value in data:
        event, kind, digest = context_identity(value)
        seen.add(digest)
        # Replay admission at native knowledge time, never wall-clock re-date records.
        reader.consume(value, now_ns=event.ts_init)
    required = {f"{identity}:{kind}" for identity in resolved_ids for kind in CONTEXT_AGES}
    missing = sorted(required - reader.latest.keys())
    absent = sorted(set(expected.values()) - seen)
    if missing or absent or not expected or set(expected) != required:
        raise ValueError(f"CONTEXT_NOT_USABLE:missing={missing},source_hashes_absent={absent}")
    return {
        "status": "USABLE_BOUNDED_SEALED_NATIVE_CONTEXT",
        "streams": sorted(required),
        "source_callback_hashes": expected,
        "readback_count": len(data),
        "reader": "CAUSAL_TYPED_RESEARCH_INPUT_NO_STRATEGY_OR_ORDER",
        "retained_source": True,
        "native_version": "2.0.0rc7",
        "reader_rejections": reader.rejects,
        "rolling_catalog": "UNQUALIFIED",
    }
