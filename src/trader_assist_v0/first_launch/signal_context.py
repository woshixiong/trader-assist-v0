"""Pure, bounded context evidence; this module owns no transport or scheduler."""

from __future__ import annotations

import hashlib
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
        return cls(
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


@dataclass(frozen=True)
class ContextSummary:
    current: ContextObservation
    oi_delta_5m: Decimal | None
    oi_pct_delta_5m: Decimal | None
    oi_delta_15m: Decimal | None
    oi_pct_delta_15m: Decimal | None
    funding_delta_5m: Decimal | None
    funding_delta_15m: Decimal | None
    classification_5m: PriceOiClassification | None
    classification_15m: PriceOiClassification | None
    canonical_hash: str

    @classmethod
    def create(
        cls,
        current: ContextObservation,
        five: ContextObservation | None,
        fifteen: ContextObservation | None,
    ) -> ContextSummary:
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
                    "PRICE_"
                    + ("UP" if price > 0 else "DOWN")
                    + "_OI_"
                    + ("UP" if oi > 0 else "DOWN")
                )
            return oi, pct, current.funding - base.funding, category

        oi5, pct5, funding5, cls5 = values(five)
        oi15, pct15, funding15, cls15 = values(fifteen)
        body = {
            "current": current.payload(),
            "oi_delta_5m": oi5,
            "oi_pct_delta_5m": pct5,
            "oi_delta_15m": oi15,
            "oi_pct_delta_15m": pct15,
            "funding_delta_5m": funding5,
            "funding_delta_15m": funding15,
            "classification_5m": cls5,
            "classification_15m": cls15,
        }
        return cls(current, oi5, pct5, oi15, pct15, funding5, funding15, cls5, cls15, _hash(body))


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
        cutoff = observation.received_at - timedelta(minutes=120)
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

        return ContextSummary.create(
            current,
            before(current.received_at - timedelta(minutes=5)),
            before(current.received_at - timedelta(minutes=15)),
        )
