"""Pure, bounded context evidence; this module owns no transport or scheduler."""

from __future__ import annotations

import hashlib
import weakref
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.first_launch.market_data import (
    ActiveAssetContext,
    _validated_context,
)


class ContextError(ValueError):
    pass


class PriceOiClassification(StrEnum):
    PRICE_UP_OI_UP = "PRICE_UP_OI_UP"
    PRICE_UP_OI_DOWN = "PRICE_UP_OI_DOWN"
    PRICE_DOWN_OI_UP = "PRICE_DOWN_OI_UP"
    PRICE_DOWN_OI_DOWN = "PRICE_DOWN_OI_DOWN"


def _hash(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


# Context values are evidence authorities, not merely convenient value objects.
# A local issuance registry prevents constructors/copies from gaining authority.
_ISSUED: dict[int, tuple[weakref.ReferenceType[object], str]] = {}


def _issue(value: object, fingerprint: str) -> object:
    key = id(value)

    def release(reference: weakref.ReferenceType[object]) -> None:
        current = _ISSUED.get(key)
        if current is not None and current[0] is reference:
            del _ISSUED[key]

    _ISSUED[key] = (weakref.ref(value, release), fingerprint)
    return value


def _issued(value: object, fingerprint: str) -> bool:
    entry = _ISSUED.get(id(value))
    return entry is not None and entry[0]() is value and entry[1] == fingerprint


@dataclass(frozen=True)
class ContextObservation:
    mark_price: Decimal
    mid_price: Decimal | None
    open_interest: Decimal
    funding: Decimal
    source_time_ms: int | None
    received_at: datetime
    receive_sequence: int
    evidence_hash: str
    reference_price: Decimal
    mark_mid_basis_bps: Decimal | None
    canonical_hash: str

    @classmethod
    def from_active_context(cls, value: ActiveAssetContext) -> ContextObservation:
        value = _validated_context(value)
        received = value.evidence.received_at.astimezone(UTC)
        basis = (
            None
            if value.mid_px is None
            else (value.mark_px - value.mid_px) / value.mid_px * Decimal("10000")
        )
        body = {
            "mark_price": value.mark_px,
            "mid_price": value.mid_px,
            "open_interest": value.open_interest,
            "funding": value.funding,
            "source_time_ms": value.source_time_ms,
            "received_at": received.isoformat(),
            "receive_sequence": value.evidence.receive_sequence,
            "evidence_hash": value.evidence.sha256,
            "reference_price": value.reference_price,
            "mark_mid_basis_bps": basis,
        }
        observation = cls(
            value.mark_px,
            value.mid_px,
            value.open_interest,
            value.funding,
            value.source_time_ms,
            received,
            value.evidence.receive_sequence,
            value.evidence.sha256,
            value.reference_price or Decimal(0),
            basis,
            _hash(body),
        )
        return _issue(observation, _observation_fingerprint(observation))  # type: ignore[return-value]

    def payload(self) -> dict[str, object]:
        return {
            "mark_price": self.mark_price,
            "mid_price": self.mid_price,
            "open_interest": self.open_interest,
            "funding": self.funding,
            "source_time_ms": self.source_time_ms,
            "received_at": self.received_at.isoformat(),
            "receive_sequence": self.receive_sequence,
            "evidence_hash": self.evidence_hash,
            "reference_price": self.reference_price,
            "mark_mid_basis_bps": self.mark_mid_basis_bps,
        }


def _observation_fingerprint(value: ContextObservation) -> str:
    if type(value) is not ContextObservation or value.canonical_hash != _hash(value.payload()):
        raise ContextError("CONTEXT_OBSERVATION_INVALID")
    if value.received_at.tzinfo is not UTC or value.reference_price <= 0:
        raise ContextError("CONTEXT_OBSERVATION_INVALID")
    return value.canonical_hash


def _validated_context_observation(value: object) -> ContextObservation:
    try:
        if not _issued(value, _observation_fingerprint(value)):  # type: ignore[arg-type]
            raise ContextError("CONTEXT_OBSERVATION_AUTHORITY_INVALID")
    except (AttributeError, TypeError, ValueError) as exc:
        raise ContextError("CONTEXT_OBSERVATION_AUTHORITY_INVALID") from exc
    return value  # type: ignore[return-value]


@dataclass(frozen=True)
class ContextSummary:
    current: ContextObservation
    baseline_5m: ContextObservation | None
    baseline_15m: ContextObservation | None
    summary_cutoff: datetime
    oi_delta_5m: Decimal | None
    oi_pct_delta_5m: Decimal | None
    oi_delta_15m: Decimal | None
    oi_pct_delta_15m: Decimal | None
    funding_delta_5m: Decimal | None
    funding_delta_15m: Decimal | None
    classification_5m: PriceOiClassification | None
    classification_15m: PriceOiClassification | None
    canonical_hash: str
    selection_proof: tuple[ContextObservation, ...] = ()

    @classmethod
    def create(
        cls,
        current: ContextObservation,
        five: ContextObservation | None,
        fifteen: ContextObservation | None,
        cutoff: datetime,
    ) -> ContextSummary:
        """Create a value for display only; it is never plan-issued authority."""
        return _build_summary(current, five, fifteen, cutoff, (), issue=False)


def _build_summary(
    current: ContextObservation,
    five: ContextObservation | None,
    fifteen: ContextObservation | None,
    cutoff: datetime,
    proof: tuple[ContextObservation, ...],
    *,
    issue: bool,
) -> ContextSummary:
    current = _validated_context_observation(current)
    if five is not None:
        five = _validated_context_observation(five)
    if fifteen is not None:
        fifteen = _validated_context_observation(fifteen)
    if cutoff.tzinfo is None:
        raise ContextError("CONTEXT_CUTOFF_INVALID")
    cutoff = cutoff.astimezone(UTC)
    if (
        current.received_at > cutoff
        or (five is not None and five.received_at > current.received_at)
        or (fifteen is not None and fifteen.received_at > current.received_at)
    ):
        raise ContextError("CONTEXT_SUMMARY_CAUSAL_INVALID")

    def values(
        base: ContextObservation | None,
    ) -> tuple[Decimal | None, Decimal | None, Decimal | None, PriceOiClassification | None]:
        if base is None:
            return None, None, None, None
        oi = current.open_interest - base.open_interest
        pct = None if base.open_interest == 0 else oi / base.open_interest * Decimal("100")
        price = current.reference_price - base.reference_price
        category = None
        if price and oi:
            category = PriceOiClassification(
                "PRICE_" + ("UP" if price > 0 else "DOWN") + "_OI_" + ("UP" if oi > 0 else "DOWN")
            )
        return oi, pct, current.funding - base.funding, category

    oi5, pct5, funding5, cls5 = values(five)
    oi15, pct15, funding15, cls15 = values(fifteen)
    ordered = tuple(sorted(proof, key=lambda item: (item.received_at, item.receive_sequence)))
    if ordered != proof or any(item.received_at > cutoff for item in ordered):
        raise ContextError("CONTEXT_SELECTION_PROOF_INVALID")
    body = {
        "current": current.payload(),
        "current_hash": current.canonical_hash,
        "baseline_5m": None if five is None else five.payload(),
        "baseline_5m_hash": None if five is None else five.canonical_hash,
        "baseline_15m": None if fifteen is None else fifteen.payload(),
        "baseline_15m_hash": None if fifteen is None else fifteen.canonical_hash,
        "summary_cutoff": cutoff.isoformat(),
        "oi_delta_5m": oi5,
        "oi_pct_delta_5m": pct5,
        "oi_delta_15m": oi15,
        "oi_pct_delta_15m": pct15,
        "funding_delta_5m": funding5,
        "funding_delta_15m": funding15,
        "classification_5m": cls5,
        "classification_15m": cls15,
        "selection_proof": [item.payload() for item in ordered],
        "selection_proof_hashes": [item.canonical_hash for item in ordered],
    }
    summary = ContextSummary(
        current,
        five,
        fifteen,
        cutoff,
        oi5,
        pct5,
        oi15,
        pct15,
        funding5,
        funding15,
        cls5,
        cls15,
        _hash(body),
        ordered,
    )
    if not issue:
        return summary
    return _issue(summary, _summary_fingerprint(summary))  # type: ignore[return-value]


def _summary_fingerprint(value: ContextSummary) -> str:
    if type(value) is not ContextSummary:
        raise ContextError("CONTEXT_SUMMARY_INVALID")
    current = _validated_context_observation(value.current)
    five = None if value.baseline_5m is None else _validated_context_observation(value.baseline_5m)
    fifteen = (
        None if value.baseline_15m is None else _validated_context_observation(value.baseline_15m)
    )
    proof = tuple(_validated_context_observation(item) for item in value.selection_proof)
    if (
        not proof
        or tuple(sorted(proof, key=lambda item: (item.received_at, item.receive_sequence))) != proof
    ):
        raise ContextError("CONTEXT_SELECTION_PROOF_INVALID")
    eligible = tuple(item for item in proof if item.received_at <= value.summary_cutoff)
    if not eligible or current is not eligible[-1]:
        raise ContextError("CONTEXT_SELECTION_PROOF_INVALID")
    expected_five = next(
        (
            item
            for item in reversed(eligible)
            if item.received_at <= current.received_at - timedelta(minutes=5)
        ),
        None,
    )
    expected_fifteen = next(
        (
            item
            for item in reversed(eligible)
            if item.received_at <= current.received_at - timedelta(minutes=15)
        ),
        None,
    )
    if five is not expected_five or fifteen is not expected_fifteen:
        raise ContextError("CONTEXT_SELECTION_PROOF_INVALID")

    def derived(
        base: ContextObservation | None,
    ) -> tuple[Decimal | None, Decimal | None, Decimal | None, PriceOiClassification | None]:
        if base is None:
            return None, None, None, None
        oi = current.open_interest - base.open_interest
        pct = None if base.open_interest == 0 else oi / base.open_interest * Decimal("100")
        price = current.reference_price - base.reference_price
        category = None
        if price and oi:
            category = PriceOiClassification(
                "PRICE_" + ("UP" if price > 0 else "DOWN") + "_OI_" + ("UP" if oi > 0 else "DOWN")
            )
        return oi, pct, current.funding - base.funding, category

    oi5, pct5, funding5, classification5 = derived(five)
    oi15, pct15, funding15, classification15 = derived(fifteen)
    body = {
        "current": current.payload(),
        "current_hash": current.canonical_hash,
        "baseline_5m": None if five is None else five.payload(),
        "baseline_5m_hash": None if five is None else five.canonical_hash,
        "baseline_15m": None if fifteen is None else fifteen.payload(),
        "baseline_15m_hash": None if fifteen is None else fifteen.canonical_hash,
        "summary_cutoff": value.summary_cutoff.isoformat(),
        "oi_delta_5m": oi5,
        "oi_pct_delta_5m": pct5,
        "oi_delta_15m": oi15,
        "oi_pct_delta_15m": pct15,
        "funding_delta_5m": funding5,
        "funding_delta_15m": funding15,
        "classification_5m": classification5,
        "classification_15m": classification15,
        "selection_proof": [item.payload() for item in proof],
        "selection_proof_hashes": [item.canonical_hash for item in proof],
    }
    if (
        (value.oi_delta_5m, value.oi_pct_delta_5m, value.funding_delta_5m, value.classification_5m)
        != (oi5, pct5, funding5, classification5)
        or (
            value.oi_delta_15m,
            value.oi_pct_delta_15m,
            value.funding_delta_15m,
            value.classification_15m,
        )
        != (oi15, pct15, funding15, classification15)
        or _hash(body) != value.canonical_hash
    ):
        raise ContextError("CONTEXT_SUMMARY_INVALID")
    return value.canonical_hash


def _validated_context_summary(value: object) -> ContextSummary:
    try:
        if not _issued(value, _summary_fingerprint(value)):  # type: ignore[arg-type]
            raise ContextError("CONTEXT_SUMMARY_AUTHORITY_INVALID")
    except (AttributeError, TypeError, ValueError) as exc:
        raise ContextError("CONTEXT_SUMMARY_AUTHORITY_INVALID") from exc
    return value  # type: ignore[return-value]


class ContextSeries:
    def __init__(self) -> None:
        self._observations: list[ContextObservation] = []

    def accept(self, value: ActiveAssetContext) -> ContextObservation:
        if type(value) is not ActiveAssetContext:
            raise ContextError("CONTEXT_AUTHORITY_INVALID")
        observation = ContextObservation.from_active_context(value)
        identity = (observation.received_at, observation.receive_sequence)
        for existing in self._observations:
            if (existing.received_at, existing.receive_sequence) == identity:
                if existing.canonical_hash != observation.canonical_hash:
                    raise ContextError("CONTEXT_IDENTITY_CONFLICT")
                return existing
        self._observations.append(observation)
        self._observations.sort(key=lambda item: (item.received_at, item.receive_sequence))
        latest = max(item.received_at for item in self._observations)
        cutoff = latest - timedelta(minutes=120)
        if observation.received_at < cutoff:
            self._observations.remove(observation)
            raise ContextError("CONTEXT_RETENTION_WINDOW_EXCEEDED")
        self._observations = [item for item in self._observations if item.received_at >= cutoff]
        return observation

    def summary_at(self, cutoff: datetime) -> ContextSummary | None:
        if cutoff.tzinfo is None:
            raise ContextError("CONTEXT_CUTOFF_INVALID")
        choices = [
            item for item in self._observations if item.received_at <= cutoff.astimezone(UTC)
        ]
        if not choices:
            return None
        current = choices[-1]

        def before(moment: datetime) -> ContextObservation | None:
            selected = [item for item in choices if item.received_at <= moment]
            return selected[-1] if selected else None

        return _build_summary(
            current,
            before(current.received_at - timedelta(minutes=5)),
            before(current.received_at - timedelta(minutes=15)),
            cutoff.astimezone(UTC),
            tuple(choices),
            issue=True,
        )
