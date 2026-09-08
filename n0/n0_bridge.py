"""A rebuildable, offline-only ClosedBar projection for Nautilus rc4.

This module deliberately owns neither market-data authority nor trading runtime
state.  ``ClosedBar`` remains the canonical evidence; Nautilus carries a small
event envelope which is decoded back to the project's immutable kernel ``Bar``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import TypeVar

from trader_assist_v0.multi_asset_shadow.models import ClosedBar
from trader_assist_v0.multi_asset_shadow.strategy_kernel import Bar

_MS_TO_NS = 1_000_000
_TYPE_NAME = "TradeOsClosedBarProjectionV1"
_TYPE_IDENTIFIER = "TRADE-OS.N0-CLOSEDBAR"
T = TypeVar("T")


class N0BridgeError(ValueError):
    """The replaceable projection is inconsistent with canonical evidence."""


@dataclass(frozen=True)
class N0ClosedBarEvent:
    """The minimal custom-data envelope accepted by Nautilus' public path."""

    closed_bar: ClosedBar
    ts_event: int
    ts_init: int


@dataclass(frozen=True)
class DispatchResult:
    """Observable output of one offline BacktestEngine dispatch."""

    bars: tuple[Bar, ...]
    outputs: tuple[object, ...]
    delivery_times: tuple[tuple[int, int], ...]


def close_boundary_ns(closed_bar: ClosedBar) -> int:
    """Map a finalized millisecond close boundary exactly into Nautilus time."""
    return closed_bar.close_time_ms * _MS_TO_NS


def project_closed_bar(closed_bar: ClosedBar) -> N0ClosedBarEvent:
    """Create a timestamped projection without changing canonical evidence."""
    # Revalidation binds this projection to the current project contract and
    # rejects a model-constructed object that has bypassed its canonical hash.
    ClosedBar.model_validate(closed_bar.model_dump(mode="python"))
    close_ns = close_boundary_ns(closed_bar)
    return N0ClosedBarEvent(closed_bar=closed_bar, ts_event=close_ns, ts_init=close_ns)


def kernel_bar_from_event(event: N0ClosedBarEvent) -> Bar:
    """Losslessly reconstruct the exact project kernel view after delivery."""
    closed_bar = event.closed_bar
    if event.ts_event != close_boundary_ns(closed_bar) or event.ts_init != event.ts_event:
        raise N0BridgeError("ClosedBar projection is not at its causal close boundary")
    ClosedBar.model_validate(closed_bar.model_dump(mode="python"))
    return Bar(
        market_id=closed_bar.market_id,
        interval=closed_bar.interval,
        open_time_ms=closed_bar.open_time_ms,
        close_time_ms=closed_bar.close_time_ms,
        open=Decimal(closed_bar.open),
        high=Decimal(closed_bar.high),
        low=Decimal(closed_bar.low),
        close=Decimal(closed_bar.close),
        volume=Decimal(closed_bar.volume),
        source_identity=closed_bar.canonical_hash,
    )


def kernel_bar_from_custom_data(custom_data: object) -> Bar:
    """Validate an official Nautilus ``CustomData`` callback and decode it."""
    event = getattr(custom_data, "data", None)
    if not isinstance(event, N0ClosedBarEvent):
        raise N0BridgeError("unexpected Nautilus custom-data projection")
    if (
        getattr(custom_data, "ts_event", None) != event.ts_event
        or getattr(custom_data, "ts_init", None) != event.ts_init
    ):
        raise N0BridgeError("Nautilus delivery timestamp changed the projection")
    return kernel_bar_from_event(event)


def dispatch_offline(
    closed_bars: Iterable[ClosedBar], kernel: Callable[[tuple[Bar, ...]], T]
) -> DispatchResult:
    """Use only rc4's public BacktestEngine custom-data dispatch surface.

    ``kernel`` receives all project bars reconstructed so far, from inside
    ``Strategy.on_data``.  It is intentionally supplied by the caller so the
    exact project kernel remains the sole economic authority.
    """
    # Imports are deliberately local: this semantic artifact is never to load
    # Nautilus on an unsupported writer host.
    from nautilus_trader.backtest.engine import BacktestEngine
    from nautilus_trader.config import BacktestEngineConfig, StrategyConfig
    from nautilus_trader.model.data import CustomData, DataType
    from nautilus_trader.trading.strategy import Strategy

    data_type = DataType(
        N0ClosedBarEvent,
        metadata={"projection": "trade-os-closed-bar-v1"},
        identifier=_TYPE_IDENTIFIER,
    )

    class ProjectionStrategy(Strategy):
        def __init__(self) -> None:
            super().__init__(StrategyConfig())
            self.bars: list[Bar] = []
            self.outputs: list[object] = []
            self.delivery_times: list[tuple[int, int]] = []

        def on_start(self) -> None:
            self.subscribe_data(data_type)

        def on_data(self, data: object) -> None:
            bar = kernel_bar_from_custom_data(data)
            self.bars.append(bar)
            self.delivery_times.append((getattr(data, "ts_event"), getattr(data, "ts_init")))
            self.outputs.append(kernel(tuple(self.bars)))

    strategy = ProjectionStrategy()
    engine = BacktestEngine(BacktestEngineConfig(bypass_logging=True, run_analysis=False))
    try:
        engine.add_strategy(strategy)
        engine.add_data(
            [CustomData(data_type, project_closed_bar(bar)) for bar in closed_bars],
            validate=True,
            sort=True,
        )
        engine.run()
        engine.get_result()
        return DispatchResult(
            bars=tuple(strategy.bars),
            outputs=tuple(strategy.outputs),
            delivery_times=tuple(strategy.delivery_times),
        )
    finally:
        engine.dispose()
