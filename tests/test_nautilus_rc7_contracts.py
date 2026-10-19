import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from trader_assist_v0.nautilus_e4.contracts import GuardInputs
from trader_assist_v0.nautilus_e4.native_execution import SubmitCertificate, final_submit_reasons
from trader_assist_v0.nautilus_e4.native_health import NativeHealth
from trader_assist_v0.nautilus_e4.shadow_ledger import ShadowLedger


def inputs() -> GuardInputs:
    return GuardInputs(
        data_evaluable=True,
        bbo_state_valid=True,
        intended_notional="10",
        top_level_notional="100",
        remaining_room_bps="100",
        all_in_friction_bps="10",
        minimum_room_to_cost="2",
        spread_bps="1",
        guard_config_version="v1",
    )


def test_health_requires_native_events_fresh_report_writer_catalog_and_disk() -> None:
    health = NativeHealth({"ETH:quote": 100, "ETH:1m": 1000}, minimum_free_bytes=100)
    assert health.report(now=1000, generated=1000, free_bytes=1000)["status"] == "DEGRADED"
    health.socket(True)
    health.writer_ok = health.catalog_verified = True
    for stream in health.required:
        assert health.observe(stream, ts_event=990, ts_init=995, now=1000)
    assert health.report(now=1000, generated=1000, free_bytes=1000)["status"] == "HEALTHY"
    assert health.report(now=1200, generated=1200, free_bytes=1000)["status"] == "DEGRADED"
    assert health.report(now=1000, generated=1000, free_bytes=1)["status"] == "DEGRADED"
    assert (
        health.report(now=20_000_000_000, generated=1000, free_bytes=1000)["status"] == "DEGRADED"
    )
    health.socket(False)
    health.socket(True)  # ACK alone never restores fresh events in a new continuity epoch.
    assert health.report(now=1000, generated=1000, free_bytes=1000)["status"] == "DEGRADED"


def test_unknown_future_out_of_order_events_cannot_make_healthy() -> None:
    health = NativeHealth({"ETH:quote": 100}, max_future_skew_ns=1)
    assert not health.observe("OTHER:quote", ts_event=10, ts_init=10, now=10)
    assert not health.observe("ETH:quote", ts_event=20, ts_init=20, now=10)
    assert health.observe("ETH:quote", ts_event=10, ts_init=10, now=10)
    assert not health.observe("ETH:quote", ts_event=9, ts_init=11, now=11)
    assert health.out_of_order == 1
    assert "OUT_OF_ORDER_OR_GAP" in health.failures


def test_closed_bar_freshness_uses_close_without_changing_source_open_time() -> None:
    second = 1_000_000_000
    health = NativeHealth({"ETH:5m": 360 * second})
    health.socket(True)
    health.writer_ok = health.catalog_verified = True
    assert health.observe(
        "ETH:5m",
        ts_event=300 * second,
        event_end_ns=600 * second,
        ts_init=600 * second,
        now=900 * second,
    )
    assert health.last["ETH:5m"][0] == 300 * second
    assert (
        health.report(now=900 * second, generated=900 * second, free_bytes=10**12)["status"]
        == "HEALTHY"
    )
    assert (
        health.report(now=1000 * second, generated=1000 * second, free_bytes=10**12)["status"]
        == "DEGRADED"
    )
    assert not health.observe(
        "ETH:5m",
        ts_event=600 * second,
        event_end_ns=900 * second,
        ts_init=899 * second,
        now=900 * second,
    )


@pytest.mark.parametrize(
    "change",
    [
        {"instrument_id": "OTHER"},
        {"epoch": 2},
        {"valid_until_ns": 99},
        {"signal_valid_until_ns": 99},
        {"generated_ns": 101},
        {"account_reconciled": False},
        {"price_known": False},
        {"native_connected": False},
        {"feed_health": "GAPPED"},
        {"feed_health": "UNKNOWN"},
        {"feed_health": "STALE"},
    ],
)
def test_final_submit_rechecks_each_safety_failure(change: dict[str, object]) -> None:
    good = SubmitCertificate("ETH", 1, 200, 200, True, True, True, "HEALTHY", 90)
    assert not final_submit_reasons(
        certificate=good, instrument_id="ETH", epoch=1, now_ns=100, inputs=inputs()
    )
    assert final_submit_reasons(
        certificate=replace(good, **change),
        instrument_id="ETH",
        epoch=1,
        now_ns=100,
        inputs=inputs(),
    )


def test_unknown_certificate_and_existing_economic_guard_fail_closed() -> None:
    assert final_submit_reasons(
        certificate=None, instrument_id="ETH", epoch=1, now_ns=100, inputs=inputs()
    )
    bad = inputs().model_copy(update={"data_evaluable": False})
    good = SubmitCertificate("ETH", 1, 200, 200, True, True, True, "HEALTHY", 90)
    assert "DATA_NOT_EVALUABLE" in final_submit_reasons(
        certificate=good, instrument_id="ETH", epoch=1, now_ns=100, inputs=bad
    )


