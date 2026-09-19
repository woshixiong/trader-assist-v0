from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    MarketIdentity,
    RegistryMarket,
    RegistryTier,
)
from trader_assist_v0.nautilus_e4.contracts import (
    AdmittedEvent,
    DataKind,
    EvidenceState,
    LifecycleKind,
    LifecycleRecord,
    LifecycleStatus,
    MarketExpression,
    SourceEvent,
)
from trader_assist_v0.nautilus_g4.catalog_bridge import (
    _canonical_native_aggressor_side,
    admit_hypothetical_order_intent,
    bind_rebuildable_cache,
    build_replay_payload,
    derive_economics_can_improve,
    derive_retest_seen,
    derive_thesis_valid,
    project_native_replay,
)
from trader_assist_v0.vnext_g4.contracts import (
    AttemptStop,
    CandidateConfig,
    CandidateManifest,
    CausalLineage,
    DerivationStatus,
    EvidenceArtifactHash,
    ExecutionModelConfig,
    ExitPolicy,
    G4RunManifest,
    OrderPrimitive,
    PositionSide,
    ReentryPolicy,
    RestartReferenceEvidence,
    RestartReferenceKind,
    ValidationReference,
    WinnerConfirmation,
)

MARKET = MarketIdentity.canonical_market_id(dex="MAIN", coin="ETH")
NATIVE_INSTRUMENT = "ETH-USD-PERP.HYPERLIQUID"
STRUCTURAL = "b" * 64
METADATA = "f" * 64
NAUTILUS_AVAILABLE = importlib.util.find_spec("nautilus_trader") is not None


def admitted(ordinal: int) -> AdmittedEvent:
    source = SourceEvent.create(
        market_id=MARKET,
        expression_id="expr-ETH",
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id="ETH-PERP.HYPERLIQUID",
        data_kind=DataKind.BAR,
        source_event_id=f"bar-{ordinal}",
        native_trade_id=None,
        provider_aggressor_side=None,
        event_context="FINALIZED_5M",
        ts_event=ordinal,
        ts_init=ordinal + 1,
        true_network_receive_ts=None,
        payload={"close": str(100 + ordinal)},
    )
    return AdmittedEvent.create(
        schema_version="E4_CAPTURE_V1",
        process_epoch="process-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
        admission_ordinal=ordinal,
        admission_ts=ordinal + 2,
        source_identity=source.replay_identity,
        out_of_order=False,
        continuity_state=EvidenceState.COMPLETE,
        source=source,
    )


def replay_admitted(
    ordinal: int,
    data_kind: DataKind,
    *,
    market_id: str = MARKET,
    expression_id: str = "expr-ETH",
    instrument_id: str = NATIVE_INSTRUMENT,
    payload: dict[str, object] | None = None,
    event_context: str = "accepted-context",
    native_trade_id: str | None = None,
    aggressor_side: str | None = None,
    out_of_order: bool = False,
    continuity_state: EvidenceState = EvidenceState.COMPLETE,
) -> AdmittedEvent:
    defaults: dict[DataKind, dict[str, object]] = {
        DataKind.BBO: {
            "bid_price": "1999.00",
            "ask_price": "2001.00",
            "bid_size": "2.00",
            "ask_size": "3.00",
        },
        DataKind.TRADE: {"price": "2000.00", "size": "1.00"},
        DataKind.BAR: {
            "open": "1998.00",
            "high": "2002.00",
            "low": "1997.00",
            "close": "2000.00",
            "volume": "12.00",
            "finalized": True,
        },
        DataKind.CONTEXT: {"mark_price": "2000.00"},
    }
    if data_kind is DataKind.TRADE:
        native_trade_id = native_trade_id or f"native-trade-{ordinal}"
        aggressor_side = aggressor_side or "BUY"
    source = SourceEvent.create(
        market_id=market_id,
        expression_id=expression_id,
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id=instrument_id,
        data_kind=data_kind,
        source_event_id=f"{data_kind.value.lower()}-{ordinal}",
        native_trade_id=native_trade_id,
        provider_aggressor_side=aggressor_side,
        event_context=event_context,
        ts_event=ordinal * 10,
        ts_init=ordinal * 10 + 1,
        true_network_receive_ts=None,
        payload=defaults[data_kind] if payload is None else payload,
    )
    return AdmittedEvent.create(
        schema_version="E4_CAPTURE_V1",
        process_epoch="process-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
        admission_ordinal=ordinal,
        admission_ts=ordinal * 10 + 2,
        source_identity=source.replay_identity,
        out_of_order=out_of_order,
        continuity_state=continuity_state,
        source=source,
    )


