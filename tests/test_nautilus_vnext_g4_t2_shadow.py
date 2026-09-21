from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_g4.runner import provider_state_semantic_source_hash
from trader_assist_v0.nautilus_g4.t2_shadow import (
    AcceptedRealT2Receipt,
    CanonicalAcceptanceExpectation,
    RoleBoundSourceArtifact,
    RootedT2Rederivation,
    SourceReference,
    T2ArtifactCandidate,
    T2SourceRole,
    T2SourceRootSnapshot,
    assess_local_acceptance_evidence,
    fresh_process_rederive,
    rederive_rooted_t2,
    verify_mechanical_t2,
)

H = "1" * 64
G = "2" * 64
PROJECT_GIT_OID = "53d4c359d7d59d7b5293f279b3922e53125e8120"
MARKET = sha256_hex(b"HYPERLIQUID|MAIN|ETH")
INSTRUMENT = "ETH-USD-PERP.HYPERLIQUID"
NAUTILUS_AVAILABLE = importlib.util.find_spec("nautilus_trader") is not None
REQUIRES_NAUTILUS = pytest.mark.skipif(
    not NAUTILUS_AVAILABLE, reason="substantive rooted-T2 fixtures require pinned Nautilus rc5"
)


def artifact(
    role: T2SourceRole,
    name: str,
    raw: bytes | None = None,
    *,
    references: tuple[SourceReference, ...] = (),
) -> RoleBoundSourceArtifact:
    return RoleBoundSourceArtifact.create(
        role=role,
        name=name,
        exact_bytes=raw or name.encode(),
        references=references,
    )


def minimal_root(*, head: str = PROJECT_GIT_OID, tree: str = "a" * 40) -> T2SourceRootSnapshot:
    items = tuple(
        artifact(role, name)
        for role, name in (
            (T2SourceRole.E4_RUN_MANIFEST, "e4-run"),
            (T2SourceRole.E4_PIT_SNAPSHOT, "e4-pit"),
            (T2SourceRole.G4_RUN_MANIFEST, "g4-run"),
            (T2SourceRole.SELECTED_CANDIDATE, "candidate"),
            (T2SourceRole.VALIDATION_REFERENCE, "validation"),
        )
    )
    by_role = {item.role: item for item in items}
    return T2SourceRootSnapshot.create(
        task_id="PILOT_TASK3_R3_ROOTED_T2_V3_REPLACEMENT",
        governance_epoch=G,
        acquisition_plan_hash=H,
        exact_source_git_head=head,
        exact_source_git_tree=tree,
        e4_run_manifest_hash=by_role[T2SourceRole.E4_RUN_MANIFEST].artifact_hash,
        e4_pit_snapshot_hash=by_role[T2SourceRole.E4_PIT_SNAPSHOT].artifact_hash,
        g4_run_manifest_hash=by_role[T2SourceRole.G4_RUN_MANIFEST].artifact_hash,
        selected_candidate_hash=by_role[T2SourceRole.SELECTED_CANDIDATE].artifact_hash,
        strategy_package_identity="strategy-v1",
        validation_reference_hash=by_role[T2SourceRole.VALIDATION_REFERENCE].artifact_hash,
        artifacts=items,
    )


def mechanical_result(root: T2SourceRootSnapshot, *, salt: str = "genuine") -> RootedT2Rederivation:
    digest = sha256_hex(salt.encode())
    return RootedT2Rederivation(
        source_root_hash=root.source_root_hash,
        thesis_id="thesis-1",
        market_id=MARKET,
        decision="TAKE",
        evaluation_inputs_hash=digest,
        participation_result_hash=G,
        order_intent_hash=H,
        replay_projection_hash=G,
        provider_execution_semantic_hash=H,
        provider_state_source_hash=H,
        provider_instrument_wire_hash=G,
        thesis_outcome_hash=H,
        cost_source_hashes=(G,),
    )


def test_t01_git_oid_domain_accepts_40_and_64_but_content_digests_do_not() -> None:
    assert minimal_root().exact_source_git_head == PROJECT_GIT_OID
    assert minimal_root(head="b" * 64, tree="c" * 64).exact_source_git_tree == "c" * 64
    values = minimal_root().model_dump(mode="python", exclude={"source_root_hash"})
    values["governance_epoch"] = "d" * 40
    with pytest.raises(ValidationError, match="governance_epoch"):
        T2SourceRootSnapshot.create(**values)
    values = minimal_root().model_dump(mode="python", exclude={"source_root_hash"})
    values["exact_source_git_head"] = "d" * 32
    with pytest.raises(ValidationError, match="exact_source_git_head"):
        T2SourceRootSnapshot.create(**values)


def test_t02_caller_hashes_cannot_construct_an_acceptable_candidate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = minimal_root()
    genuine = mechanical_result(root)
    forged = mechanical_result(root, salt="caller-forged")
    with pytest.raises(TypeError, match="requires exact root"):
        T2ArtifactCandidate.model_validate(
            {
                "task_id": root.task_id,
                "source_root_hash": root.source_root_hash,
                "evaluation_inputs_hash": forged.evaluation_inputs_hash,
            }
        )
    candidate = T2ArtifactCandidate(root=root, rederivation=forged)
    monkeypatch.setattr(
        "trader_assist_v0.nautilus_g4.t2_shadow.fresh_process_rederive",
        lambda **_kwargs: genuine,
    )
    with pytest.raises(ValueError, match="genuine fresh-process"):
        verify_mechanical_t2(root=root, candidate=candidate, catalog_path=tmp_path)


def test_t03_complete_candidate_identity_must_equal_fresh_rederivation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = minimal_root()
    genuine = mechanical_result(root)
    exact = T2ArtifactCandidate(root=root, rederivation=genuine)
    monkeypatch.setattr(
        "trader_assist_v0.nautilus_g4.t2_shadow.fresh_process_rederive",
        lambda **_kwargs: genuine,
    )
    verified = verify_mechanical_t2(root=root, candidate=exact, catalog_path=tmp_path)
    assert verified.mechanically_verified is True
    assert verified.formal_real_t2_credit is False
    assert verified.real_t2_credit is False


