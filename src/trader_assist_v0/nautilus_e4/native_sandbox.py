# mypy: disable-error-code="import-not-found"
"""Official ExecTester protocol probe, exclusively on the native Sandbox node.

This is an isolated integration fixture, not an approved trading strategy or
strategy-to-order mapping. No Hyperliquid execution client is constructed.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any

from .shadow_ledger import ShadowLedger


def attach_sandbox_probe(node: Any) -> None:
    from nautilus_trader.model import InstrumentId, Quantity, StrategyId, TimeInForce
    from nautilus_trader.testkit import ExecTesterConfig

    node.add_builtin_strategy(
        "ExecTester",
        ExecTesterConfig(
            strategy_id=StrategyId("RC7-SANDBOX-PROBE-001"),
            instrument_id=InstrumentId.from_str("ETH-USD-PERP.HYPERLIQUID"),
            order_qty=Quantity.from_str("0.010"),
            open_position_on_start_qty=Decimal("0.010"),
            open_position_on_first_quote=True,
            open_position_time_in_force=TimeInForce.IOC,
            subscribe_quotes=True,
            enable_limit_buys=True,
            enable_limit_sells=True,
            modify_orders_to_maintain_tob_offset=True,
            trigger_limit_order_maintenance_once=True,
            cancel_orders_on_stop=True,
            close_positions_on_stop=True,
            reduce_only_on_stop=True,
            log_data=False,
        ),
    )


def record_sandbox_state(node: Any, ledger: ShadowLedger, *, now_ns: int) -> dict[str, Any]:
    """Record native facts idempotently; account/fees/PnL never locally modeled."""
    from nautilus_trader.model import Venue

    kinds: Counter[str] = Counter()
    orders = node.cache.orders()
    for order in orders:
        events = order.events()
        for event in events:
            ledger.native_event(event)
            kinds[type(event).__name__] += 1
        if events:
            origin = events[0]
            ledger.decision(
                decision_id=f"native-probe:{order.client_order_id}",
                ts_ns=origin.ts_init,
                source_identity=f"OrderInitialized:{origin.event_id}",
                source_ts_ns=origin.ts_init,
                outcome="SUBMIT",
                details={"origin": "OFFICIAL_EXEC_TESTER_PROTOCOL_ONLY"},
            )
    venue = Venue("HYPERLIQUID")
    account = node.cache.account_for_venue(venue)
    if account is None:
        raise RuntimeError("NATIVE_SANDBOX_ACCOUNT_MISSING")
    snapshot = {
        "account": account.to_dict(),
        "orders": [order.to_dict() for order in orders],
        "positions": [position.to_dict() for position in node.cache.positions()],
        "realized_pnl": {str(k): str(v) for k, v in node.portfolio.realized_pnls(venue).items()},
        "unrealized_pnl": {
            str(k): str(v) for k, v in node.portfolio.unrealized_pnls(venue).items()
        },
        "equity": {str(k): str(v) for k, v in node.portfolio.equity(venue).items()},
    }
    ledger.append(
        event_id=f"native-state:{now_ns}", kind="NATIVE_STATE", ts_ns=now_ns, payload=snapshot
    )
    ledger.verify()
    return {
        "status": "OBSERVED" if kinds["OrderFilled"] else "NO_NATIVE_FILL_OBSERVED",
        "native_event_counts": dict(kinds),
        "snapshot": snapshot,
        "strategy_order_mapping": "NOT_QUALIFIED_PROTOCOL_FIXTURE_ONLY",
        "partial_fill_stop_tp_rejection_restart": "NOT_INFERRED_FROM_OTHER_EVENTS",
    }