def validation() -> ValidationReference:
    return ValidationReference.create(
        validation_reference_id="validation-v1",
        source_artifact_hash="1" * 64,
        fee_profile_id="fee-v1",
        fee_profile_source_hash="2" * 64,
        fee_effective_at_ns=1,
        fee_bps=Decimal("1"),
        all_in_friction_state_id="friction-v1",
        all_in_friction_source_hash="3" * 64,
        all_in_friction_bps=Decimal("2"),
        execution_model_id="execution-v1",
        execution_model_source_hash="4" * 64,
        technical_quantity_rule_id="quantity-v1",
        technical_quantity_rule_source_hash="5" * 64,
        latency_control_id="latency-v1",
        latency_control_source_hash="6" * 64,
        latency_ms=Decimal("0"),
        latency_evidence_role="CONTROL_ONLY",
    )


def lineage() -> CausalLineage:
    accepted = validation()
    return CausalLineage.create(
        source_e4_manifest_hash="7" * 64,
        source_pit_snapshot_hash="8" * 64,
        source_structural_artifact_hash="9" * 64,
        structural_component_manifest_hash=STRUCTURAL,
        market_id=MARKET,
        instrument_id="ETH-PERP.HYPERLIQUID",
        formal_setup_id="setup-1",
        formal_setup_admission_ordinal=1,
        formal_setup_admission_ts=1,
        thesis_id="thesis-1",
        activation_sequence_id="activation-1",
        attempt_lineage_id="attempt-1",
        restart_reference_id="restart-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
        instrument_metadata_version="meta-v1",
        instrument_metadata_hash=METADATA,
        validation_reference_id=accepted.validation_reference_id,
        validation_reference_hash=accepted.reference_hash,
    )


def lifecycle(
    ordinal: int,
    *,
    kind: LifecycleKind = LifecycleKind.THESIS,
    status: LifecycleStatus = LifecycleStatus.ACTIVE,
    reason: str,
    evidence_state: EvidenceState = EvidenceState.COMPLETE,
) -> LifecycleRecord:
    return LifecycleRecord.create(
        schema_version="E4_CAPTURE_V1",
        run_id="run-1",
        object_id="thesis-1" if kind is LifecycleKind.THESIS else f"attempt-{ordinal}",
        parent_id=None if kind is LifecycleKind.THESIS else "thesis-1",
        package_id="package-1",
        market_id=MARKET,
        expression_id="expr-ETH",
        kind=kind,
        status=status,
        state_ts=ordinal * 10,
        reason_codes=(reason,),
        decision_state=None,
        approval_timing_mode=None,
        approval_provenance="NOT_APPLICABLE",
        expiry_ts=None,
        supersedes_id=None,
        last_admission_ordinal=ordinal,
        evidence_state=evidence_state,
    )


def bbo(
    ordinal: int,
    *,
    ask: str,
    state: EvidenceState = EvidenceState.COMPLETE,
) -> AdmittedEvent:
    ask_value = Decimal(ask)
    source = SourceEvent.create(
        market_id=MARKET,
        expression_id="expr-ETH",
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id="ETH-PERP.HYPERLIQUID",
        data_kind=DataKind.BBO,
        source_event_id=f"bbo-{ordinal}",
        native_trade_id=None,
        provider_aggressor_side=None,
        event_context=f"block-{ordinal}",
        ts_event=ordinal * 10,
        ts_init=ordinal * 10 + 1,
        true_network_receive_ts=None,
        payload={
            "bid_price": str(ask_value - Decimal("0.01")),
            "ask_price": str(ask_value),
            "bid_size": "2.00",
            "ask_size": "2.00",
        },
    )
    return AdmittedEvent.create(
        schema_version="E4_CAPTURE_V1",
        process_epoch="process-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
        admission_ordinal=ordinal,
        admission_ts=ordinal * 10 + 2,
        source_identity=source.replay_identity,
        out_of_order=False,
        continuity_state=state,
        source=source,
    )