@dataclass(frozen=True)
class RealFixture:
    root: T2SourceRootSnapshot
    execution_record: object


def _json_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        return value.model_dump_json().encode()
    return TypeAdapter(type(value)).dump_json(value)


def _native_instrument() -> object:
    from nautilus_trader.model import (
        CryptoPerpetual,
        Currency,
        InstrumentId,
        Price,
        Quantity,
        Symbol,
    )

    return CryptoPerpetual(
        instrument_id=InstrumentId.from_str(INSTRUMENT),
        raw_symbol=Symbol("ETH"),
        base_currency=Currency.from_str("ETH"),
        quote_currency=Currency.from_str("USDC"),
        settlement_currency=Currency.from_str("USDC"),
        is_inverse=False,
        price_precision=1,
        size_precision=3,
        price_increment=Price.from_str("0.1"),
        size_increment=Quantity.from_str("0.001"),
        ts_event=0,
        ts_init=0,
        margin_init=Decimal("0.05"),
        margin_maint=Decimal("0.025"),
        maker_fee=Decimal("0.0002"),
        taker_fee=Decimal("0.0005"),
    )


def _build_real_fixture(catalog_path: Path) -> RealFixture:
    from trader_assist_v0.multi_asset_shadow.models import (
        AssetClass,
        MarketIdentity,
        RegistryMarket,
        RegistryTier,
    )
    from trader_assist_v0.multi_asset_shadow.strategy_kernel.types import (
        DecisionKind,
        HtfRelation,
        SetupFamily,
        Side,
        StrategyDecision,
        TargetKind,
        TargetReference,
        ZoneQuality,
        ZoneSnapshot,
        ZoneType,
    )
    from trader_assist_v0.nautilus_e4.contracts import (
        AdmittedEvent,
        DataKind,
        EvidenceState,
        LifecycleKind,
        LifecycleRecord,
        LifecycleStatus,
        MarketExpression,
        PitUniverseSnapshot,
        RunManifest,
        SourceEvent,
    )
    from trader_assist_v0.nautilus_g4.catalog_bridge import (
        EvaluatorSupplementEvidence,
        admit_hypothetical_order_intent,
        project_native_replay,
    )
    from trader_assist_v0.nautilus_g4.runner import execute_provider_native_state
    from trader_assist_v0.vnext_g4.contracts import (
        AttemptStop,
        CandidateConfig,
        EntryActivation,
        EvidenceArtifactHash,
        ExecutionModelConfig,
        ExitPolicy,
        G4RunManifest,
        OrderPrimitive,
        PositionSide,
        ProspectiveEconomicCandidateIdentity,
        ReentryPolicy,
        RestartReferenceEvidence,
        RestartReferenceKind,
        ValidationReference,
        WinnerConfirmation,
    )
    from trader_assist_v0.vnext_g4.reporting import CostComponent, CostProvenance, ThesisOutcome

    zone = ZoneSnapshot(
        zone_id="zone-1",
        market_id=MARKET,
        zone_type=ZoneType.LOW,
        center=Decimal("2000"),
        low=Decimal("1990"),
        high=Decimal("2010"),
        half_width=Decimal("10"),
        quality=ZoneQuality.ZQ1,
        reaction_count=1,
        latest_reaction_bar_index=1,
        member_reaction_ids=("reaction-1",),
        active_for_new_event=True,
    )
    structural = StrategyDecision(
        market_id=MARKET,
        setup_family=SetupFamily.SWEEP_RECLAIM,
        setup_mode=None,
        retest_type=None,
        side=Side.LONG,
        decision=DecisionKind.FORMAL_SETUP_CONFIRMED,
        reason="ROOTED_FIXTURE",
        market_event_id="setup-1",
        zone_id=zone.zone_id,
        zone_snapshot=zone,
        a5_event=Decimal("10"),
        m20_event=Decimal("5"),
        htf_relation=HtfRelation.ALIGNED_STRONG,
        breakout_linkage=None,
        ideal_entry_low=Decimal("1990"),
        ideal_entry_high=Decimal("2005"),
        chase_limit=Decimal("2010"),
        structural_stop=Decimal("1980"),
        target_reference=TargetReference(
            kind=TargetKind.OPEN_SPACE_REFERENCE, price=Decimal("2100")
        ),
        transition="FORMAL_SETUP_CONFIRMED",
        scanner_linkage=None,
    )
    structural_artifact = artifact(
        T2SourceRole.STRUCTURAL_SOURCE,
        "structural",
        TypeAdapter(StrategyDecision).dump_json(structural),
    )
    validation = ValidationReference.create(
        validation_reference_id="validation-v1",
        source_artifact_hash="3" * 64,
        fee_profile_id="fee-v1",
        fee_profile_source_hash="4" * 64,
        fee_effective_at_ns=1,
        fee_bps=Decimal("1"),
        all_in_friction_state_id="friction-v1",
        all_in_friction_source_hash="5" * 64,
        all_in_friction_bps=Decimal("2"),
        execution_model_id="execution-v1",
        execution_model_source_hash="6" * 64,
        technical_quantity_rule_id="quantity-v1",
        technical_quantity_rule_source_hash="7" * 64,
        latency_control_id="latency-v1",
        latency_control_source_hash="8" * 64,
        latency_ms=Decimal("0"),
        latency_evidence_role="CONTROL_ONLY",
    )
    expression = MarketExpression(
        market_id=MARKET,
        dex="MAIN",
        provider_coin="ETH",
        instrument_id=INSTRUMENT,
        expression_id="expr-ETH",
        listing_state="ACTIVE",
        instrument_metadata_version="meta-v1",
        instrument_metadata_hash="b" * 64,
        fee_state_version="fee-v1",
        fee_state_hash="d" * 64,
    )
    pit_snapshot = PitUniverseSnapshot.create(
        observed_at_ns=1_700_000_000_000_000_000,
        expressions=(expression,),
    )
    e4_manifest = RunManifest.create(
        run_id="run-1",
        git_sha=PROJECT_GIT_OID,
        git_tree="a" * 40,
        snapshot=pit_snapshot,
        process_epoch="process-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
        capture_configuration={"mode": "rooted-t2-test"},
        subscription_policy={"scope": "ETH"},
        trial_ledger_id="trial-v1",
    )
    from trader_assist_v0.vnext_g4.contracts import CausalLineage

    lineage = CausalLineage.create(
        source_e4_manifest_hash=e4_manifest.manifest_hash,
        source_pit_snapshot_hash=pit_snapshot.snapshot_hash,
        source_structural_artifact_hash=structural_artifact.artifact_hash,
        structural_component_manifest_hash=structural_artifact.artifact_hash,
        market_id=MARKET,
        instrument_id=INSTRUMENT,
        formal_setup_id="setup-1",
        formal_setup_admission_ordinal=1,
        formal_setup_admission_ts=10,
        thesis_id="thesis-1",
        activation_sequence_id="activation-1",
        attempt_lineage_id="attempt-1",
        restart_reference_id="restart-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
        instrument_metadata_version="meta-v1",
        instrument_metadata_hash="b" * 64,
        validation_reference_id=validation.validation_reference_id,
        validation_reference_hash=validation.reference_hash,
    )
    source = SourceEvent.create(
        market_id=MARKET,
        expression_id="expr-ETH",
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id=INSTRUMENT,
        data_kind=DataKind.BBO,
        source_event_id="bbo-3",
        native_trade_id=None,
        provider_aggressor_side=None,
        event_context="accepted-bbo",
        ts_event=1_700_000_000_000_000_000,
        ts_init=1_700_000_000_000_000_001,
        true_network_receive_ts=None,
        payload={
            "bid_price": "1999.0",
            "ask_price": "2001.0",
            "bid_size": "2.000",
            "ask_size": "2.000",
        },
    )
    admitted = AdmittedEvent.create(
        schema_version="E4_CAPTURE_V1",
        process_epoch="process-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
        admission_ordinal=3,
        admission_ts=1_700_000_000_000_000_002,
        source_identity=source.replay_identity,
        out_of_order=False,
        continuity_state=EvidenceState.COMPLETE,
        source=source,
    )
    lifecycle = (
        LifecycleRecord.create(
            schema_version="E4_CAPTURE_V1",
            run_id="run-1",
            object_id="thesis-1",
            parent_id=None,
            package_id="package-1",
            market_id=MARKET,
            expression_id="expr-ETH",
            kind=LifecycleKind.THESIS,
            status=LifecycleStatus.ACTIVE,
            state_ts=20,
            reason_codes=("THESIS_CREATED",),
            decision_state=None,
            approval_timing_mode=None,
            approval_provenance="NOT_APPLICABLE",
            expiry_ts=None,
            supersedes_id=None,
            last_admission_ordinal=1,
            evidence_state=EvidenceState.COMPLETE,
        ),
        LifecycleRecord.create(
            schema_version="E4_CAPTURE_V1",
            run_id="run-1",
            object_id="thesis-1",
            parent_id=None,
            package_id="package-1",
            market_id=MARKET,
            expression_id="expr-ETH",
            kind=LifecycleKind.THESIS,
            status=LifecycleStatus.ACTIVE,
            state_ts=30,
            reason_codes=("ACTIVE_VALID",),
            decision_state=None,
            approval_timing_mode=None,
            approval_provenance="NOT_APPLICABLE",
            expiry_ts=None,
            supersedes_id=None,
            last_admission_ordinal=2,
            evidence_state=EvidenceState.COMPLETE,
        ),
    )
    restart = RestartReferenceEvidence.create(
        lineage_hash=lineage.lineage_hash,
        restart_reference_id="restart-1",
        side=PositionSide.LONG,
        kind=RestartReferenceKind.PIVOT_HIGH,
        price=Decimal("1990"),
        reset_admission_ordinal=1,
        confirmed_admission_ordinal=1,
        confirmed_admission_ts=10,
        source_artifact_hash="c" * 64,
    )
    registry = RegistryMarket(
        display="ETH",
        tier=RegistryTier.P0,
        identity=MarketIdentity.create(dex="MAIN", coin="ETH"),
        asset_class=AssetClass.CRYPTO,
        size_decimals=3,
        price_max_significant_figures=5,
        price_max_decimals=1,
        is_hip3=False,
        market_status="ACTIVE",
        metadata_observed_at=datetime(2026, 9, 20, tzinfo=UTC),
        metadata_hash="b" * 64,
    )
    supplement = EvaluatorSupplementEvidence.create(
        causal_lineage_hash=lineage.lineage_hash,
        source_artifact_hash="e" * 64,
        microstructure_warmup_seconds=60,
        side_adjusted_aggressor_imbalance_15s=Decimal("1"),
        flow_price_response_15s_bps=Decimal("1"),
    )
    config = CandidateConfig(
        entry_activation=EntryActivation.EA0,
        attempt_stop=AttemptStop.AP0,
        room_to_cost_k=Decimal("3"),
        reentry_policy=ReentryPolicy.NO_REENTRY_REFERENCE,
        winner_confirmation=WinnerConfirmation.WC0,
        winner_progress_bps=Decimal("10"),
        exit_policy=ExitPolicy.X0,
        comparison_role="REFERENCE",
    )
    prospective = ProspectiveEconomicCandidateIdentity.create(
        candidate_id="TASK5D_PHASE0C_TECHNICAL_REFERENCE_V1",
        config=config,
    )
    selected = prospective.materialize_candidate_manifest(
        structural_component_manifest_hash=structural_artifact.artifact_hash
    )
    execution_model = ExecutionModelConfig(
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
    g4 = G4RunManifest.create(
        run_id="run-1",
        git_sha=PROJECT_GIT_OID,
        git_tree="a" * 40,
        source_e4_manifest_hash=e4_manifest.manifest_hash,
        source_pit_snapshot_hash=pit_snapshot.snapshot_hash,
        source_evidence_artifact_hashes=(EvidenceArtifactHash(name="admissions", sha256=H),),
        structural_component_manifest_hash=structural_artifact.artifact_hash,
        execution_model=execution_model,
        candidates=(selected,),
        trial_adaptivity_id="trial-v1",
        cutoff_id="cutoff-v1",
    )
    instrument = _native_instrument()
    wire = instrument.to_dict()
    wire_hash = sha256_hex(canonical_json_bytes(wire))
    intent_admission = admit_hypothetical_order_intent(
        strategy_decision_id=structural_artifact.artifact_hash,
        candidate_hash=selected.candidate_hash,
        side=PositionSide.LONG,
        lineage=lineage,
        current_bbo=admitted,
        technical_quantity=Decimal(str(instrument.size_increment)),
        size_decimals=int(instrument.size_precision),
        activation_reference_hash=restart.reference_hash,
        validation=validation,
    )
    assert intent_admission.intent is not None, intent_admission.reason_codes
    projection = project_native_replay(
        events=(admitted,),
        market_id=MARKET,
        expression_id=expression.expression_id,
        instrument_id=INSTRUMENT,
    )
    execution = execute_provider_native_state(
        projection=projection,
        intent=intent_admission.intent,
        trigger_admission_hash=admitted.admission_hash,
        provider_instrument=instrument,
        catalog_path=catalog_path,
    )
    cost_artifacts = tuple(
        artifact(T2SourceRole.COST_SOURCE, name, name.encode())
        for name in ("fee", "spread", "slippage", "impact", "funding", "shortfall")
    )
    costs = tuple(
        CostComponent(
            amount_bps=Decimal("0"),
            provenance=CostProvenance.PROVEN_ZERO,
            source_hash=item.artifact_hash,
        )
        for item in cost_artifacts
    )
    outcome = ThesisOutcome(
        thesis_id=lineage.thesis_id,
        market_id=lineage.market_id,
        provider_state_source_hash=provider_state_semantic_source_hash(execution.record),
        order_intent_hash=intent_admission.intent.order_intent_hash,
        decision="TAKE",
        attempt_count=1,
        net_r_after_cost=Decimal("1"),
        fee=costs[0],
        spread=costs[1],
        slippage=costs[2],
        impact_size_feasibility=costs[3],
        funding=costs[4],
        implementation_shortfall=costs[5],
    )
    e4_run = artifact(
        T2SourceRole.E4_RUN_MANIFEST, "e4-run", _json_bytes(e4_manifest)
    )
    e4_pit = artifact(
        T2SourceRole.E4_PIT_SNAPSHOT, "e4-pit", _json_bytes(pit_snapshot)
    )
    g4_artifact = artifact(T2SourceRole.G4_RUN_MANIFEST, "g4-run", _json_bytes(g4))
    prospective_artifact = artifact(
        T2SourceRole.PROSPECTIVE_ECONOMIC_CANDIDATE_IDENTITY,
        "prospective-candidate",
        _json_bytes(prospective),
    )
    selected_artifact = artifact(
        T2SourceRole.SELECTED_CANDIDATE,
        "selected",
        _json_bytes(selected),
        references=(
            SourceReference(
                role=prospective_artifact.role,
                name=prospective_artifact.name,
                artifact_hash=prospective_artifact.artifact_hash,
            ),
        ),
    )
    validation_artifact = artifact(
        T2SourceRole.VALIDATION_REFERENCE, "validation", _json_bytes(validation)
    )
    items = (
        e4_run,
        e4_pit,
        g4_artifact,
        selected_artifact,
        prospective_artifact,
        validation_artifact,
        structural_artifact,
        artifact(T2SourceRole.CAUSAL_LINEAGE, "lineage", _json_bytes(lineage)),
        artifact(T2SourceRole.E4_ADMISSION, "admission-z", _json_bytes(admitted)),
        artifact(T2SourceRole.E4_LIFECYCLE, "lifecycle-z", _json_bytes(lifecycle[1])),
        artifact(T2SourceRole.E4_LIFECYCLE, "lifecycle-a", _json_bytes(lifecycle[0])),
        artifact(T2SourceRole.RESTART_REFERENCE, "restart-z", _json_bytes(restart)),
        artifact(T2SourceRole.EVALUATOR_SUPPLEMENT, "supplement", _json_bytes(supplement)),
        artifact(T2SourceRole.MARKET_EXPRESSION, "expression", _json_bytes(expression)),
        artifact(T2SourceRole.REGISTRY_MARKET, "registry", _json_bytes(registry)),
        artifact(
            T2SourceRole.PROVIDER_INSTRUMENT_WIRE,
            "instrument-wire",
            canonical_json_bytes(wire),
        ),
        artifact(
            T2SourceRole.INSTRUMENT_METADATA,
            "instrument-metadata",
            canonical_json_bytes({"provider_wire_hash": wire_hash}),
        ),
        artifact(T2SourceRole.THESIS_OUTCOME, "outcome", _json_bytes(outcome)),
        *cost_artifacts,
    )
    root = T2SourceRootSnapshot.create(
        task_id="PILOT_TASK3_R3_ROOTED_T2_V3_REPLACEMENT",
        governance_epoch=G,
        acquisition_plan_hash=H,
        exact_source_git_head=PROJECT_GIT_OID,
        exact_source_git_tree="a" * 40,
        e4_run_manifest_hash=e4_run.artifact_hash,
        e4_pit_snapshot_hash=e4_pit.artifact_hash,
        g4_run_manifest_hash=g4_artifact.artifact_hash,
        selected_candidate_hash=selected_artifact.artifact_hash,
        strategy_package_identity="strategy-v1",
        validation_reference_hash=validation_artifact.artifact_hash,
        artifacts=items,
    )
    return RealFixture(root=root, execution_record=execution.record)


@pytest.fixture(scope="module")
def real_fixture(tmp_path_factory: pytest.TempPathFactory) -> RealFixture:
    if not NAUTILUS_AVAILABLE:
        pytest.skip("pinned Nautilus rc5 is absent")
    return _build_real_fixture(tmp_path_factory.mktemp("rooted-t2-precompute"))


def _replace_role_artifacts(
    root: T2SourceRootSnapshot,
    role: T2SourceRole,
    replacements: tuple[RoleBoundSourceArtifact, ...],
) -> T2SourceRootSnapshot:
    values = root.model_dump(mode="python", exclude={"source_root_hash"})
    values["artifacts"] = (
        *(item for item in root.artifacts if item.role is not role),
        *replacements,
    )
    return T2SourceRootSnapshot.create(**values)


def _patch_execution(monkeypatch: pytest.MonkeyPatch, record: object) -> None:
    monkeypatch.setattr(
        "trader_assist_v0.nautilus_g4.runner.execute_provider_native_state",
        lambda **_kwargs: SimpleNamespace(record=record),
    )


def _replace_declared_role_artifact(
    root: T2SourceRootSnapshot,
    role: T2SourceRole,
    replacement: RoleBoundSourceArtifact,
) -> T2SourceRootSnapshot:
    field_by_role = {
        T2SourceRole.E4_RUN_MANIFEST: "e4_run_manifest_hash",
        T2SourceRole.E4_PIT_SNAPSHOT: "e4_pit_snapshot_hash",
        T2SourceRole.G4_RUN_MANIFEST: "g4_run_manifest_hash",
        T2SourceRole.SELECTED_CANDIDATE: "selected_candidate_hash",
    }
    values = root.model_dump(mode="python", exclude={"source_root_hash"})
    values["artifacts"] = (
        *(item for item in root.artifacts if item.role is not role),
        replacement,
    )
    values[field_by_role[role]] = replacement.artifact_hash
    return T2SourceRootSnapshot.create(**values)


def _prospective_artifact(root: T2SourceRootSnapshot) -> RoleBoundSourceArtifact:
    return next(
        item
        for item in root.artifacts
        if item.role is T2SourceRole.PROSPECTIVE_ECONOMIC_CANDIDATE_IDENTITY
    )


def _selected_artifact(root: T2SourceRootSnapshot) -> RoleBoundSourceArtifact:
    return next(
        item for item in root.artifacts if item.role is T2SourceRole.SELECTED_CANDIDATE
    )


def _replace_selected_and_prospective(
    root: T2SourceRootSnapshot,
    *,
    selected: RoleBoundSourceArtifact,
    prospective: RoleBoundSourceArtifact | None,
) -> T2SourceRootSnapshot:
    values = root.model_dump(mode="python", exclude={"source_root_hash"})
    values["artifacts"] = (
        *(
            item
            for item in root.artifacts
            if item.role
            not in {
                T2SourceRole.SELECTED_CANDIDATE,
                T2SourceRole.PROSPECTIVE_ECONOMIC_CANDIDATE_IDENTITY,
            }
        ),
        selected,
        *((prospective,) if prospective is not None else ()),
    )
    values["selected_candidate_hash"] = selected.artifact_hash
    return T2SourceRootSnapshot.create(**values)


@REQUIRES_NAUTILUS
def test_t04_prospective_identity_is_rooted_and_selected_candidate_references_it(
    real_fixture: RealFixture,
) -> None:
    prospective = _prospective_artifact(real_fixture.root)
    selected = _selected_artifact(real_fixture.root)
    assert tuple(
        item
        for item in real_fixture.root.artifacts
        if item.role is T2SourceRole.PROSPECTIVE_ECONOMIC_CANDIDATE_IDENTITY
    ) == (prospective,)
    assert SourceReference(
        role=prospective.role,
        name=prospective.name,
        artifact_hash=prospective.artifact_hash,
    ) in selected.references


@REQUIRES_NAUTILUS
def test_t04_prospective_identity_is_required_before_participation(
    real_fixture: RealFixture, tmp_path: Path
) -> None:
    selected = _selected_artifact(real_fixture.root)
    unreferenced = artifact(
        T2SourceRole.SELECTED_CANDIDATE,
        selected.name,
        selected.exact_bytes(),
    )
    root = _replace_selected_and_prospective(
        real_fixture.root, selected=unreferenced, prospective=None
    )
    with pytest.raises(ValueError, match="requires exactly one PROSPECTIVE_ECONOMIC"):
        rederive_rooted_t2(root=root, catalog_path=tmp_path)


@REQUIRES_NAUTILUS
def test_t04_selected_candidate_requires_exact_prospective_edge(
    real_fixture: RealFixture, tmp_path: Path
) -> None:
    selected = _selected_artifact(real_fixture.root)
    unreferenced = artifact(
        T2SourceRole.SELECTED_CANDIDATE,
        selected.name,
        selected.exact_bytes(),
    )
    root = _replace_selected_and_prospective(
        real_fixture.root,
        selected=unreferenced,
        prospective=_prospective_artifact(real_fixture.root),
    )
    with pytest.raises(ValueError, match="does not reference the exact prospective"):
        rederive_rooted_t2(root=root, catalog_path=tmp_path)


@pytest.mark.parametrize("mismatch", ("candidate_id", "config"))
@REQUIRES_NAUTILUS
def test_t04_prospective_economic_mismatch_fails_closed(
    real_fixture: RealFixture,
    tmp_path: Path,
    mismatch: str,
) -> None:
    from trader_assist_v0.vnext_g4.contracts import (
        CandidateConfig,
        ProspectiveEconomicCandidateIdentity,
    )

    current_artifact = _prospective_artifact(real_fixture.root)
    current = ProspectiveEconomicCandidateIdentity.model_validate_json(
        current_artifact.exact_bytes()
    )
    if mismatch == "candidate_id":
        changed = ProspectiveEconomicCandidateIdentity.create(
            candidate_id="different-prospective-candidate",
            config=current.config,
        )
    else:
        changed_config = CandidateConfig.model_validate(
            {**current.config.model_dump(mode="python"), "room_to_cost_k": Decimal("2")}
        )
        changed = ProspectiveEconomicCandidateIdentity.create(
            candidate_id=current.candidate_id,
            config=changed_config,
        )
    changed_artifact = artifact(
        T2SourceRole.PROSPECTIVE_ECONOMIC_CANDIDATE_IDENTITY,
        current_artifact.name,
        _json_bytes(changed),
    )
    structural_artifact = next(
        item
        for item in real_fixture.root.artifacts
        if item.role is T2SourceRole.STRUCTURAL_SOURCE
    )
    matching_selected = changed.materialize_candidate_manifest(
        structural_component_manifest_hash=structural_artifact.artifact_hash
    )
    selected = _selected_artifact(real_fixture.root)
    rewired_selected = artifact(
        T2SourceRole.SELECTED_CANDIDATE,
        selected.name,
        _json_bytes(matching_selected),
        references=(
            SourceReference(
                role=changed_artifact.role,
                name=changed_artifact.name,
                artifact_hash=changed_artifact.artifact_hash,
            ),
        ),
    )
    root = _replace_selected_and_prospective(
        real_fixture.root,
        selected=rewired_selected,
        prospective=changed_artifact,
    )
    with pytest.raises(ValueError, match="does not match the frozen Phase 0C identity"):
        rederive_rooted_t2(root=root, catalog_path=tmp_path)


@REQUIRES_NAUTILUS
def test_t04_prospective_version_tamper_fails_closed(
    real_fixture: RealFixture, tmp_path: Path
) -> None:
    current_artifact = _prospective_artifact(real_fixture.root)
    raw = json.loads(current_artifact.exact_bytes())
    raw["strategy_version"] = "TA_VNEXT_E4_C1_2026-09-11"
    changed_artifact = artifact(
        T2SourceRole.PROSPECTIVE_ECONOMIC_CANDIDATE_IDENTITY,
        current_artifact.name,
        canonical_json_bytes(raw),
    )
    selected = _selected_artifact(real_fixture.root)
    rewired_selected = artifact(
        T2SourceRole.SELECTED_CANDIDATE,
        selected.name,
        selected.exact_bytes(),
        references=(
            SourceReference(
                role=changed_artifact.role,
                name=changed_artifact.name,
                artifact_hash=changed_artifact.artifact_hash,
            ),
        ),
    )
    root = _replace_selected_and_prospective(
        real_fixture.root,
        selected=rewired_selected,
        prospective=changed_artifact,
    )
    with pytest.raises(ValidationError, match="strategy_version"):
        rederive_rooted_t2(root=root, catalog_path=tmp_path)


@REQUIRES_NAUTILUS
def test_t04_selected_candidate_cannot_bind_another_structural_hash(
    real_fixture: RealFixture, tmp_path: Path
) -> None:
    from trader_assist_v0.vnext_g4.contracts import ProspectiveEconomicCandidateIdentity

    prospective_artifact = _prospective_artifact(real_fixture.root)
    prospective = ProspectiveEconomicCandidateIdentity.model_validate_json(
        prospective_artifact.exact_bytes()
    )
    wrong = prospective.materialize_candidate_manifest(
        structural_component_manifest_hash="f" * 64
    )
    selected = artifact(
        T2SourceRole.SELECTED_CANDIDATE,
        "selected",
        _json_bytes(wrong),
        references=(
            SourceReference(
                role=prospective_artifact.role,
                name=prospective_artifact.name,
                artifact_hash=prospective_artifact.artifact_hash,
            ),
        ),
    )
    root = _replace_selected_and_prospective(
        real_fixture.root,
        selected=selected,
        prospective=prospective_artifact,
    )
    with pytest.raises(ValueError, match="not the exact source-bound prospective"):
        rederive_rooted_t2(root=root, catalog_path=tmp_path)


@REQUIRES_NAUTILUS
def test_t04a_e4_manifest_must_cross_bind_lineage_and_g4(
    real_fixture: RealFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from trader_assist_v0.nautilus_e4.contracts import PitUniverseSnapshot, RunManifest

    _patch_execution(monkeypatch, real_fixture.execution_record)
    manifest_artifact = next(
        item
        for item in real_fixture.root.artifacts
        if item.role is T2SourceRole.E4_RUN_MANIFEST
    )
    pit_artifact = next(
        item
        for item in real_fixture.root.artifacts
        if item.role is T2SourceRole.E4_PIT_SNAPSHOT
    )
    manifest = RunManifest.model_validate_json(manifest_artifact.exact_bytes())
    pit = PitUniverseSnapshot.model_validate_json(pit_artifact.exact_bytes())
    other = RunManifest.create(
        run_id="run-other",
        git_sha=manifest.git_sha,
        git_tree=manifest.git_tree,
        snapshot=pit,
        process_epoch=manifest.process_epoch,
        continuity_epoch=manifest.continuity_epoch,
        admission_epoch=manifest.admission_epoch,
        capture_configuration=manifest.capture_configuration,
        subscription_policy=manifest.subscription_policy,
        trial_ledger_id=manifest.trial_ledger_id,
    )
    root = _replace_declared_role_artifact(
        real_fixture.root,
        T2SourceRole.E4_RUN_MANIFEST,
        artifact(T2SourceRole.E4_RUN_MANIFEST, "e4-run", _json_bytes(other)),
    )
    with pytest.raises(ValueError, match="E4 manifest is not cross-bound"):
        rederive_rooted_t2(root=root, catalog_path=tmp_path)


@REQUIRES_NAUTILUS
def test_t04b_e4_manifest_must_bind_rooted_pit_snapshot(
    real_fixture: RealFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from trader_assist_v0.nautilus_e4.contracts import PitUniverseSnapshot

    _patch_execution(monkeypatch, real_fixture.execution_record)
    pit_artifact = next(
        item
        for item in real_fixture.root.artifacts
        if item.role is T2SourceRole.E4_PIT_SNAPSHOT
    )
    pit = PitUniverseSnapshot.model_validate_json(pit_artifact.exact_bytes())
    other = PitUniverseSnapshot.create(
        observed_at_ns=pit.observed_at_ns + 1,
        expressions=pit.expressions,
    )
    root = _replace_declared_role_artifact(
        real_fixture.root,
        T2SourceRole.E4_PIT_SNAPSHOT,
        artifact(T2SourceRole.E4_PIT_SNAPSHOT, "e4-pit", _json_bytes(other)),
    )
    with pytest.raises(ValueError, match="E4 manifest does not bind rooted PIT"):
        rederive_rooted_t2(root=root, catalog_path=tmp_path)


@REQUIRES_NAUTILUS
def test_t04c_g4_manifest_must_share_e4_identity_with_lineage(
    real_fixture: RealFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from trader_assist_v0.vnext_g4.contracts import CandidateManifest, G4RunManifest

    _patch_execution(monkeypatch, real_fixture.execution_record)
    g4_artifact = next(
        item
        for item in real_fixture.root.artifacts
        if item.role is T2SourceRole.G4_RUN_MANIFEST
    )
    selected_artifact = next(
        item
        for item in real_fixture.root.artifacts
        if item.role is T2SourceRole.SELECTED_CANDIDATE
    )
    g4 = G4RunManifest.model_validate_json(g4_artifact.exact_bytes())
    selected = CandidateManifest.model_validate_json(selected_artifact.exact_bytes())
    other = G4RunManifest.create(
        run_id=g4.run_id,
        git_sha=g4.git_sha,
        git_tree=g4.git_tree,
        source_e4_manifest_hash="f" * 64,
        source_pit_snapshot_hash=g4.source_pit_snapshot_hash,
        source_evidence_artifact_hashes=g4.source_evidence_artifact_hashes,
        structural_component_manifest_hash=g4.structural_component_manifest_hash,
        execution_model=g4.execution_model,
        candidates=(selected,),
        trial_adaptivity_id=g4.trial_adaptivity_id,
        cutoff_id=g4.cutoff_id,
    )
    root = _replace_declared_role_artifact(
        real_fixture.root,
        T2SourceRole.G4_RUN_MANIFEST,
        artifact(T2SourceRole.G4_RUN_MANIFEST, "g4-run", _json_bytes(other)),
    )
    with pytest.raises(ValueError, match="E4 manifest is not cross-bound"):
        rederive_rooted_t2(root=root, catalog_path=tmp_path)


@REQUIRES_NAUTILUS
def test_t04_artifact_names_do_not_control_semantic_owner_order(
    real_fixture: RealFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_execution(monkeypatch, real_fixture.execution_record)
    original = rederive_rooted_t2(root=real_fixture.root, catalog_path=tmp_path / "original")
    lifecycle = tuple(
        artifact(item.role, f"renamed-{index}", item.exact_bytes())
        for index, item in enumerate(
            reversed(
                tuple(
                    source
                    for source in real_fixture.root.artifacts
                    if source.role is T2SourceRole.E4_LIFECYCLE
                )
            )
        )
    )
    renamed = _replace_role_artifacts(
        real_fixture.root, T2SourceRole.E4_LIFECYCLE, lifecycle
    )
    repeated = rederive_rooted_t2(root=renamed, catalog_path=tmp_path / "renamed")
    assert repeated.owner_payload() == original.owner_payload()
    assert repeated.source_root_hash != original.source_root_hash


@REQUIRES_NAUTILUS
def test_t05_causal_record_mutation_rejects_semantically(
    real_fixture: RealFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from trader_assist_v0.nautilus_e4.contracts import LifecycleRecord

    _patch_execution(monkeypatch, real_fixture.execution_record)
    target = next(
        item
        for item in real_fixture.root.artifacts
        if item.role is T2SourceRole.E4_LIFECYCLE
        and "THESIS_CREATED" in item.exact_bytes().decode()
    )
    record = LifecycleRecord.model_validate_json(target.exact_bytes())
    values = record.model_dump(mode="python", exclude={"record_hash"})
    values["market_id"] = sha256_hex(b"other-market")
    mutated = LifecycleRecord.create(**values)
    replacement = artifact(target.role, target.name, _json_bytes(mutated))
    root = _replace_role_artifacts(
        real_fixture.root,
        T2SourceRole.E4_LIFECYCLE,
        tuple(
            replacement if item.name == target.name else item
            for item in real_fixture.root.artifacts
            if item.role is T2SourceRole.E4_LIFECYCLE
        ),
    )
    with pytest.raises(ValueError, match="THESIS_LIFECYCLE_MARKET_CONFLICT"):
        rederive_rooted_t2(root=root, catalog_path=tmp_path)


def _mutate_outcome(
    root: T2SourceRootSnapshot, **changes: object
) -> T2SourceRootSnapshot:
    from trader_assist_v0.vnext_g4.reporting import ThesisOutcome

    current = next(item for item in root.artifacts if item.role is T2SourceRole.THESIS_OUTCOME)
    outcome = ThesisOutcome.model_validate_json(current.exact_bytes())
    values = {**outcome.model_dump(mode="python"), **changes}
    if values["decision"] != "TAKE" and "order_intent_hash" not in changes:
        values["order_intent_hash"] = outcome.order_intent_hash
    replacement = artifact(current.role, current.name, _json_bytes(ThesisOutcome(**values)))
    return _replace_role_artifacts(root, T2SourceRole.THESIS_OUTCOME, (replacement,))


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"thesis_id": "thesis-other"}, "another thesis"),
        ({"market_id": sha256_hex(b"other-market")}, "another market"),
        ({"decision": "PASS"}, "decision is not TAKE"),
    ),
    ids=("T06-other-thesis", "T07-other-market", "T08-non-take"),
)
@REQUIRES_NAUTILUS
def test_t06_t08_outcome_must_bind_same_take_lineage(
    real_fixture: RealFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    changes: dict[str, object],
    message: str,
) -> None:
    _patch_execution(monkeypatch, real_fixture.execution_record)
    with pytest.raises(ValueError, match=message):
        rederive_rooted_t2(
            root=_mutate_outcome(real_fixture.root, **changes), catalog_path=tmp_path
        )


@REQUIRES_NAUTILUS
def test_t09_fresh_child_uses_installed_module_from_non_repository_cwd(
    real_fixture: RealFixture, tmp_path: Path
) -> None:
    result = fresh_process_rederive(root=real_fixture.root, catalog_path=tmp_path / "catalog")
    assert result.source_root_hash == real_fixture.root.source_root_hash
    assert result.decision == "TAKE"


def _positive_acceptance_graph(
    root: T2SourceRootSnapshot, candidate: T2ArtifactCandidate
) -> tuple[AcceptedRealT2Receipt, CanonicalAcceptanceExpectation]:
    receipt = AcceptedRealT2Receipt.create(
        acceptance_claim="ACCEPTED",
        task_id=root.task_id,
        governance_epoch=root.governance_epoch,
        accepted_t2_source_root_hash=root.source_root_hash,
        t2_artifact_candidate_hash=candidate.candidate_hash,
        exact_implementation_head=PROJECT_GIT_OID,
        exact_implementation_tree="a" * 40,
        required_ci_run_ids_and_conclusions=("run-1:success",),
        fresh_independent_review_result_key="review-pass",
        fresh_independent_review_locator="issue-comment-1",
        fresh_independent_review_verdict="PASS",
        exact_reviewed_head=PROJECT_GIT_OID,
        canonical_acceptance_receipt_key="receipt-key",
    )
    deserialized = AcceptedRealT2Receipt.model_validate_json(receipt.model_dump_json())
    canonical = CanonicalAcceptanceExpectation(
        task_id=root.task_id,
        governance_epoch=root.governance_epoch,
        source_root_hash=root.source_root_hash,
        candidate_hash=candidate.candidate_hash,
        implementation_head=PROJECT_GIT_OID,
        implementation_tree="a" * 40,
        required_ci_run_ids_and_conclusions=("run-1:success",),
        independent_review_result_key="review-pass",
        independent_review_locator="issue-comment-1",
        exact_reviewed_head=PROJECT_GIT_OID,
        canonical_receipt_key="receipt-key",
        copied_receipt_evidence_hash=deserialized.evidence_hash,
    )
    return deserialized, CanonicalAcceptanceExpectation.model_validate_json(
        canonical.model_dump_json()
    )


def test_t10_strongest_local_positive_object_graph_has_zero_formal_authority() -> None:
    root = minimal_root()
    candidate = T2ArtifactCandidate(root=root, rederivation=mechanical_result(root))
    receipt, canonical = _positive_acceptance_graph(root, candidate)
    decision = assess_local_acceptance_evidence(receipt=receipt, canonical=canonical)
    assert receipt.acceptance_claim == "ACCEPTED"
    assert receipt.fresh_independent_review_verdict == "PASS"
    assert decision.evidence_consistent is True
    assert decision.claimed_accepted is True
    assert decision.formal_real_t2_credit is False
    assert decision.real_t2_credit is False


@REQUIRES_NAUTILUS
def test_t11_genuine_mechanics_plus_local_acceptance_still_has_no_formal_credit(
    real_fixture: RealFixture, tmp_path: Path
) -> None:
    local = rederive_rooted_t2(
        root=real_fixture.root, catalog_path=tmp_path / "local-catalog"
    )
    candidate = T2ArtifactCandidate(root=real_fixture.root, rederivation=local)
    mechanical = verify_mechanical_t2(
        root=real_fixture.root,
        candidate=candidate,
        catalog_path=tmp_path / "child-catalog",
    )
    receipt, canonical = _positive_acceptance_graph(real_fixture.root, candidate)
    local_acceptance = assess_local_acceptance_evidence(receipt=receipt, canonical=canonical)
    assert mechanical.mechanically_verified is True
    assert candidate.real_t2_credit is False
    assert mechanical.formal_real_t2_credit is False
    assert local_acceptance.evidence_consistent is True
    assert local_acceptance.formal_real_t2_credit is False
    assert local_acceptance.real_t2_credit is False


def test_cli_without_real_root_is_truthful(capsys: pytest.CaptureFixture[str]) -> None:
    from trader_assist_v0.nautilus_g4.t2_shadow import main

    assert main([]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["R3_RUNTIME_T2_STATUS"] == "NONDECISIVE_REAL_INPUT_ABSENT"
    assert result["FORMAL_REAL_T2_CREDIT"] == "NO"
    assert result["REAL_T2_CREDIT"] == "NO"


def test_task5d_strict_root_cannot_reuse_legacy_hand_authored_source_graph(
    tmp_path: Path,
) -> None:
    from trader_assist_v0.nautilus_g4.t2_acquisition import REAL_T2_TASK_ID

    legacy = minimal_root()
    values = legacy.model_dump(mode="python", exclude={"source_root_hash"})
    values["task_id"] = REAL_T2_TASK_ID
    strict = T2SourceRootSnapshot.create(**values)
    with pytest.raises(ValueError, match="PROSPECTIVE_ECONOMIC_CANDIDATE_IDENTITY"):
        rederive_rooted_t2(root=strict, catalog_path=tmp_path)
