"""Small reusable Hypothesis domains for cross-layer contract closure."""

from __future__ import annotations

from decimal import Decimal

from hypothesis import strategies as st
from hypothesis.strategies import DrawFn

from trader_assist_v0.multi_asset_shadow.strategy_kernel import Bar

MARKET_ID = "9" * 64
FIVE_MINUTES_MS = 300_000
PRICE_SCALE = Decimal("100000000")


@st.composite
def valid_strategy_bars(
    draw: DrawFn,
    *,
    interval: str = "5m",
    open_time_ms: int = 0,
) -> Bar:
    """Generate admitted finite OHLC, including zero range and zero volume."""
    width = {"5m": FIVE_MINUTES_MS, "15m": 900_000, "1h": 3_600_000}[interval]
    low_units = draw(st.integers(min_value=1, max_value=10**16))
    span_units = draw(st.one_of(st.just(0), st.integers(min_value=1, max_value=10**8)))
    high_units = low_units + span_units
    open_units = draw(st.integers(min_value=low_units, max_value=high_units))
    close_units = draw(st.integers(min_value=low_units, max_value=high_units))
    volume_units = draw(st.one_of(st.just(0), st.integers(min_value=1, max_value=10**12)))
    return Bar(
        market_id=MARKET_ID,
        interval=interval,
        open_time_ms=open_time_ms,
        close_time_ms=open_time_ms + width,
        open=Decimal(open_units) / PRICE_SCALE,
        high=Decimal(high_units) / PRICE_SCALE,
        low=Decimal(low_units) / PRICE_SCALE,
        close=Decimal(close_units) / PRICE_SCALE,
        volume=Decimal(volume_units) / PRICE_SCALE,
        source_identity="HYPOTHESIS_ADMITTED_BAR",
    )


@st.composite
def causal_five_minute_series(draw: DrawFn) -> tuple[Bar, ...]:
    """Continuous valid prefixes beginning at an arbitrary UTC 5m phase."""
    phase = draw(st.integers(min_value=0, max_value=11))
    count = draw(st.integers(min_value=1, max_value=48))
    start = phase * FIVE_MINUTES_MS
    base_units = draw(st.integers(min_value=1, max_value=10**12))
    values: list[Bar] = []
    for index in range(count):
        movement = draw(st.integers(min_value=-1000, max_value=1000))
        center = max(1, base_units + movement)
        span = draw(st.integers(min_value=0, max_value=1000))
        low = Decimal(center) / PRICE_SCALE
        high = Decimal(center + span) / PRICE_SCALE
        values.append(
            Bar(
                MARKET_ID,
                "5m",
                start + index * FIVE_MINUTES_MS,
                start + (index + 1) * FIVE_MINUTES_MS,
                low,
                high,
                low,
                high,
                Decimal(),
                "HYPOTHESIS_CAUSAL_PREFIX",
            )
        )
    return tuple(values)