def reference(
    *,
    reference_id: str = "restart-1",
    price: str = "100",
    confirmed: int = 1,
    side: PositionSide = PositionSide.LONG,
) -> RestartReferenceEvidence:
    return RestartReferenceEvidence.create(
        lineage_hash=lineage().lineage_hash,
        restart_reference_id=reference_id,
        side=side,
        kind=(
            RestartReferenceKind.PIVOT_HIGH
            if side is PositionSide.LONG
            else RestartReferenceKind.PIVOT_LOW
        ),
        price=Decimal(price),
        reset_admission_ordinal=confirmed,
        confirmed_admission_ordinal=confirmed,
        confirmed_admission_ts=confirmed * 10,
        source_artifact_hash="a" * 64,
    )


def market_sources() -> tuple[MarketExpression, RegistryMarket]:
    expression = MarketExpression(
        market_id=MARKET,
        dex="MAIN",
        provider_coin="ETH",
        instrument_id="ETH-PERP.HYPERLIQUID",
        expression_id="expr-ETH",
        listing_state="ACTIVE",
        instrument_metadata_version="meta-v1",
        instrument_metadata_hash=METADATA,
        fee_state_version="fee-v1",
        fee_state_hash="e" * 64,
    )
    market = RegistryMarket(
        display="ETH",
        tier=RegistryTier.P0,
        identity=MarketIdentity.create(dex="MAIN", coin="ETH"),
        asset_class=AssetClass.CRYPTO,
        size_decimals=2,
        price_max_significant_figures=5,
        price_max_decimals=2,
        is_hip3=False,
        market_status="ACTIVE",
        metadata_observed_at=datetime(2026, 9, 17, tzinfo=UTC),
        metadata_hash=METADATA,
    )
    return expression, market


def manifest() -> G4RunManifest:
    config = CandidateConfig(
        entry_activation="EA1",
        attempt_stop=AttemptStop.AP0,
        room_to_cost_k=Decimal("2"),
        reentry_policy=ReentryPolicy.NO_REENTRY_REFERENCE,
        winner_confirmation=WinnerConfirmation.WC0,
        winner_progress_bps=Decimal("3"),
        exit_policy=ExitPolicy.X1,
        comparison_role="REFERENCE",
    )
    candidate = CandidateManifest.create(
        candidate_id="reference",
        structural_component_manifest_hash=STRUCTURAL,
        config=config,
    )
    execution = ExecutionModelConfig(
        book_type="L1_MBP",
        order_primitive=OrderPrimitive.MARKETABLE,
        prob_fill_on_limit=Decimal("0"),
        prob_slippage=Decimal("0"),
        trade_execution=True,
        queue_position=False,
        liquidity_consumption=True,
        fill_limit_at_price=False,
        fill_stop_at_price=False,
        random_seed=7,
        execution_model_limited=True,
    )
    return G4RunManifest.create(
        run_id="run-1",
        git_sha="1" * 40,
        git_tree="2" * 40,
        source_e4_manifest_hash="c" * 64,
        source_pit_snapshot_hash="d" * 64,
        source_evidence_artifact_hashes=(
            EvidenceArtifactHash(name="admissions", sha256="e" * 64),
        ),
        structural_component_manifest_hash=STRUCTURAL,
        execution_model=execution,
        candidates=(candidate,),
        trial_adaptivity_id="trial-v1",
        cutoff_id="cutoff-v1",
    )


def test_replay_payload_is_deterministic_and_source_bound() -> None:
    events = (admitted(1), admitted(2))
    payload = build_replay_payload(events)
    assert payload == build_replay_payload(events)
    identity = bind_rebuildable_cache(manifest=manifest(), payload=payload)
    assert identity.derived_payload_hash == sha256_hex(payload)
    assert identity.source_g4_manifest_hash == manifest().manifest_hash