def test_decisions_no_fill_reject_and_partial_fill_survive_restart(tmp_path: Path) -> None:
    path = tmp_path / "ledger.sqlite"
    ledger = ShadowLedger(path, strategy_id="approved-strategy", strategy_version="v1")
    for i, outcome in enumerate(("REJECT", "WAIT", "PASS", "UNFILLED", "LOST", "SUBMIT")):
        ledger.decision(
            decision_id=str(i),
            ts_ns=100,
            source_identity=f"quote:{i}",
            source_ts_ns=90,
            outcome=outcome,
            details={},
        )
    for i, qty in enumerate(("0.1", "0.2")):
        ledger.append(
            event_id=f"fill:{i}",
            kind="OrderFilled",
            ts_ns=110 + i,
            payload={
                "native_order_id": "order-1",
                "last_qty": qty,
                "commission": "0.01 USDC",
                "liquidity_side": "TAKER",
            },
        )
    assert ledger.verify() == 8
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        ledger.db.execute("DELETE FROM events")
    ledger.close()
    reopened = ShadowLedger(path, strategy_id="approved-strategy", strategy_version="v1")
    assert reopened.verify() == 8
    assert reopened.db.execute("SELECT count(*) FROM events WHERE kind='DECISION'").fetchone() == (
        6,
    )
    with pytest.raises(ValueError, match="conflicting"):
        reopened.append(event_id="fill:0", kind="OrderFilled", ts_ns=120, payload={})
    reopened.close()


def test_approved_strategy_retains_cold_start_no_signal_denominator(tmp_path: Path) -> None:
    from decimal import Decimal

    from test_nautilus_pilot_contracts import _closed_bar, _manifest

    from trader_assist_v0.nautilus_e4.registered_shadow import RegisteredShadowEvaluator

    manifest = _manifest()
    ledger = ShadowLedger(
        tmp_path / "strategy.sqlite",
        strategy_id=manifest.package_version,
        strategy_version=manifest.strategy_version,
    )
    evaluator = RegisteredShadowEvaluator(
        manifest=manifest,
        market_id=_closed_bar(0).market_id,
        minimum_tick=Decimal("0.1"),
        ledger=ledger,
    )
    for i in range(3):
        bar = _closed_bar(i)
        assert evaluator.evaluate(bar, now_ns=bar.close_time_ms * 1_000_000) is None
    assert ledger.verify() == 3
    evaluator.evaluate(_closed_bar(2), now_ns=_closed_bar(2).close_time_ms * 1_000_000)
    assert ledger.verify() == 3  # replay does not inflate the strategy decision denominator
    with pytest.raises(ValueError, match="lookahead"):
        evaluator.evaluate(_closed_bar(3), now_ns=1)
    ledger.close()


def test_native_universe_uses_provider_identity_without_inventing_symbols() -> None:
    from types import SimpleNamespace

    from trader_assist_v0.nautilus_e4.native_capture import NativeUniverse

    universe = NativeUniverse(("ETH", "xyz:SKHX"), None)
    with pytest.raises(ValueError, match="MISSING"):
        universe.current_snapshot(now_ns=1)

    class Identity:
        venue = "HYPERLIQUID"

        def __init__(self, symbol: str) -> None:
            self.symbol = symbol

        def __str__(self) -> str:
            return self.symbol + ".HYPERLIQUID"

    for coin, symbol in (("ETH", "provider-eth"), ("xyz:SKHX", "provider-rwa")):
        native = SimpleNamespace(
            raw_symbol=coin, id=Identity(symbol), to_dict=lambda value=coin: {"coin": value}
        )
        expression = universe.admit(native)
        assert expression is not None
        assert expression.instrument_id == str(native.id)
    snapshot = universe.current_snapshot(now_ns=1)
    pinned = NativeUniverse(("ETH", "xyz:SKHX"), snapshot)
    with pytest.raises(ValueError, match="identity mismatch"):
        pinned.admit(SimpleNamespace(raw_symbol="ETH", id=native.id))
    assert not universe.missing
    with pytest.raises(ValueError, match="approved registry"):
        NativeUniverse(("ETH", "fake:NEW"), None)


@pytest.mark.parametrize("minutes", [1, 5])
def test_native_closed_bar_admission_has_no_partial_or_future_bar(minutes: int) -> None:
    from types import SimpleNamespace

    from trader_assist_v0.nautilus_e4.native_capture import closed_bar_window

    duration = minutes * 60_000_000_000
    event = SimpleNamespace(
        bar_type=SimpleNamespace(spec=SimpleNamespace(step=minutes)),
        ts_event=duration,
        ts_init=2 * duration,
    )
    assert closed_bar_window(event, now_ns=2 * duration) == (
        duration // 1_000_000,
        2 * duration // 1_000_000 - 1,
    )
    event.ts_init -= 1
    with pytest.raises(ValueError, match="NOT_CLOSED"):
        closed_bar_window(event, now_ns=2 * duration)
    event.ts_init = 2 * duration + 1
    with pytest.raises(ValueError, match="FUTURE"):
        closed_bar_window(event, now_ns=2 * duration)
