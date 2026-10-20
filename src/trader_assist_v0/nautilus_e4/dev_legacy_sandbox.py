# mypy: disable-error-code="import-not-found"
"""Disposable native engineering fixture; never a forward-research profile.

No production entry point imports or registers this strategy. Muse supplies only
fixture provenance: 100 USD notional and three-original structural/3 ATR exits.
Native Sandbox owns all fills, positions, fees and PnL. In particular, a touched
legacy bar price is never recorded here as a fill.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal
from pathlib import Path
from typing import Any

from .native_capture import closed_bar_window, native_event_hash
from .shadow_ledger import ShadowLedger

VERSION = "DEV-MUSE-THREE-ORIGINAL-SANDBOX-v1"
LABEL = "DEV_ONLY_DO_NOT_USE_FOR_RESEARCH"
PROFILE = {
    "classification": LABEL,
    "research_profile": "NOT_A_FORWARD_RESEARCH_PROFILE",
    "notional_usd": "100",
    "eth_fee_per_side": "0.000432",
    "exit": "structural_stop_or_3_ATR_trail_on_causal_quote_no_fixed_TP",
    "entry": "GTC_limit_at_current_ask_round_down_0.001_ETH",
    "fill": "native_L1_Sandbox_liquidity_consumption_no_queue_model",
    "latency": "native_default_zero_NOT_legacy_1000ms_or_measured_latency",
    "funding": "NOT_MODELED",
    "balances": "FAKE_100000_USD_AND_100000_USDC_separate_no_conversion",
    "risk": "native_RiskEngine_enabled_one_long_attempt_100_USD_cap_leverage_1",
    "signal": "SYNTHETIC_FROZEN_TEST_OPPORTUNITY_NOT_Muse_signal_generator",
    "muse_shadow_blob": "39d9c5c2df75b6a373be140fefca330fc77eb829",
    "muse_exit_blob": "b6aa5e04d8bd78f8c7219f83f4c05abe694c15a2",
}


def admission_reasons(
    *, now_ns: int, event_ns: int, init_ns: int, coverage_ok: bool, duplicate: bool
) -> list[str]:
    reasons = []
    if not 0 < event_ns <= init_ns <= now_ns:
        reasons.append("NONCAUSAL_OR_UNKNOWN_CLOCK")
    if now_ns - init_ns > 2_000_000_000:
        reasons.append("STALE")
    if not coverage_ok:
        reasons.append("GAP")
    if duplicate:
        reasons.append("DUPLICATE")
    return reasons


def create_dev_fixture(
    path: Path, *, dev_only: bool = False, passive: bool = False, coverage_ok: bool = True
) -> Any:
    """Explicit opt-in, fresh isolated ledger, no production/research registration."""
    if not dev_only or not path.name.endswith(".dev-only.sqlite") or path.exists():
        raise ValueError("DEV_ONLY requires a NEW isolated *.dev-only.sqlite ledger")
    from nautilus_trader.model import (
        BarType,
        ClientId,
        InstrumentId,
        OrderSide,
        Price,
        Quantity,
        StrategyId,
    )
    from nautilus_trader.trading import Strategy, StrategyConfig

    # Optional native wheel is qualified in Linux CI, absent in the V0 type environment.
    native_base: Any = Strategy

    class LegacyDevFixture(native_base):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__(StrategyConfig(strategy_id=StrategyId(VERSION + "-001")))
            self.ledger = ShadowLedger(path, strategy_id=VERSION, strategy_version=VERSION)
            self.instrument_id = InstrumentId.from_str("ETH-USD-PERP.HYPERLIQUID")
            self.coverage_ok = coverage_ok
            self.seen: set[str] = set()
            self.source: dict[str, Any] | None = None
            self.entry: Any = None
            self.exiting = False
            self.failed = False
            self.high = Decimal("0")
            self.links: dict[str, dict[str, Any]] = {}
            self.observations: Any = None  # Optional test-only asyncio.Queue, never an order queue.

        def notify(self, kind: str, value: Any) -> None:
            if self.observations is not None:
                self.observations.put_nowait((kind, value))

        def on_start(self) -> None:
            self.ledger.append(
                event_id="dev-profile",
                kind="DEV_PROFILE",
                ts_ns=self.clock.timestamp_ns(),
                payload={"version": VERSION, **PROFILE, "passive_entry_negative": passive},
            )
            client = ClientId("DEV-FIXTURE")
            self.subscribe_quotes(self.instrument_id, client_id=client)
            self.subscribe_bars(
                BarType.from_str(str(self.instrument_id) + "-5-MINUTE-LAST-EXTERNAL"),
                client_id=client,
            )

        def reject(self, identity: str, event: Any, reasons: list[str]) -> None:
            now = self.clock.timestamp_ns()
            self.ledger.append(
                event_id=f"reject:{identity}:{','.join(reasons)}",
                kind="DEV_REJECTION",
                ts_ns=now,
                payload={"source": event.to_dict(), "source_hash": identity, "reasons": reasons},
            )
            self.notify("REJECT", reasons)

        def on_bar(self, bar: Any) -> None:
            identity = native_event_hash(bar)
            now = self.clock.timestamp_ns()
            reasons = admission_reasons(
                now_ns=now,
                event_ns=bar.ts_event,
                init_ns=bar.ts_init,
                coverage_ok=self.coverage_ok,
                duplicate=identity in self.seen,
            )
            try:
                closed_bar_window(bar, now_ns=now)
            except ValueError:
                reasons.append("BAR_NOT_CLOSED")
            if bar.bar_type.spec.step != 5 or bar.bar_type.instrument_id != self.instrument_id:
                reasons.append("WRONG_5M_SOURCE")
            if reasons:
                self.reject(identity, bar, reasons)
                return
            self.seen.add(identity)
            if self.source is not None:
                self.reject(identity, bar, ["ONE_DISPOSABLE_ATTEMPT_ONLY"])
                return
            # Frozen synthetic test signal supplied by this fixture, not claimed as
            # an E3 or Muse natural signal. No signal search/tuning occurs here.
            self.source = {
                "source_hash": identity,
                "source": bar.to_dict(),
                "opportunity_id": f"dev-opportunity:{identity}",
                "attempt_id": f"{identity}:1",
                "signal": "SYNTHETIC_THREE_ORIGINAL_LONG",
                "cut_line": "1990.0",
                "atr": "5.0",
            }
            self.ledger.append(
                event_id=identity,
                kind="DEV_SOURCE_SIGNAL",
                ts_ns=now,
                payload=self.source,
            )
            self.notify("SIGNAL", self.source)

        def link_and_submit(self, order: Any, quote: Any, role: str) -> None:
            assert self.source is not None
            link = {
                **self.source,
                "role": role,
                "quote_hash": native_event_hash(quote),
                "quote": quote.to_dict(),
                "client_order_id": str(order.client_order_id),
                "parent_order_id": None if role == "ENTRY" else str(self.entry.client_order_id),
                "order": order.to_dict(),
                "classification": LABEL,
            }
            self.links[str(order.client_order_id)] = link
            self.ledger.decision(
                decision_id=str(order.client_order_id),
                ts_ns=self.clock.timestamp_ns(),
                source_identity=link["source_hash"],
                source_ts_ns=link["source"]["ts_event"],
                outcome="SUBMIT",
                details=link,
            )
            self.submit_order(order)  # Official RiskEngine -> native Sandbox; never bypass.

        def on_quote(self, quote: Any) -> None:
            if self.source is None or self.failed:
                self.notify("QUOTE", quote)
                return
            identity = native_event_hash(quote)
            reasons = admission_reasons(
                now_ns=self.clock.timestamp_ns(),
                event_ns=quote.ts_event,
                init_ns=quote.ts_init,
                coverage_ok=self.coverage_ok,
                duplicate=identity in self.seen,
            )
            if quote.instrument_id != self.instrument_id or quote.bid_price > quote.ask_price:
                reasons.append("INVALID_QUOTE")
            if reasons:
                self.reject(identity, quote, reasons)
                return
            self.seen.add(identity)
            bid, ask = Decimal(str(quote.bid_price)), Decimal(str(quote.ask_price))
            if self.entry is None:
                quantity = (Decimal("100") / ask).quantize(Decimal("0.001"), rounding=ROUND_DOWN)
                if quantity <= 0:
                    self.reject(identity, quote, ["ZERO_SIZE"])
                    return
                order = self.order_factory.limit(
                    self.instrument_id,
                    OrderSide.BUY,
                    Quantity.from_str(str(quantity)),
                    Price.from_str(str(ask - Decimal("100") if passive else ask)),
                    tags=[LABEL, VERSION],
                )
                self.entry = order
                self.link_and_submit(order, quote, "ENTRY")
            elif not self.exiting:
                positions = self.cache.positions_open(instrument_id=self.instrument_id)
                if positions:
                    self.high = max(self.high, bid)
                    if bid <= max(Decimal("1990"), self.high - Decimal("15")):
                        # Native quantity/position state, never inferred from a touched price.
                        self.exiting = True
                        entry_state = self.cache.order(self.entry.client_order_id)
                        if entry_state is None:
                            self.failed = True
                            self.reject(identity, quote, ["UNKNOWN_NATIVE_ORDER_STATE"])
                            return
                        if entry_state.is_open:
                            self.cancel_order(entry_state)
                        order = self.order_factory.market(
                            self.instrument_id,
                            OrderSide.SELL,
                            positions[0].quantity,
                            reduce_only=True,
                            tags=[LABEL, VERSION],
                        )
                        self.link_and_submit(order, quote, "EXIT")
            self.notify("QUOTE", quote)

        def on_order_event(self, event: Any) -> None:
            self.ledger.native_event(event)
            key = str(event.client_order_id)
            self.ledger.append(
                event_id=f"link:{event.event_id}",
                kind="DEV_ORDER_EVENT_LINK",
                ts_ns=event.ts_init,
                payload={
                    "native_event_id": str(event.event_id),
                    "link": self.links.get(key),
                    "unknown_final_state": key not in self.links,
                },
            )
            if key not in self.links or type(event).__name__ in {
                "OrderDenied",
                "OrderRejected",
                "OrderCancelRejected",
                "OrderFillVoided",
            }:
                self.failed = True
            self.notify(type(event).__name__, event)

        def on_order_canceled(self, event: Any) -> None:
            if self.entry is not None and event.client_order_id == self.entry.client_order_id:
                assert self.source is not None
                entry_state = self.cache.order(event.client_order_id)
                if entry_state is None:
                    self.failed = True
                    return
                self.ledger.decision(
                    decision_id=f"cancel:{event.event_id}",
                    ts_ns=event.ts_init,
                    source_identity=self.source["source_hash"],
                    source_ts_ns=self.source["source"]["ts_event"],
                    outcome="UNFILLED" if Decimal(str(entry_state.filled_qty)) == 0 else "PASS",
                    details={
                        "native_cancel_event_id": str(event.event_id),
                        "filled_qty": str(entry_state.filled_qty),
                        "status": "NATIVE_CANCEL_OBSERVED_REMAINDER_NOT_FILLED",
                        "client_order_id": str(event.client_order_id),
                    },
                )

        def on_position_event(self, event: Any) -> None:
            # rc7 position events expose native fields but no to_dict(). Native
            # order events still use ShadowLedger.native_event unchanged.
            self.ledger.append(
                event_id=str(event.event_id),
                kind=type(event).__name__,
                ts_ns=event.ts_init,
                payload={
                    "position_id": str(event.position_id),
                    "opening_order_id": str(event.opening_order_id),
                    "quantity": str(event.quantity),
                    "realized_pnl": str(event.realized_pnl),
                    "ts_event": event.ts_event,
                    "source_hash": self.source["source_hash"] if self.source else None,
                },
            )
            self.notify(type(event).__name__, event)

        def snapshot(self) -> dict[str, Any]:
            from nautilus_trader.model import Venue

            venue = Venue("HYPERLIQUID")
            account = self.cache.account_for_venue(venue)
            if account is None:
                raise RuntimeError("DEV_NATIVE_ACCOUNT_MISSING")
            payload = {
                "classification": LABEL,
                "account": account.to_dict(),
                "positions": [p.to_dict() for p in self.cache.positions()],
                "orders": [o.to_dict() for o in self.cache.orders()],
                "realized_pnl": {
                    str(k): str(v) for k, v in self.portfolio.realized_pnls(venue).items()
                },
                "unrealized_pnl": {
                    str(k): str(v) for k, v in self.portfolio.unrealized_pnls(venue).items()
                },
            }
            now = self.clock.timestamp_ns()
            self.ledger.append(
                event_id=f"state:{now}", kind="DEV_NATIVE_STATE", ts_ns=now, payload=payload
            )
            self.ledger.verify()
            return payload

    return LegacyDevFixture()