def test_replay_bridge_rejects_noncausal_or_duplicate_order() -> None:
    with pytest.raises(ValueError, match="causal admission order"):
        build_replay_payload((admitted(2), admitted(1)))
    with pytest.raises(ValueError, match="duplicate admission ordinals"):
        build_replay_payload((admitted(1), admitted(1)))


@pytest.mark.skipif(not NAUTILUS_AVAILABLE, reason="optional Nautilus rc5 is absent")
def test_native_replay_projection_is_lossless_deterministic_and_source_bound() -> None:
    from nautilus_trader.model import (
        AggregationSource,
        Bar,
        BarAggregation,
        BarSpecification,
        BarType,
        InstrumentId,
        PriceType,
        QuoteTick,
        TradeTick,
    )

    bar_type = str(
        BarType(
            InstrumentId.from_str(NATIVE_INSTRUMENT),
            BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST),
            AggregationSource.EXTERNAL,
        )
    )
    events = (
        replay_admitted(1, DataKind.BBO),
        replay_admitted(2, DataKind.TRADE, aggressor_side="BUY"),
        replay_admitted(3, DataKind.BAR, event_context=bar_type),
    )
    projection = project_native_replay(
        events=events,
        market_id=MARKET,
        expression_id="expr-ETH",
        instrument_id=NATIVE_INSTRUMENT,
    )
    repeated = project_native_replay(
        events=events,
        market_id=MARKET,
        expression_id="expr-ETH",
        instrument_id=NATIVE_INSTRUMENT,
    )

    assert projection.identity == repeated.identity
    assert projection.identity.ordered_source_admission_hashes == tuple(
        event.admission_hash for event in events
    )
    assert projection.identity.event_count == 3
    assert projection.identity.quote_tick_count == 1
    assert projection.identity.trade_tick_count == 1
    assert projection.identity.bar_count == 1
    assert len(set(projection.identity.ordered_native_event_hashes)) == 3

    quote, trade, bar = projection.events
    assert isinstance(quote, QuoteTick)
    assert str(quote.instrument_id) == NATIVE_INSTRUMENT
    assert (str(quote.bid_price), str(quote.ask_price)) == ("1999.00", "2001.00")
    assert (str(quote.bid_size), str(quote.ask_size)) == ("2.00", "3.00")
    assert (quote.ts_event, quote.ts_init) == (10, 11)

    assert isinstance(trade, TradeTick)
    assert str(trade.instrument_id) == NATIVE_INSTRUMENT
    assert (str(trade.price), str(trade.size)) == ("2000.00", "1.00")
    assert str(trade.trade_id) == "native-trade-2"
    assert str(trade.aggressor_side) == "BUY"
    assert (trade.ts_event, trade.ts_init) == (20, 21)

    assert isinstance(bar, Bar)
    assert str(bar.bar_type) == bar_type
    assert (str(bar.open), str(bar.high), str(bar.low), str(bar.close)) == (
        "1998.00",
        "2002.00",
        "1997.00",
        "2000.00",
    )
    assert str(bar.volume) == "12.00"
    assert (bar.ts_event, bar.ts_init) == (30, 31)


@pytest.mark.parametrize(
    ("source_side", "canonical_side"),
    (("BUY", "BUY"), ("BUYER", "BUY"), ("SELL", "SELL"), ("SELLER", "SELL")),
)
def test_aggressor_side_source_labels_have_unambiguous_canonical_meaning(
    source_side: str,
    canonical_side: str,
) -> None:
    assert _canonical_native_aggressor_side(source_side) == canonical_side


