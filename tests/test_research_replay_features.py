"""Hand-computed formulas, missing states and accepted raw-reader composition."""

from decimal import Decimal

import pytest
from test_research_data_admission import admission, event
from test_research_replay_contracts import H, changed, raw, spec

from trader_assist_v0.research_data.admission import ExternalReferenceLedger
from trader_assist_v0.research_data.storage import ReferenceDatasetStore, ReferenceReplayReader
from trader_assist_v0.research_replay.evidence import read_external
from trader_assist_v0.research_replay.microstructure import (
    bbo_features,
    depth_features,
    trade_features,
)
from trader_assist_v0.research_replay.profiles import AuctionConfig, auction_step, volume_profile


def test_bbo_ofi_microprice_oracle_and_depth_independence():
    first = raw(100, values={"bid": "99", "ask": "101", "bid_size": "2", "ask_size": "2"})
    second = raw(110, values={"bid": "100", "ask": "101", "bid_size": "3", "ask_size": "1"})
    expected = bbo_features((first, second), spec(), 110, 110)
    values = {k: Decimal(v) for k, v in expected.values}
    assert values["ofi"] == 4 and values["imbalance"] == Decimal("0.5")
    assert values["microprice"] == Decimal("100.75")
    depth = raw(
        110, kind="DEPTH", values={"native_depth": '{"bids":[["100","2"]],"asks":[["101","2"]]}'}
    )
    assert bbo_features((first, second, depth), spec(), 110, 110) == expected
    ds = spec(kind="DEPTH", family="DEPTH10_OR_L2", parameters=(("top_n", "1"),))
    assert depth_features(depth, ds, 110, 110, Decimal(1)).status == "AVAILABLE"
    assert depth_features(depth, ds, 110, 110, Decimal(3)).status == "DEPTH_UNAVAILABLE"
    assert depth_features(None, ds, 110, 110, Decimal(1)).values == ()
    delta = changed(depth, values=(("native_depth", '{"semantics":"DELTA"}'),))
    assert depth_features(delta, ds, 110, 110, Decimal(1)).status == "DEPTH_UNAVAILABLE"


def test_missing_is_not_measured_zero():
    rows = (
        raw(100),
        raw(110, values={"bid": "99", "ask": "101", "bid_size": "0", "ask_size": "0"}),
    )
    assert bbo_features(rows, spec(), 110, 110).status == "MISSING_SOURCE"
    trade = raw(110, kind="TRADE", values={"price": "100", "size": "1", "aggressor": "UNKNOWN"})
    assert trade_features((trade,), spec("TRADE"), 110, 110).values == ()
    signed = changed(trade, values=(("aggressor", "BUY"), ("price", "100"), ("size", "1")))
    assert (
        Decimal(dict(trade_features((signed,), spec("TRADE"), 110, 110).values)["signed_flow"]) == 1
    )
    assert bbo_features(rows, spec(warmup_ns=200), 110, 110).status == "WARMUP_INCOMPLETE"
    assert (
        bbo_features((rows[0], changed(rows[1], continuity_epoch="new")), spec(), 110, 110).status
        == "GAPPED"
    )


def test_profile_value_area_nodes_concentration_migration():
    s = spec(
        "TRADE",
        parameters=tuple(
            sorted(
                dict(
                    bin_width="1", origin="0", value_fraction="0.7", price_tick="1", node_radius="1"
                ).items()
            )
        ),
    )
    rows = tuple(
        raw(100 + i, kind="TRADE", values={"price": str(99 + i), "size": str(q)})
        for i, q in enumerate((2, 6, 2))
    )
    feature = volume_profile(rows, s, 110, 110)
    values = {k: Decimal(v) for k, v in feature.values}
    assert (values["poc"], values["val"], values["vah"]) == (100, 99, 101)
    assert values["concentration"] == Decimal("0.44") and values["hvn_0"] == 100
    assert Decimal(dict(volume_profile(rows, s, 111, 111, feature).values)["value_migration"]) == 0
    hole = (rows[0], changed(rows[2], values=(("price", "103"), ("size", "6"))))
    more_area = changed(
        s, parameters=tuple((k, "0.9" if k == "value_fraction" else v) for k, v in s.parameters)
    )
    assert volume_profile(hole, more_area, 110, 110).status == "GAPPED"


def test_failed_auction_confirmation_does_not_backdate_or_create_setup():
    config = AuctionConfig.create(
        version="B_AUCTION_CONFIG_V1",
        balance_low=Decimal(99),
        balance_high=Decimal(101),
        frozen_at=100,
        boundary_source_hash=H,
        max_response_bps=Decimal(10),
        acceptance_dwell_ns=20,
        require_second_attempt=False,
    )
    state = auction_step(
        config, None, ts=101, price=Decimal(102), opposing_flow=False, response_bps=Decimal(5)
    )
    assert state.state == "EDGE_TEST" and state.confirmed_at is None
    failed = auction_step(
        config, state, ts=110, price=Decimal(100), opposing_flow=True, response_bps=Decimal(5)
    )
    assert failed.state == "FAILED_AUCTION" and failed.confirmed_at == 110
    with pytest.raises(ValueError, match="order"):
        auction_step(
            config, state, ts=101, price=Decimal(100), opposing_flow=True, response_bps=Decimal(5)
        )


def test_accepted_raw_reader_rebuild_and_sealed_refusal_before_io(tmp_path, monkeypatch):
    bound = admission()
    ledger = ExternalReferenceLedger(bound)
    ledger.observe(event(bound), evaluated_at_ns=1001)
    store = ReferenceDatasetStore(tmp_path)
    path, checksum = store.write(ledger)
    reader = ReferenceReplayReader(store, bound)
    first = read_external(reader, path, checksum, H)
    assert read_external(reader, path, checksum, H) == first
    assert first[0].evidence.source_hash == ledger.observations[0].event.record_hash
    bound.dataset = changed(bound.dataset, exposure_state="VALIDATION_SEALED")
    monkeypatch.setattr(type(path), "open", lambda *a, **k: pytest.fail("sealed I/O"))
    with pytest.raises(PermissionError):
        read_external(reader, path, checksum, H)
