"""Bounded, recomputable Strategy continuation for chronological replay."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal
from hashlib import sha256
from statistics import median

from trader_assist_v0.contracts.common import canonical_json_bytes

from .strategy_kernel import (
    Bar,
    EventLedger,
    HtfContext,
    HtfMomentum,
    HtfStructure,
    ScannerLinkage,
    StrategyEvaluationInput,
)
from .strategy_kernel.indicators import (
    aggregate_closed_5m_causally,
    directional_efficiency_8,
    directional_move_8,
    true_range,
)
from .strategy_kernel.zones import build_zone_book

REPRESENTATION_VERSION = "STRATEGY_CONTINUATION_V2"
_SOURCE_DOMAIN = b"trader-assist-v0/strategy-source-history/v1\0"
_TERMINAL_DOMAIN = b"trader-assist-v0/strategy-terminal-history/v1\0"
EMPTY_SOURCE_COMMITMENT = sha256(_SOURCE_DOMAIN).hexdigest()
EMPTY_TERMINAL_COMMITMENT = sha256(_TERMINAL_DOMAIN).hexdigest()


@dataclass
class RollingAtr:
    """Exact Wilder accumulator; seed and recursion match the frozen kernel."""

    bar_count: int = 0
    previous_close: Decimal | None = None
    seed_sum: Decimal = Decimal()
    value: Decimal | None = None

    def ingest(self, bar: Bar) -> Decimal | None:
        if self.bar_count == 0:
            self.bar_count = 1
            self.previous_close = bar.close
            return None
        if self.previous_close is None:  # pragma: no cover - dataclass invariant
            raise ValueError("ATR continuation lacks previous close")
        current_range = true_range(bar, self.previous_close)
        if self.bar_count < 14:
            self.seed_sum += current_range
        elif self.bar_count == 14:
            self.seed_sum += current_range
            self.value = self.seed_sum / Decimal(14)
        else:
            if self.value is None:  # pragma: no cover - dataclass invariant
                raise ValueError("ATR continuation lacks recursive anchor")
            self.value = (Decimal(13) * self.value + current_range) / Decimal(14)
        self.bar_count += 1
        self.previous_close = bar.close
        return self.value


def _commit(previous: str, domain: bytes, payload: object) -> str:
    if len(previous) != 64:
        raise ValueError("history commitment is invalid")
    return sha256(domain + bytes.fromhex(previous) + canonical_json_bytes(payload)).hexdigest()


@dataclass
class IncrementalStrategyState:
    """Causally necessary bounded state; historical audit stays in EvidenceStore."""

    market_id: str
    bars_5m: list[Bar] = field(default_factory=list)
    bars_15m: list[Bar] = field(default_factory=list)
    atr_15m_values: list[Decimal | None] = field(default_factory=list)
    bars_1h: list[Bar] = field(default_factory=list)
    atr_5m: RollingAtr = field(default_factory=RollingAtr)
    atr_15m: RollingAtr = field(default_factory=RollingAtr)
    atr_1h: RollingAtr = field(default_factory=RollingAtr)
    total_5m: int = 0
    total_15m: int = 0
    total_1h: int = 0
    pivot_highs_1h: list[Decimal] = field(default_factory=list)
    pivot_lows_1h: list[Decimal] = field(default_factory=list)
    ledger: EventLedger = field(default_factory=EventLedger)
    source_history_commitment: str = EMPTY_SOURCE_COMMITMENT
    terminal_history_commitment: str = EMPTY_TERMINAL_COMMITMENT
    last_source_open_time_ms: int | None = None

    def clone(self) -> IncrementalStrategyState:
        return deepcopy(self)

    def ingest(self, bar: Bar) -> None:
        if bar.market_id != self.market_id or bar.interval != "5m":
            raise ValueError("Strategy continuation bar identity is invalid")
        if self.last_source_open_time_ms is not None and (
            bar.open_time_ms != self.last_source_open_time_ms + 300_000
        ):
            raise ValueError("Strategy continuation source history is not chronological")
        self.source_history_commitment = _commit(
            self.source_history_commitment,
            _SOURCE_DOMAIN,
            {
                "market_id": bar.market_id,
                "interval": bar.interval,
                "open_time_ms": bar.open_time_ms,
                "canonical_hash": bar.source_identity,
            },
        )
        self.last_source_open_time_ms = bar.open_time_ms
        self.total_5m += 1
        self.atr_5m.ingest(bar)
        self.bars_5m.append(bar)
        self.bars_5m = self.bars_5m[-21:]

        if self.total_5m >= 3 and (bar.open_time_ms // 300_000 + 1) % 3 == 0:
            derived_15m = aggregate_closed_5m_causally(self.bars_5m[-3:], minutes=15)
            if len(derived_15m) != 1:
                raise ValueError("15m continuation aggregation is incomplete")
            value = derived_15m[0]
            self.total_15m += 1
            atr = self.atr_15m.ingest(value)
            self.bars_15m.append(value)
            self.atr_15m_values.append(atr)
            self.bars_15m = self.bars_15m[-98:]
            self.atr_15m_values = self.atr_15m_values[-98:]

        if self.total_5m >= 12 and (bar.open_time_ms // 300_000 + 1) % 12 == 0:
            derived_1h = aggregate_closed_5m_causally(self.bars_5m[-12:], minutes=60)
            if len(derived_1h) != 1:
                raise ValueError("1h continuation aggregation is incomplete")
            value = derived_1h[0]
            if len(self.bars_1h) >= 2:
                left, pivot = self.bars_1h[-2:]
                if pivot.high > left.high and pivot.high >= value.high:
                    self.pivot_highs_1h.append(pivot.high)
                    self.pivot_highs_1h = self.pivot_highs_1h[-2:]
                if pivot.low < left.low and pivot.low <= value.low:
                    self.pivot_lows_1h.append(pivot.low)
                    self.pivot_lows_1h = self.pivot_lows_1h[-2:]
            self.total_1h += 1
            self.atr_1h.ingest(value)
            self.bars_1h.append(value)
            self.bars_1h = self.bars_1h[-10:]

    def evaluation_input(
        self, *, minimum_tick: Decimal, scanner_linkage: ScannerLinkage | None
    ) -> StrategyEvaluationInput:
        if (
            len(self.bars_5m) < 21
            or len(self.bars_15m) < 15
            or self.atr_5m.value is None
            or self.atr_15m.value is None
        ):
            raise ValueError("Strategy continuation context is insufficient")
        offset = self.total_15m - len(self.bars_15m)
        zone_book = build_zone_book(
            tuple(self.bars_15m),
            minimum_tick=minimum_tick,
            atr_values=tuple(self.atr_15m_values),
            index_offset=offset,
        )
        return StrategyEvaluationInput(
            bars_5m=tuple(self.bars_5m),
            minimum_tick=minimum_tick,
            bars_15m=tuple(self.bars_15m),
            bars_1h=tuple(self.bars_1h),
            zone_book=zone_book,
            scanner_linkage=scanner_linkage,
            mandatory_data_valid=True,
            a5_override=self.atr_5m.value,
            m20_override=median(item.volume for item in self.bars_5m[-21:-1]),
            a15_override=self.atr_15m.value,
            htf_context_override=self._htf_context(),
        )

    def retain_result(self, ledger: EventLedger, terminal_payload: object) -> None:
        terminal = tuple(event for event in ledger.events if event.status.terminal)
        if terminal:
            self.terminal_history_commitment = _commit(
                self.terminal_history_commitment, _TERMINAL_DOMAIN, terminal_payload
            )
        self.ledger = EventLedger(
            tuple(event for event in ledger.events if not event.status.terminal)
        )

    def _htf_context(self) -> HtfContext:
        if self.atr_1h.value is None or self.total_1h < 15 or len(self.bars_1h) < 9:
            return HtfContext(HtfMomentum.UNAVAILABLE, HtfStructure.UNAVAILABLE, None, None)
        bars = tuple(self.bars_1h)
        er8 = directional_efficiency_8(bars)
        d8 = directional_move_8(bars, self.atr_1h.value)
        if er8 >= Decimal("0.35") and d8 >= Decimal("0.75"):
            momentum = HtfMomentum.UP
        elif er8 >= Decimal("0.35") and d8 <= Decimal("-0.75"):
            momentum = HtfMomentum.DOWN
        else:
            momentum = HtfMomentum.NEUTRAL
        if len(self.pivot_highs_1h) < 2 or len(self.pivot_lows_1h) < 2:
            structure = HtfStructure.INSUFFICIENT
        else:
            epsilon = Decimal("0.10") * self.atr_1h.value
            first_high, second_high = self.pivot_highs_1h[-2:]
            first_low, second_low = self.pivot_lows_1h[-2:]
            high_state = (
                "HH"
                if second_high > first_high + epsilon
                else "LH"
                if second_high < first_high - epsilon
                else "EH"
            )
            low_state = (
                "HL"
                if second_low > first_low + epsilon
                else "LL"
                if second_low < first_low - epsilon
                else "EL"
            )
            if high_state == "HH" and low_state == "HL":
                structure = HtfStructure.UP
            elif high_state == "LH" and low_state == "LL":
                structure = HtfStructure.DOWN
            elif high_state in {"LH", "EH"} and low_state in {"HL", "EL"}:
                structure = HtfStructure.RANGE
            else:
                structure = HtfStructure.TRANSITION
        return HtfContext(momentum, structure, er8, d8)