@pytest.mark.skipif(not NAUTILUS_AVAILABLE, reason="optional Nautilus rc5 is absent")
def test_aggressor_aliases_bind_canonical_native_content_and_source_provenance() -> None:
    from nautilus_trader.model import TradeTick

    projections = {
        source_side: project_native_replay(
            events=(
                replay_admitted(1, DataKind.TRADE, aggressor_side=source_side),
            ),
            market_id=MARKET,
            expression_id="expr-ETH",
            instrument_id=NATIVE_INSTRUMENT,
        )
        for source_side in ("BUY", "BUYER", "SELL", "SELLER")
    }

    for source_side, canonical_side in (
        ("BUY", "BUY"),
        ("BUYER", "BUY"),
        ("SELL", "SELL"),
        ("SELLER", "SELL"),
    ):
        trade = projections[source_side].events[0]
        assert isinstance(trade, TradeTick)
        assert str(trade.aggressor_side) == canonical_side
        repeated = project_native_replay(
            events=(
                replay_admitted(1, DataKind.TRADE, aggressor_side=source_side),
            ),
            market_id=MARKET,
            expression_id="expr-ETH",
            instrument_id=NATIVE_INSTRUMENT,
        )
        assert repeated.identity == projections[source_side].identity

    for canonical, legacy in (("BUY", "BUYER"), ("SELL", "SELLER")):
        assert (
            projections[canonical].identity.ordered_native_event_hashes
            == projections[legacy].identity.ordered_native_event_hashes
        )
        assert (
            projections[canonical].identity.ordered_source_admission_hashes
            != projections[legacy].identity.ordered_source_admission_hashes
        )
        assert (
            projections[canonical].identity.projection_hash
            != projections[legacy].identity.projection_hash
        )


@pytest.mark.parametrize(
    "source_side",
    (None, "", "UNKNOWN", "BUY/SELL", "NO_AGGRESSOR", "buy"),
)
def test_aggressor_side_unknown_missing_or_ambiguous_fails_closed(
    source_side: str | None,
) -> None:
    with pytest.raises(ValueError, match="unknown or ambiguous"):
        _canonical_native_aggressor_side(source_side)


def test_native_replay_projection_rejects_unaccepted_or_mixed_sources() -> None:
    project = {
        "market_id": MARKET,
        "expression_id": "expr-ETH",
        "instrument_id": NATIVE_INSTRUMENT,
    }
    with pytest.raises(ValueError, match="at least one"):
        project_native_replay(events=(), **project)
    with pytest.raises(ValueError, match="causal admission order"):
        project_native_replay(
            events=(
                replay_admitted(2, DataKind.BBO),
                replay_admitted(1, DataKind.BBO),
            ),
            **project,
        )
    with pytest.raises(ValueError, match="duplicate admission ordinals"):
        project_native_replay(
            events=(
                replay_admitted(1, DataKind.BBO),
                replay_admitted(1, DataKind.TRADE),
            ),
            **project,
        )
    with pytest.raises(ValueError, match="out_of_order"):
        project_native_replay(
            events=(replay_admitted(1, DataKind.BBO, out_of_order=True),),
            **project,
        )
    with pytest.raises(ValueError, match="COMPLETE continuity"):
        project_native_replay(
            events=(
                replay_admitted(
                    1,
                    DataKind.BBO,
                    continuity_state=EvidenceState.GAPPED,
                ),
            ),
            **project,
        )
    with pytest.raises(ValueError, match="mixed or unselected"):
        project_native_replay(
            events=(
                replay_admitted(1, DataKind.BBO),
                replay_admitted(2, DataKind.TRADE, expression_id="expr-other"),
            ),
            **project,
        )
    with pytest.raises(ValueError, match="unsupported native replay data kind"):
        project_native_replay(
            events=(replay_admitted(1, DataKind.CONTEXT),),
            **project,
        )


def test_native_replay_projection_rejects_malformed_or_synthetic_content() -> None:
    project = {
        "market_id": MARKET,
        "expression_id": "expr-ETH",
        "instrument_id": NATIVE_INSTRUMENT,
    }
    with pytest.raises(ValueError, match="ask_size"):
        project_native_replay(
            events=(
                replay_admitted(
                    1,
                    DataKind.BBO,
                    payload={
                        "bid_price": "1999.00",
                        "ask_price": "2001.00",
                        "bid_size": "2.00",
                    },
                ),
            ),
            **project,
        )
    with pytest.raises(ValueError, match="unknown or ambiguous"):
        project_native_replay(
            events=(
                replay_admitted(1, DataKind.TRADE, aggressor_side="UNKNOWN"),
            ),
            **project,
        )
    with pytest.raises(ValueError, match="finalized=true"):
        project_native_replay(
            events=(
                replay_admitted(
                    1,
                    DataKind.BAR,
                    payload={
                        "open": "1998.00",
                        "high": "2002.00",
                        "low": "1997.00",
                        "close": "2000.00",
                        "volume": "12.00",
                        "finalized": False,
                    },
                ),
            ),
            **project,
        )
    with pytest.raises(ValueError, match="BAR high"):
        project_native_replay(
            events=(
                replay_admitted(
                    1,
                    DataKind.BAR,
                    payload={
                        "open": "1998.00",
                        "high": "1999.00",
                        "low": "1997.00",
                        "close": "2000.00",
                        "volume": "12.00",
                        "finalized": True,
                    },
                ),
            ),
            **project,
        )


