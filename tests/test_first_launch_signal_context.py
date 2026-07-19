from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trader_assist_v0.first_launch.market_data import context_from_websocket, evidence_from_raw
from trader_assist_v0.first_launch.signal_context import ContextSeries, PriceOiClassification


def _observation(seconds: int, price: str, oi: str):
    received = datetime(2026, 7, 14, tzinfo=UTC) + timedelta(seconds=seconds)
    raw = (
        '{"channel":"activeAssetCtx","data":{"coin":"ETH","ctx":'
        f'{{"markPx":"{price}","openInterest":"{oi}","funding":"0"}}}}}}'
    )
    return context_from_websocket(
        raw,
        evidence_from_raw(
            raw,
            operation="WebSocket",
            received_at=received,
            receive_sequence=seconds,
            connection_id="context-test",
        ),
    )


def test_context_summary_is_causal_and_classifies_price_oi() -> None:
    series = ContextSeries()
    series.accept(_observation(0, "100", "10"))
    series.accept(_observation(300, "101", "11"))
    summary = series.summary_at(datetime(2026, 7, 14, tzinfo=UTC) + timedelta(seconds=300))
    assert summary is not None
    assert summary.oi_delta_5m == Decimal("1")
    assert summary.classification_5m is PriceOiClassification.PRICE_UP_OI_UP
