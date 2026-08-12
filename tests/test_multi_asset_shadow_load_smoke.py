"""Fixed-40 deterministic smoke evidence; no timing thresholds or network."""

from __future__ import annotations

from trader_assist_v0.multi_asset_shadow.load_smoke import run_fixed_40_load_smoke


def test_fixed_manual_40_load_smoke_covers_bounded_public_data_route(tmp_path) -> None:  # type: ignore[no-untyped-def]
    report = run_fixed_40_load_smoke(tmp_path)

    assert report.fixed_market_count == 40
    assert report.five_m_events_processed == 480
    assert report.max_pending_finality_generations == 40
    assert report.max_active_confirmations == 4
    assert report.bars_persisted == 680
    assert report.fifteen_m_aggregates == 160
    assert report.one_h_aggregates == 40
    assert report.failed_market_count == 1
    assert report.healthy_markets_progress == 39
    assert report.reconnect_result == "CLEARED"
    assert report.shutdown_pending_state == "CLEARED"
    assert not report.full_universe_continuous_1m
    assert not report.continuous_l2
    assert not report.account_private_or_write_surface


def test_fixed_manual_40_load_smoke_emits_stable_required_evidence(tmp_path) -> None:  # type: ignore[no-untyped-def]
    evidence = run_fixed_40_load_smoke(tmp_path).evidence_lines()

    assert evidence[0] == "FIXED_MARKET_COUNT=40"
    assert "RECONNECT_RESULT=CLEARED" in evidence
    assert "SHUTDOWN_PENDING_STATE=CLEARED" in evidence