def test_s1_attempt_failure_does_not_invalidate_thesis_and_stale_freezes_history() -> None:
    records = (
        lifecycle(1, reason="THESIS_CREATED"),
        lifecycle(2, reason="ACTIVE_VALID"),
        lifecycle(3, kind=LifecycleKind.ATTEMPT, reason="ATTEMPT_FAILURE"),
    )
    derived = derive_thesis_valid(
        formal_setup_confirmed=True,
        lineage=lineage(),
        records=records,
    )
    assert derived.status is DerivationStatus.EVALUABLE
    assert derived.value is True

    stale = derive_thesis_valid(
        formal_setup_confirmed=True,
        lineage=lineage(),
        records=(*records, lifecycle(4, reason="ACTIVE_VALID", evidence_state=EvidenceState.STALE)),
    )
    assert stale.status is DerivationStatus.NOT_EVALUABLE
    assert stale.value is None
    assert stale.last_causally_defensible_value is True

    invalidated = derive_thesis_valid(
        formal_setup_confirmed=True,
        lineage=lineage(),
        records=(
            *records,
            lifecycle(
                4,
                status=LifecycleStatus.TERMINAL,
                reason="STRUCTURAL_THESIS_INVALIDATION",
            ),
        ),
    )
    assert invalidated.status is DerivationStatus.EVALUABLE
    assert invalidated.value is False


def test_s2_exact_break_return_reaccel_and_no_reuse_after_failure() -> None:
    events = (
        bbo(1, ask="99.00"),
        bbo(2, ask="101.00"),
        bbo(3, ask="100.00"),
        bbo(4, ask="101.00"),
    )
    complete = derive_retest_seen(
        lineage=lineage(),
        side=PositionSide.LONG,
        events=events,
        references=(reference(),),
    )
    assert complete.status is DerivationStatus.EVALUABLE
    assert complete.retest_seen is True
    assert complete.restart_reference_crossed is True
    assert (complete.break_ordinal, complete.return_ordinal, complete.reaccel_ordinal) == (
        2,
        3,
        4,
    )

    no_reuse = derive_retest_seen(
        lineage=lineage(),
        side=PositionSide.LONG,
        events=(*events, bbo(5, ask="101.50")),
        references=(reference(),),
        attempt_failed_admission_ordinal=5,
    )
    assert no_reuse.retest_seen is False
    assert no_reuse.restart_reference_crossed is False


def test_s2_new_reference_resets_incomplete_sequence_and_gap_is_not_evaluable() -> None:
    reset = derive_retest_seen(
        lineage=lineage(),
        side=PositionSide.LONG,
        events=(
            bbo(1, ask="99.00"),
            bbo(2, ask="101.00"),
            bbo(3, ask="100.00"),
            bbo(4, ask="101.00"),
        ),
        references=(
            reference(reference_id="restart-old", confirmed=1),
            reference(reference_id="restart-1", price="102", confirmed=4),
        ),
    )
    assert reset.status is DerivationStatus.EVALUABLE
    assert reset.retest_seen is False
    assert reset.restart_reference_crossed is False

    for source_state in (
        EvidenceState.GAPPED,
        EvidenceState.STALE,
        EvidenceState.CONFLICTED,
    ):
        unavailable = derive_retest_seen(
            lineage=lineage(),
            side=PositionSide.LONG,
            events=(bbo(1, ask="99.00"), bbo(2, ask="101.00", state=source_state)),
            references=(reference(),),
        )
        assert unavailable.status is DerivationStatus.NOT_EVALUABLE
        assert unavailable.retest_seen is None
    missing = derive_retest_seen(
        lineage=lineage(),
        side=PositionSide.LONG,
        events=(),
        references=(reference(),),
    )
    assert missing.status is DerivationStatus.NOT_EVALUABLE


