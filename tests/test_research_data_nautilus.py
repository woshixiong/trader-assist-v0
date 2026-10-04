"""Offline composition contracts; installed rc5 proof is authoritative only in CI."""

import importlib
import os
from importlib.metadata import PackageNotFoundError, version
from types import SimpleNamespace

import pytest
from test_research_data_admission import admission, capability
from test_research_data_contracts import dataset
from test_research_data_mapping import mapping, snapshot

from trader_assist_v0.research_data.admission import (
    AdmissionPolicy,
    ExternalReferenceAdmission,
    ExternalReferenceLedger,
)
from trader_assist_v0.research_data.contracts import ControlReplan
from trader_assist_v0.research_data.history import HistoricalRequestSpec, OfficialArchiveRoute
from trader_assist_v0.research_data.mapping import PitReferenceResolver
from trader_assist_v0.research_data.nautilus import (
    RC5_VERSION,
    ExternalReferenceNodeSpec,
    ExternalReferenceObserver,
    NativeSemanticProfile,
    build_external_reference_node,
)
from trader_assist_v0.research_data.storage import ReferenceDatasetStore

KINDS = ("BAR_1M", "BAR_5M", "TRADE", "BBO", "MARK", "INDEX", "FUNDING", "OI")


def matrix(provider="BINANCE", product="SPOT"):
    return tuple(
        capability(
            provider=provider,
            venue=provider,
            product=product,
            datatype=kind,
            source_exposes=kind in KINDS[:4] or product != "SPOT",
            adapter_state="SOURCE_NOT_AVAILABLE"
            if kind in KINDS[4:] and product == "SPOT"
            else "AVAILABLE_VERIFIED",
            enabled=kind in KINDS[:4] or product != "SPOT",
            adapter_owner="OKX_PUBLIC_STDLIB"
            if provider == "OKX" and kind == "OI" and product == "SWAP"
            else "NAUTILUS_RC5",
        )
        for kind in KINDS
    )


def spec(provider="BINANCE", product="SPOT", **changes):
    return ExternalReferenceNodeSpec.create(
        **{
            "version": "synthetic-v1",
            "provider": provider,
            "product": product,
            "instruments": (f"SYNTH.{provider}",),
            "capabilities": matrix(provider, product),
            **changes,
        }
    )


def profile(cap, **changes):
    return NativeSemanticProfile.create(
        **{
            "version": "synthetic-v1",
            "datatype": cap.datatype,
            "capability_hash": cap.record_hash,
            "proof_locator": "synthetic://callback-proof",
            "bar_timestamp_meaning": "CLOSE",
            "bar_finality_proven": True,
            "trade_semantics": "TRADE",
            "unit": "CONTRACTS",
            "period": "SOURCE_DEFINED",
            **changes,
        }
    )


def node_observer(node_spec):
    caps = node_spec.capabilities
    maps = snapshot(
        mapping(
            provider=node_spec.provider,
            venue=node_spec.provider,
            product=node_spec.product,
            instrument_id=node_spec.instruments[0],
            valid_to=10**18,
        )
    )
    ds = dataset(
        source=node_spec.provider,
        venue=node_spec.provider,
        instruments=node_spec.instruments,
        datatypes=KINDS,
        mapping_hash=maps.record_hash,
    )
    policy = AdmissionPolicy.create(
        version="synthetic-v1",
        stale_after_ns=100,
        sequence_semantics="UNKNOWN",
        max_observations=100,
    )
    bound = ExternalReferenceAdmission(
        ds, PitReferenceResolver(maps), caps, policy, production=False
    )
    return ExternalReferenceObserver(
        ExternalReferenceLedger(bound),
        tuple(profile(c) for c in caps if c.enabled and c.adapter_owner == "NAUTILUS_RC5"),
        lambda: 600_000_000_001,
    )


