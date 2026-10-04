"""Backward/PIT/clock joins cannot acquire future or external E4 authority."""

from decimal import Decimal

from test_research_replay_contracts import changed, raw, spec

from trader_assist_v0.research_replay.alignment import (
    backward,
    cross_venue,
    eligible,
    lead_lag,
    propagation,
)


def test_future_and_late_join_cannot_change_committed_prefix():
    old = raw(90, provider="BINANCE")
    newer = raw(101, provider="BINANCE")
    late = raw(95, provider="BINANCE", known=110)
    s = spec(family="CROSS_VENUE")
    args = dict(provider="BINANCE", kind="BBO", expression="SYNTH")
    assert backward((old,), s, 100, 100, **args) == backward(
        (old, newer, late), s, 100, 100, **args
    )
    assert backward((old, newer, late), s, 110, 110, **args)[0] == newer


def test_gap_skew_stale_conflict_and_pit_edges():
    s = spec(stale_ns=10)
    row = raw(100)
    assert eligible(row, s, 111, 111) == "STALE"
    assert (
        eligible(changed(row, ts_receive=99, receive_provenance="PROVIDER_EXPOSED"), s, 100, 100)
        == "CLOCK_SKEW"
    )
    assert (
        eligible(changed(row, evidence=changed(row.evidence, valid_to=100)), s, 100, 100)
        == "MAPPING_UNAVAILABLE"
    )
    assert (
        eligible(changed(row, evidence=changed(row.evidence, mapping_known_at=101)), s, 100, 100)
        == "MAPPING_UNAVAILABLE"
    )
    args = dict(provider="NAUTILUS_HYPERLIQUID", kind="BBO", expression="SYNTH")
    gap = raw(99, known=101, quality=("GAPPED",))
    assert backward((row, gap), s, 101, 101, **args)[1] == "GAPPED"
    conflict = changed(row, ordinal=101, values=(("ask", "102"), ("bid", "99")))
    assert backward((row, conflict), s, 100, 100, **args)[1] == "AMBIGUOUS"
    assert eligible(row, changed(s, clock="RECEIVE"), 100, 100) == "MISSING_SOURCE"
    bar = raw(90, kind="BAR", values={"high": "105", "low": "95"})
    assert eligible(changed(bar, bar_end=110), s, 100, 100) == "MISSING_SOURCE"


def test_breadth_units_disagreement_no_external_repair():
    s = spec(family="CROSS_VENUE", parameters=(("confirmation_bps", "10"),))
    hl, bn, okx = (
        raw(),
        raw(provider="BINANCE"),
        raw(provider="OKX", values={"bid": "101", "ask": "103", "bid_size": "1", "ask_size": "1"}),
    )
    feature = cross_venue((hl, bn, okx), s, 100, 100, "SYNTH")
    v = dict(feature.values)
    assert Decimal(v["eligible"]) == 2 and Decimal(v["agreeing"]) == 1
    assert Decimal(v["disagreement_bps"]) == -200
    assert cross_venue((bn, okx), s, 100, 100, "SYNTH").status == "MISSING_SOURCE"
    mismatch = changed(okx, evidence=changed(okx.evidence, price_unit="USDT"))
    assert (
        Decimal(dict(cross_venue((hl, bn, mismatch), s, 100, 100, "SYNTH").values)["missing"]) == 1
    )


def test_historical_retrospective_clock_claim_never_becomes_receive_or_live():
    row = raw(100, known=1000)
    row = changed(row, evidence=changed(row.evidence, source_mode="HISTORY"))
    original = spec(skew_ns=10)
    assert eligible(row, original, 100, 1000) == "CLOCK_SKEW"
    retrospective = changed(original, availability_claim="RETROSPECTIVE_EVENT_TIME")
    assert eligible(row, retrospective, 100, 1000) == "AVAILABLE"
    assert eligible(row, changed(retrospective, clock="RECEIVE"), 100, 1000) == "MISSING_SOURCE"
    assert row.evidence.source_mode == "HISTORY"


def test_lead_lag_and_forward_propagation_are_separate_matured_labels():
    s = spec(family="CROSS_VENUE", window_ns=50, parameters=(("response_bps", "10"),))
    previous = raw(80, provider="BINANCE")
    impulse = raw(100, provider="BINANCE", values={"bid": "101", "ask": "103"})
    before = raw(90)
    response = raw(110, values={"bid": "100", "ask": "102"})
    rows = (previous, impulse, before, response, raw(80))
    assert (
        propagation(
            impulse, previous, rows, s, follower="NAUTILUS_HYPERLIQUID", horizon_ns=20, as_of=110
        ).state
        == "CENSORED"
    )
    label = propagation(
        impulse, previous, rows, s, follower="NAUTILUS_HYPERLIQUID", horizon_ns=20, as_of=120
    )
    assert label.state == "RESPONSE" and label.elapsed_ns == 10
    feature = lead_lag(rows, s, 100, 100, "SYNTH", "BINANCE", "NAUTILUS_HYPERLIQUID", 20, 0)
    assert response.record_hash not in feature.input_hashes