def test_s2_short_uses_causal_best_bid_with_mirrored_side_sign() -> None:
    complete = derive_retest_seen(
        lineage=lineage(),
        side=PositionSide.SHORT,
        events=(
            bbo(1, ask="101.01"),
            bbo(2, ask="99.01"),
            bbo(3, ask="100.01"),
            bbo(4, ask="99.01"),
        ),
        references=(reference(side=PositionSide.SHORT),),
    )
    assert complete.status is DerivationStatus.EVALUABLE
    assert complete.current_executable_price == Decimal("99.00")
    assert complete.retest_seen is True
    assert complete.restart_reference_crossed is True


def test_s3_empty_a_now_is_false_and_distinct_from_missing_validation() -> None:
    expression, market = market_sources()
    empty = derive_economics_can_improve(
        lineage=lineage(),
        side=PositionSide.LONG,
        ideal_entry_low=Decimal("100.001"),
        ideal_entry_high=Decimal("100.009"),
        target_reference=Decimal("110"),
        room_to_cost_k=Decimal("2"),
        current_bbo=bbo(10, ask="100.01"),
        market_expression=expression,
        registry_market=market,
        validation=validation(),
    )
    assert empty.status is DerivationStatus.EVALUABLE
    assert empty.a_now_empty is True
    assert empty.economics_can_improve is False
    assert empty.best_admissible_price is None
    assert empty.best_room_to_cost is None
    assert empty.current_executable_price == Decimal("100.01")

    missing = derive_economics_can_improve(
        lineage=lineage(),
        side=PositionSide.LONG,
        ideal_entry_low=Decimal("100"),
        ideal_entry_high=Decimal("101"),
        target_reference=Decimal("110"),
        room_to_cost_k=Decimal("2"),
        current_bbo=bbo(10, ask="100.01"),
        market_expression=expression,
        registry_market=market,
        validation=None,
    )
    assert missing.status is DerivationStatus.NOT_EVALUABLE
    assert missing.economics_can_improve is None


def test_s3_existential_uses_venue_valid_geometry_without_snapping_current_price() -> None:
    expression, market = market_sources()
    derived = derive_economics_can_improve(
        lineage=lineage(),
        side=PositionSide.LONG,
        ideal_entry_low=Decimal("100"),
        ideal_entry_high=Decimal("101"),
        target_reference=Decimal("110"),
        room_to_cost_k=Decimal("2"),
        current_bbo=bbo(10, ask="100.01"),
        market_expression=expression,
        registry_market=market,
        validation=validation(),
    )
    assert derived.status is DerivationStatus.EVALUABLE
    assert derived.a_now_empty is False
    assert derived.economics_can_improve is True
    assert derived.best_admissible_price == Decimal("100")
    assert derived.current_executable_price == Decimal("100.01")
    assert derived.current_remaining_room_bps is not None
    assert derived.best_room_to_cost is not None


def test_execution_binding_is_typed_not_evaluable_or_canonical_zero_write() -> None:
    too_large = admit_hypothetical_order_intent(
        strategy_decision_id="decision-1",
        candidate_hash="c" * 64,
        side=PositionSide.LONG,
        lineage=lineage(),
        current_bbo=bbo(10, ask="100.01"),
        technical_quantity=Decimal("2.01"),
        size_decimals=2,
        activation_reference_hash="d" * 64,
        validation=validation(),
    )
    assert too_large.status is DerivationStatus.NOT_EVALUABLE
    assert too_large.intent is None

    admitted_intent = admit_hypothetical_order_intent(
        strategy_decision_id="decision-1",
        candidate_hash="c" * 64,
        side=PositionSide.LONG,
        lineage=lineage(),
        current_bbo=bbo(10, ask="100.01"),
        technical_quantity=Decimal("1.20"),
        size_decimals=2,
        activation_reference_hash="d" * 64,
        validation=validation(),
    )
    assert admitted_intent.status is DerivationStatus.EVALUABLE
    assert admitted_intent.intent is not None
    assert admitted_intent.intent.not_submitted is True
    assert admitted_intent.intent.venue_submitted is False