@pytest.mark.parametrize(
    "provider,product",
    [
        ("BINANCE", "SPOT"),
        ("BINANCE", "USD_M"),
        ("BINANCE", "COIN_M"),
        ("OKX", "SPOT"),
        ("OKX", "SWAP"),
    ],
)
def test_complete_matrix_and_explicit_owner(provider, product):
    value = spec(provider, product)
    assert value.credentials is None and not value.depth_enabled
    if provider == "OKX" and product == "SWAP":
        assert value.capabilities[-1].adapter_owner == "OKX_PUBLIC_STDLIB"


def test_matrix_cannot_silently_downgrade_substitute_or_enable_depth():
    with pytest.raises(ValueError):
        spec(capabilities=matrix()[:-1])
    for state in ("ADAPTER_UNSUPPORTED", "CAPABILITY_UNPROVEN", "RUNTIME_UNAVAILABLE"):
        caps = list(matrix())
        caps[0] = capability(product="SPOT", datatype="BAR_1M", adapter_state=state)
        with pytest.raises(ControlReplan):
            spec(capabilities=tuple(caps))
    with pytest.raises(ControlReplan):
        caps = list(matrix())
        caps[0] = capability(product="SPOT", datatype="BAR_1M", source_exposes=None)
        spec(capabilities=tuple(caps))
    with pytest.raises(ValueError):
        spec("OKX", "SWAP", capabilities=matrix("BINANCE", "USD_M"))
    with pytest.raises(ValueError):
        spec(depth_enabled=True)
    with pytest.raises(ValueError):
        spec(credentials="forbidden")
    with pytest.raises(ValueError):
        spec(instruments=("SYNTH.BINANCE", "SYNTH.BINANCE"))


def test_callback_timestamp_missing_receive_and_duplicate_facts():
    bound = admission(datatype="BBO", policy_changes={"sequence_semantics": "UNKNOWN"})
    observer = ExternalReferenceObserver(
        ExternalReferenceLedger(bound), (profile(bound.capabilities[0]),), lambda: 1001
    )
    native = SimpleNamespace(
        instrument_id="SYNTH",
        ts_event=1000,
        ts_init=1001,
        bid_price="10",
        ask_price="11",
        bid_size="2",
        ask_size="3",
    )
    observer.on_native("BBO", native)
    observer.on_native("BBO", native)
    first, duplicate = observer.ledger.observations
    assert first.event.authority == "EXTERNAL_REFERENCE"
    assert first.event.timestamps.ts_event == 1000
    assert first.event.timestamps.ts_init == 1001
    assert first.event.timestamps.true_network_receive_ts is None
    assert duplicate.duplicate


def test_unproven_trade_or_bar_semantics_and_wrong_profile_fail_closed():
    for kind, changes in (
        ("TRADE", {"trade_semantics": "NOT_APPLICABLE"}),
        ("BAR_1M", {"bar_finality_proven": False}),
    ):
        bound = admission(datatype=kind)
        observer = ExternalReferenceObserver(
            ExternalReferenceLedger(bound),
            (profile(bound.capabilities[0], **changes),),
            lambda: 1001,
        )
        native = SimpleNamespace(
            instrument_id="SYNTH", ts_event=1000, bar_type=SimpleNamespace(instrument_id="SYNTH")
        )
        with pytest.raises(ControlReplan):
            observer.on_native(kind, native)
    bound = admission()
    with pytest.raises(ValueError, match="profile"):
        ExternalReferenceObserver(
            ExternalReferenceLedger(bound),
            (profile(bound.capabilities[0], datatype="BBO"),),
            lambda: 1001,
        )


