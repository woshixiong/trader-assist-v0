"""Deterministic, offline-only examples for the First Launch review surface."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from trader_assist_v0.first_launch.market_data import (
    Candle,
    DataQualityState,
    EthMarketData,
    StrategySnapshot,
    candle_from_websocket,
    context_from_websocket,
    evidence_from_raw,
    metadata_from_info,
)
from trader_assist_v0.first_launch.operator_review import (
    HumanDecision,
    OperatorReviewCard,
    OperatorReviewError,
    append_decision,
    build_operator_card,
    create_shadow_order,
    read_journal,
    render_terminal,
)
from trader_assist_v0.first_launch.strategy import (
    PreparedSetup,
    Side,
    Signal,
    StrategyOutput,
    advance_prepare,
    build_plan,
    evaluate_signal,
)

_NOW = datetime(2026, 7, 14, tzinfo=UTC)


def _candle(
    open_time: int,
    *,
    open: str = "100",
    high: str = "101",
    low: str = "99",
    close: str = "100",
    volume: str = "10",
    interval: str = "5m",
) -> Candle:
    width = 300_000 if interval == "5m" else 900_000
    latest_index = 26 if interval == "5m" else 10
    actual = int(_NOW.timestamp() * 1000) - 1_000 - ((latest_index + 1) * width) + open_time
    values = tuple(map(Decimal, (open, high, low, close)))
    raw = json.dumps(
        {
            "channel": "candle",
            "data": {
                "s": "ETH",
                "i": interval,
                "t": actual,
                "T": actual + width,
                "o": str(values[0]),
                "h": str(max(values[1], values[0], values[3])),
                "l": str(min(values[2], values[0], values[3])),
                "c": str(values[3]),
                "v": volume,
            },
        },
        separators=(",", ":"),
    )
    return candle_from_websocket(
        raw,
        evidence_from_raw(
            raw,
            operation="WebSocket",
            received_at=max(_NOW, datetime.fromtimestamp((actual + width + 1_000) / 1_000, tz=UTC)),
            receive_sequence=max(0, actual // width),
            connection_id="operator-demo",
        ),
    )


def _snapshot(candles_5m: tuple[Candle, ...], candles_15m: tuple[Candle, ...]) -> StrategySnapshot:
    data = EthMarketData()
    data.begin_connection()
    for candle in (*candles_5m, *candles_15m):
        data.accept_candle(candle)
    evaluated_at = max(candle.evidence.received_at for candle in (*candles_5m, *candles_15m))
    context = (
        '{"channel":"activeAssetCtx","data":{"coin":"ETH","ctx":'
        '{"markPx":"100","openInterest":"1","funding":"0"}}}'
    )
    data.accept_context(
        context_from_websocket(
            context,
            evidence_from_raw(
                context,
                operation="WebSocket",
                received_at=evaluated_at,
                receive_sequence=90,
                connection_id="operator-demo",
            ),
        )
    )
    metadata = '{"universe":[{"name":"ETH","szDecimals":3}]}'
    data.accept_metadata(
        metadata_from_info(
            metadata,
            evidence_from_raw(
                metadata,
                operation="metaAndAssetCtxs",
                received_at=evaluated_at,
                receive_sequence=91,
                connection_id="operator-demo",
            ),
        )
    )
    snapshot = data.strategy_snapshot(evaluated_at)
    if snapshot.quality.state is not DataQualityState.READY:
        raise RuntimeError("deterministic demo market-data fixture is not READY")
    return snapshot


def _output(side: Side, fast: bool) -> StrategyOutput:
    candles_5m = [_candle(index * 300_000) for index in range(-9, 26)]
    trigger = _candle(
        26 * 300_000,
        high="101" if side is Side.LONG else "102",
        low="98" if side is Side.LONG else "99",
        close="100",
        volume="20" if fast else "13",
    )
    candles_15m = tuple(
        _candle(
            index * 900_000,
            close=str(100 + index if side is Side.LONG else 100 - index),
            interval="15m",
        )
        for index in range(-9, 11)
    )
    history = tuple([*candles_5m, trigger])
    first = evaluate_signal(_snapshot(history, candles_15m))
    if fast:
        if type(first) is not StrategyOutput:
            raise RuntimeError("fast demo fixture did not produce a StrategyOutput")
        return first
    if type(first) is not PreparedSetup:
        raise RuntimeError("standard demo fixture did not produce a PreparedSetup")
    boundary = first.provenance.boundary
    retest = _candle(
        27 * 300_000,
        open=str(boundary),
        high=str(boundary + Decimal("1")) if side is Side.LONG else str(boundary),
        low=str(boundary) if side is Side.LONG else str(boundary - Decimal("1")),
        close=str(boundary + Decimal("1")) if side is Side.LONG else str(boundary - Decimal("1")),
    )
    result = advance_prepare(first, _snapshot((*history, retest), candles_15m))
    if type(result) is not StrategyOutput:
        raise RuntimeError("standard demo fixture did not confirm")
    return result


def _wait() -> Signal:
    candles_5m = tuple(_candle(index * 300_000) for index in range(-9, 27))
    candles_15m = tuple(_candle(index * 900_000, interval="15m") for index in range(-9, 11))
    result = evaluate_signal(_snapshot(candles_5m, candles_15m))
    if type(result) is not Signal:
        raise RuntimeError("wait demo fixture unexpectedly became actionable")
    return result


def _card(case: str) -> OperatorReviewCard:
    if case == "wait":
        return build_operator_card(_wait(), now=_NOW, quality=DataQualityState.READY)
    side, fast = {
        "long-fast": (Side.LONG, True),
        "short-fast": (Side.SHORT, True),
        "long-standard": (Side.LONG, False),
        "short-standard": (Side.SHORT, False),
    }[case]
    output = _output(side, fast)
    plan = build_plan(
        strategy_output=output,
        reference=output.raw_entry_low,
        equity=Decimal("1000"),
        sz_decimals=3,
    )
    return build_operator_card(plan, now=output.created_at, quality=DataQualityState.READY)


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic offline operator-review demo")
    parser.add_argument(
        "--case",
        choices=("wait", "long-fast", "short-fast", "long-standard", "short-standard"),
        default="wait",
    )
    parser.add_argument("--decision", choices=tuple(item.value for item in HumanDecision))
    parser.add_argument("--reason", default="deterministic offline demo")
    parser.add_argument("--journal", type=Path)
    args = parser.parse_args()
    card = _card(args.case)
    print("DEMO | OFFLINE | NOT SUBMITTED")
    print(render_terminal(card))
    if args.decision is None:
        return 0
    if not card.actionable:
        parser.error("WAIT, WATCH, and PREPARE cards cannot receive a decision")
    if args.journal is None:
        parser.error("--journal is required when --decision is supplied")
    shadow = create_shadow_order(card)
    decision = HumanDecision(args.decision)
    try:
        record = append_decision(
            args.journal,
            card=card,
            shadow_order=shadow,
            decision=decision,
            timestamp=_NOW,
            reason=args.reason,
        )
    except OperatorReviewError as exc:
        parser.error(str(exc))
    records = read_journal(args.journal)
    if len(records) < 1 or records[-1].record_hash != record.record_hash:
        raise RuntimeError("demo journal readback failed")
    print(f"DECISION {decision.value} JOURNAL {record.record_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