def test_history_is_bounded_and_never_silently_live_or_current_oi():
    cap = capability(source_mode="HISTORY", datatype="BAR_1M")
    args = dict(
        version="synthetic-v1",
        capability=cap,
        instrument_id="SYNTH.BINANCE",
        start_ns=1_000_000_000,
        end_ns=61_000_000_000,
        limit=10,
        bar_timestamp_meaning="CLOSE",
        finality_proven=True,
    )
    assert HistoricalRequestSpec.create(**args).capability.source_mode == "HISTORY"
    for change in ({"limit": 1001}, {"end_ns": 1}, {"capability": capability()}):
        with pytest.raises(ValueError):
            HistoricalRequestSpec.create(**{**args, **change})
    with pytest.raises(ControlReplan):
        HistoricalRequestSpec.create(**{**args, "finality_proven": False})
    with pytest.raises(ValueError):
        HistoricalRequestSpec.create(
            **{
                **args,
                "capability": capability(
                    provider="OKX",
                    source_mode="HISTORY",
                    datatype="OI",
                    adapter_owner="OKX_PUBLIC_STDLIB",
                ),
            }
        )
    with pytest.raises(ValueError):
        OfficialArchiveRoute.create(
            version="1",
            provider="BINANCE",
            source_locator="https://evil.invalid/archive",
            layout_hash="a" * 64,
            semantics_proof_locator="synthetic://proof",
            datatype="TRADE",
            product="SPOT",
        )


@pytest.fixture
def exact_rc5():
    try:
        installed = version("nautilus_trader")
    except PackageNotFoundError:
        if os.environ.get("NAUTILUS_E4_REQUIRED") == "1":
            pytest.fail("authoritative CI requires installed exact rc5")
        pytest.skip("PENDING_GITHUB_CI: no local rc5 runtime; this is not PASS evidence")
    assert installed == RC5_VERSION
    return importlib.import_module("nautilus_trader.model")


@pytest.mark.parametrize(
    "provider,product",
    [
        ("BINANCE", "SPOT"),
        ("BINANCE", "USD_M"),
        ("BINANCE", "COIN_M"),
        ("OKX", "SPOT"),
        ("OKX", "SWAP"),
    ],
)
def test_exact_rc5_data_only_node_build_without_start(exact_rc5, provider, product):
    value = spec(provider, product)
    node = build_external_reference_node(value, node_observer(value))
    try:
        live = importlib.import_module("nautilus_trader.live")
        assert isinstance(node, live.LiveNode)
        assert callable(node.handle().stop)
        strategy = importlib.import_module("nautilus_trader.trading").Strategy
        for name in (
            "subscribe_bars",
            "subscribe_quotes",
            "subscribe_trades",
            "subscribe_mark_prices",
            "subscribe_index_prices",
            "subscribe_funding_rates",
            "request_data",
            "request_bars",
            "request_trades",
            "request_funding_rates",
        ):
            assert callable(getattr(strategy, name))
    finally:
        node.dispose()


@pytest.mark.parametrize("kind", ["BBO", "TRADE", "BAR_1M", "BAR_5M"])
def test_exact_rc5_native_callback_and_catalog_roundtrip(exact_rc5, tmp_path, kind):
    model = exact_rc5
    value = spec()
    observer = node_observer(value)
    instrument = model.InstrumentId.from_str(value.instruments[0])
    price = model.Price.from_str
    size = model.Quantity.from_str
    if kind == "BBO":
        native = model.QuoteTick(
            instrument,
            price("10"),
            price("11"),
            size("2"),
            size("3"),
            600_000_000_000,
            600_000_000_001,
        )
    elif kind == "TRADE":
        native = model.TradeTick(
            instrument,
            price("10"),
            size("2"),
            model.AggressorSide.BUYER,
            model.TradeId("synthetic-one"),
            600_000_000_000,
            600_000_000_001,
        )
    else:
        minutes = 1 if kind == "BAR_1M" else 5
        bar_type = model.BarType.from_str(f"{instrument}-{minutes}-MINUTE-LAST-EXTERNAL")
        native = model.Bar(
            bar_type,
            price("10"),
            price("11"),
            price("9"),
            price("10"),
            size("2"),
            600_000_000_000,
            600_000_000_001,
        )
    observer.on_native(kind, native)
    assert observer.ledger.observations[0].event.authority == "EXTERNAL_REFERENCE"
    catalog = importlib.import_module("nautilus_trader.persistence").ParquetDataCatalog(
        str(tmp_path)
    )
    store = ReferenceDatasetStore(tmp_path, catalog=catalog)
    store.write_native(kind, [native], observer.ledger.admission)
    assert list(tmp_path.rglob("*.parquet"))
