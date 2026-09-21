#!/usr/bin/env python3
# mypy: disable-error-code="import-not-found"
"""Single-attempt public-only Task #5D Real-T2 acquisition entrypoint."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import threading
import time
from decimal import Decimal
from pathlib import Path

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import HyperliquidPublicClient
from trader_assist_v0.nautilus_e4.capture import SubscriptionPolicy
from trader_assist_v0.nautilus_e4.contracts import PitUniverseSnapshot, RunManifest
from trader_assist_v0.nautilus_e4.host import (
    NautilusE4CaptureStrategy,
    assert_exact_nautilus_version,
    build_capture_strategy,
    build_public_data_node,
)
from trader_assist_v0.nautilus_e4.safety import assert_public_only
from trader_assist_v0.nautilus_g4.t2_acquisition import (
    CausalBboBinding,
    PHASE0C_MARKET_SET_HASH,
    REAL_T2_ACQUISITION_NS,
    REAL_T2_ACQUISITION_SECONDS,
    REAL_T2_TASK_ID,
    RealT2IntegrationError,
    RealT2StrategyCoordinator,
    assemble_real_t2_root,
    assess_public_funding_history,
    derive_evaluator_supplement_source,
    derive_restart_pivot_source,
    expected_external_bar_type,
    frozen_task5d_prospective_candidate,
    materialize_fixed_markets_from_public_metadata,
    materialize_evaluator_supplement,
    materialize_restart_reference,
    materialize_task5d_g4_manifest,
    materialize_task5d_validation_source,
    position_side_for_focal,
    provider_instrument_metadata_document,
    select_first_exit_trigger,
)
from trader_assist_v0.nautilus_g4.catalog_bridge import (
    admit_hypothetical_order_intent,
    project_native_replay,
)
from trader_assist_v0.nautilus_g4.runner import (
    execute_provider_native_round_trip_state,
    provider_round_trip_state_semantic_source_hash,
)
from trader_assist_v0.nautilus_g4.t2_shadow import (
    RoleBoundSourceArtifact,
    SourceReference,
    T2SourceRole,
)
from trader_assist_v0.vnext_g4.contracts import CausalLineage
from trader_assist_v0.vnext_g4.reporting import CostComponent, CostProvenance, ThesisOutcome

_GIT_OID = re.compile(r"^[0-9a-f]{40}$")
TASK_PACKET_SHA256 = "9be069776518f311872e0e1cde25efc74a6f1a4f97726a1f36ab4ef865107250"
RESULT_SCHEMA = "TASK5D_REAL_T2_ACQUISITION_RESULT_V1"
NOT_EVALUABLE = 2
APPLICATION_FAILURE = 3
GOVERNANCE_EPOCH = "900cc84d5162512322b5c0f5cd0715e46e36133398ab1c6b5744a0506145f171"


def _git_identity() -> tuple[str, str]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"], check=True, capture_output=True, text=True
    ).stdout.strip()
    if not _GIT_OID.fullmatch(head) or not _GIT_OID.fullmatch(tree):
        raise RealT2IntegrationError("git identity is invalid")
    return head, tree


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(canonical_json_bytes(payload) + b"\n")
    tmp.replace(path)


def _reference(artifact: RoleBoundSourceArtifact) -> SourceReference:
    return SourceReference(
        role=artifact.role,
        name=artifact.name,
        artifact_hash=artifact.artifact_hash,
    )


def _cost_source(
    *, name: str, payload: dict[str, object], provenance: CostProvenance,
    amount_bps: Decimal | None,
) -> tuple[RoleBoundSourceArtifact, CostComponent]:
    artifact = RoleBoundSourceArtifact.create(
        role=T2SourceRole.COST_SOURCE,
        name=name,
        exact_bytes=canonical_json_bytes(payload),
    )
    return artifact, CostComponent(
        amount_bps=amount_bps,
        provenance=provenance,
        source_hash=artifact.artifact_hash,
    )


def _build_bar_type(instrument_id: str, minutes: int) -> str:
    from nautilus_trader.model import (
        AggregationSource,
        BarAggregation,
        BarSpecification,
        BarType,
        InstrumentId,
        PriceType,
    )
    built = str(BarType(
        InstrumentId.from_str(instrument_id),
        BarSpecification(minutes, BarAggregation.MINUTE, PriceType.LAST),
        AggregationSource.EXTERNAL,
    ))
    expected = expected_external_bar_type(instrument_id, minutes)
    if built != expected:
        raise RealT2IntegrationError("rc5 BarType differs from frozen Route A")
    return built


def _result_base(head: str | None, tree: str | None, start_ns: int | None) -> dict[str, object]:
    return {
        "schema_version": RESULT_SCHEMA,
        "task_id": REAL_T2_TASK_ID,
        "task_packet_sha256": TASK_PACKET_SHA256,
        "exact_head": head,
        "exact_tree": tree,
        "fixed_market_set_hash": PHASE0C_MARKET_SET_HASH,
        "clock_start_ns": start_ns,
        "cutoff_ns": None if start_ns is None else start_ns + REAL_T2_ACQUISITION_NS,
        "acquisition_seconds": REAL_T2_ACQUISITION_SECONDS,
        "target_count": 20,
        "public_data_only": True,
        "private_api": False,
        "signing": False,
        "exchange_write": False,
        "automatic_retry": False,
        "market_substitution": False,
        "cutoff_extension": False,
        "route_b_internal_aggregation": False,
        "project_1m_to_5m_aggregation": False,
        "formal_real_t2_credit": "NO",
        "g4_promotion": "NO",
    }


def run_single_attempt(*, evidence_root: Path, result_path: Path, expected_head: str) -> int:
    head: str | None = None
    tree: str | None = None
    start_ns: int | None = None
    node = None
    timer: threading.Timer | None = None
    try:
        assert_public_only(env=os.environ)
        assert_exact_nautilus_version()
        head, tree = _git_identity()
        if head != expected_head:
            raise RealT2IntegrationError("checked-out HEAD differs from authorized exact head")

        # Frozen clock rule: sample immediately before first outbound provider request.
        start_ns = time.time_ns()
        response = HyperliquidPublicClient().metadata_and_context_with_raw("")
        observed_ns = time.time_ns()
        if observed_ns < start_ns:
            raise RealT2IntegrationError("metadata observation precedes attempt clock")
        markets = materialize_fixed_markets_from_public_metadata(
            raw_response=response.raw_bytes,
            parsed_response=response.parsed,
            observed_at_ns=observed_ns,
        )
        expressions = tuple(item.expression for item in markets)
        snapshot = PitUniverseSnapshot.create(observed_at_ns=observed_ns, expressions=expressions)
        market_ids = [item.identity.market_id for item in markets]
        attempt_identity = {
            "task_id": REAL_T2_TASK_ID,
            "task_packet_sha256": TASK_PACKET_SHA256,
            "exact_head": head,
            "exact_tree": tree,
            "clock_start_ns": start_ns,
            "cutoff_ns": start_ns + REAL_T2_ACQUISITION_NS,
            "fixed_market_set_hash": PHASE0C_MARKET_SET_HASH,
            "ordered_market_ids": market_ids,
        }
        attempt_hash = sha256_hex(canonical_json_bytes(attempt_identity))
        manifest = RunManifest.create(
            run_id=f"task5d-real-t2-{attempt_hash[:24]}",
            git_sha=head,
            git_tree=tree,
            snapshot=snapshot,
            process_epoch=f"process-{attempt_hash[:24]}",
            continuity_epoch=f"continuity-{attempt_hash[:24]}",
            admission_epoch=f"admission-{attempt_hash[:24]}",
            capture_configuration={
                "mode": "TASK5D_REAL_T2_ROUTE_A_V1",
                "attempt_identity": attempt_identity,
                "attempt_hash": attempt_hash,
                "provider_native_5m_last_external": True,
                "provider_native_1m_restart_evidence": True,
                "run_seconds": REAL_T2_ACQUISITION_SECONDS,
                "one_livenode": True,
                "one_hyperliquid_data_client": True,
                "route_b_internal_aggregation": False,
                "project_1m_to_5m_aggregation": False,
            },
            subscription_policy={
                "discovery": market_ids,
                "watch": market_ids,
                "actionable": [],
            },
            trial_ledger_id="task5d-real-t2-prospective-v1",
        )
        evidence_root.mkdir(parents=True, exist_ok=True)
        (evidence_root / "provider-metaAndAssetCtxs.raw.json").write_bytes(response.raw_bytes)
        _write_json(evidence_root / "acquisition-plan.json", {
            "schema_version": "TASK5D_REAL_T2_ACQUISITION_PLAN_V1",
            "status": "FROZEN_BEFORE_PROVIDER_SUBSCRIPTIONS",
            "attempt_identity": attempt_identity,
            "attempt_hash": attempt_hash,
            "e4_run_manifest_hash": manifest.manifest_hash,
            "e4_pit_snapshot_hash": snapshot.snapshot_hash,
            "raw_provider_response_sha256": response.raw_sha256,
            "bar_route": "NAUTILUS_2.0.0rc5_HYPERLIQUID_5M_LAST_EXTERNAL",
            "restart_route": "NAUTILUS_2.0.0rc5_HYPERLIQUID_1M_LAST_EXTERNAL",
        })

        policy = SubscriptionPolicy(
            discovery=frozenset(market_ids),
            watch=frozenset(market_ids),
            actionable=frozenset(),
        )
        bar_types = tuple(
            bar_type
            for item in markets
            for bar_type in (
                _build_bar_type(item.identity.instrument_id, 1),
                _build_bar_type(item.identity.instrument_id, 5),
            )
        )
        node = build_public_data_node()
        strategy: NautilusE4CaptureStrategy = build_capture_strategy(
            manifest=manifest,
            snapshot=snapshot,
            policy=policy,
            bar_types=bar_types,
            evidence_root=evidence_root,
        )
        registry = {item.identity.market_id: item.registry_market for item in markets}
        coordinator = RealT2StrategyCoordinator(
            registry_markets=registry,
            open_structural_package=strategy.open_structural_package,
            clock_start_ns=start_ns,
            cutoff_ns=start_ns + REAL_T2_ACQUISITION_NS,
        )
        strategy.set_admitted_event_observer(coordinator.observe_admitted_event)
        node.add_strategy(strategy)

        remaining_ns = start_ns + REAL_T2_ACQUISITION_NS - time.time_ns()
        if remaining_ns <= 0:
            raise RealT2IntegrationError("fixed cutoff elapsed before provider subscriptions")
        timer = threading.Timer(remaining_ns / 1_000_000_000, node.handle().stop)
        timer.start()
        node.run()
        ended_ns = time.time_ns()
        if ended_ns > start_ns + REAL_T2_ACQUISITION_NS + 5_000_000_000:
            raise RealT2IntegrationError("attempt exceeded fixed cutoff shutdown tolerance")

        base = _result_base(head, tree, start_ns)
        focal = coordinator.focal
        if focal is None:
            _write_json(result_path, {
                **base,
                "RESULT": "NO_OPPORTUNITY",
                "terminal_state": "REAL_T2_SOURCE_ABSENT_OR_NOT_EVALUABLE",
                "formal_setup_count": 0,
                "focal_opportunity_switch": False,
            })
            return NOT_EVALUABLE

        # Structural source is the outcome-blind global minimum among all Formal Setups.
        structural_artifact = RoleBoundSourceArtifact.create(
            role=T2SourceRole.STRUCTURAL_SOURCE,
            name="focal-structural-source",
            exact_bytes=canonical_json_bytes(
                focal.structural.model_dump(mode="json")
            ),
        )
        structural_path = evidence_root / "focal-structural-source.json"
        structural_path.write_bytes(structural_artifact.exact_bytes())

        # Persist provider-native normalized metadata for every frozen market; absence
        # is NOT_EVALUABLE, never a default or reconstructed substitute.
        from nautilus_trader.model import CryptoPerpetual

        metadata_dir = evidence_root / "provider-instruments"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        metadata_names: list[str] = []
        metadata_documents: dict[str, bytes] = {}
        native_by_market: dict[str, CryptoPerpetual] = {}
        for item in markets:
            normalized = coordinator.provider_instruments.get(
                item.identity.market_id
            )
            if normalized is None:
                _write_json(result_path, {
                    **base,
                    "RESULT": "MISSING_PROVIDER_NATIVE_INSTRUMENT",
                    "terminal_state": (
                        "REAL_T2_SOURCE_ABSENT_OR_NOT_EVALUABLE"
                    ),
                    "market_id": item.identity.market_id,
                    "formal_setup_count": len(coordinator.observations),
                    "focal_key": focal.focal_key,
                })
                return NOT_EVALUABLE
            native = CryptoPerpetual.from_dict(normalized)
            native_by_market[item.identity.market_id] = native
            document = provider_instrument_metadata_document(
                raw_provider_response=response.raw_bytes,
                materialization=item,
                provider_instrument=native,
            )
            metadata_documents[item.identity.market_id] = document
            target = metadata_dir / (
                f"{item.identity.ordinal:02d}-"
                f"{item.identity.provider_coin}.json"
            )
            target.write_bytes(document)
            metadata_names.append(
                str(target.relative_to(evidence_root))
            )

        provider_wire_artifact = RoleBoundSourceArtifact.create(
            role=T2SourceRole.PROVIDER_INSTRUMENT_WIRE,
            name="provider-metaAndAssetCtxs-raw",
            exact_bytes=response.raw_bytes,
        )
        expression_artifacts = tuple(
            RoleBoundSourceArtifact.create(
                role=T2SourceRole.MARKET_EXPRESSION,
                name=f"market-expression-{item.identity.ordinal:02d}",
                exact_bytes=canonical_json_bytes(
                    item.expression.model_dump(mode="json")
                ),
            )
            for item in markets
        )
        registry_artifacts = tuple(
            RoleBoundSourceArtifact.create(
                role=T2SourceRole.REGISTRY_MARKET,
                name=f"registry-market-{item.identity.ordinal:02d}",
                exact_bytes=canonical_json_bytes(
                    item.registry_market.model_dump(mode="json")
                ),
            )
            for item in markets
        )
        metadata_artifacts = tuple(
            RoleBoundSourceArtifact.create(
                role=T2SourceRole.INSTRUMENT_METADATA,
                name=f"instrument-metadata-{item.identity.ordinal:02d}",
                exact_bytes=metadata_documents[
                    item.identity.market_id
                ],
                references=(
                    SourceReference(
                        role=provider_wire_artifact.role,
                        name=provider_wire_artifact.name,
                        artifact_hash=(
                            provider_wire_artifact.artifact_hash
                        ),
                    ),
                    SourceReference(
                        role=registry_artifacts[
                            item.identity.ordinal - 1
                        ].role,
                        name=registry_artifacts[
                            item.identity.ordinal - 1
                        ].name,
                        artifact_hash=registry_artifacts[
                            item.identity.ordinal - 1
                        ].artifact_hash,
                    ),
                ),
            )
            for item in markets
        )
        metadata_artifact_by_market = {
            item.identity.market_id: artifact
            for item, artifact in zip(
                markets, metadata_artifacts, strict=True
            )
        }
        e4_run_artifact = RoleBoundSourceArtifact.create(
            role=T2SourceRole.E4_RUN_MANIFEST,
            name="e4-run-manifest",
            exact_bytes=canonical_json_bytes(
                manifest.model_dump(mode="json")
            ),
        )
        e4_pit_artifact = RoleBoundSourceArtifact.create(
            role=T2SourceRole.E4_PIT_SNAPSHOT,
            name="e4-pit-snapshot",
            exact_bytes=canonical_json_bytes(
                snapshot.model_dump(mode="json")
            ),
        )
        e4_admission_artifacts = tuple(
            RoleBoundSourceArtifact.create(
                role=T2SourceRole.E4_ADMISSION,
                name=(
                    f"e4-admission-{event.admission_ordinal:09d}-"
                    f"{event.admission_hash[:12]}"
                ),
                exact_bytes=canonical_json_bytes(
                    event.model_dump(mode="json")
                ),
            )
            for event in coordinator.admissions
        )
        admission_artifact_by_hash = {
            event.admission_hash: artifact
            for event, artifact in zip(
                coordinator.admissions,
                e4_admission_artifacts,
                strict=True,
            )
        }

        side = position_side_for_focal(focal)
        # The coordinator froze this BBO synchronously at its admission.  Do not
        # derive entry/evaluation semantics from the complete cutoff-time stream.
        causal_bbo = coordinator.source_bound_bbo_for(focal)
        if causal_bbo is None:
            _write_json(result_path, {
                **base,
                "RESULT": "MISSING_CAUSAL_BBO",
                "terminal_state": (
                    "REAL_T2_SOURCE_ABSENT_OR_NOT_EVALUABLE"
                ),
                "formal_setup_count": len(coordinator.observations),
                "focal_key": focal.focal_key,
                "focal_market_id": focal.structural.market_id,
                "focal_formal_setup_id": (
                    focal.structural.formal_setup_id
                ),
                "focal_opportunity_switch": False,
                "candidate_switch": False,
            })
            return NOT_EVALUABLE
        bbo_artifact = admission_artifact_by_hash.get(
            causal_bbo.admission.admission_hash
        )
        if bbo_artifact is None:
            raise RealT2IntegrationError(
                "causal BBO admission artifact is absent"
            )

        prospective = frozen_task5d_prospective_candidate()
        prospective_artifact = RoleBoundSourceArtifact.create(
            role=(
                T2SourceRole.PROSPECTIVE_ECONOMIC_CANDIDATE_IDENTITY
            ),
            name="prospective-economic-candidate",
            exact_bytes=canonical_json_bytes(
                prospective.model_dump(mode="json")
            ),
        )
        selected = prospective.materialize_candidate_manifest(
            structural_component_manifest_hash=(
                structural_artifact.artifact_hash
            )
        )
        selected_artifact = RoleBoundSourceArtifact.create(
            role=T2SourceRole.SELECTED_CANDIDATE,
            name="selected-candidate",
            exact_bytes=canonical_json_bytes(
                selected.model_dump(mode="json")
            ),
            references=(
                SourceReference(
                    role=prospective_artifact.role,
                    name=prospective_artifact.name,
                    artifact_hash=prospective_artifact.artifact_hash,
                ),
            ),
        )
        g4_manifest = materialize_task5d_g4_manifest(
            exact_source_git_head=head,
            exact_source_git_tree=tree,
            e4_manifest_hash=manifest.manifest_hash,
            pit_snapshot_hash=snapshot.snapshot_hash,
            structural_artifact=structural_artifact,
            candidate=selected,
            e4_admission_artifacts=e4_admission_artifacts,
        )
        g4_artifact = RoleBoundSourceArtifact.create(
            role=T2SourceRole.G4_RUN_MANIFEST,
            name="g4-run-manifest",
            exact_bytes=canonical_json_bytes(
                g4_manifest.model_dump(mode="json")
            ),
        )
        focal_market = next(
            item
            for item in markets
            if item.identity.market_id == focal.structural.market_id
        )
        focal_metadata_artifact = metadata_artifact_by_market[
            focal.structural.market_id
        ]
        focal_native = native_by_market[
            focal.structural.market_id
        ]
        try:
            validation = materialize_task5d_validation_source(
                clock_start_ns=start_ns,
                exact_source_git_head=head,
                exact_source_git_tree=tree,
                focal=focal,
                side=side,
                causal_bbo=causal_bbo,
                provider_instrument=focal_native,
                registry_market=focal_market.registry_market,
                instrument_metadata_version=(
                    focal_market.expression.instrument_metadata_version
                ),
                instrument_metadata_artifact=(
                    focal_metadata_artifact
                ),
                e4_admission_artifact=bbo_artifact,
                prospective_candidate_artifact=(
                    prospective_artifact
                ),
                prospective_candidate=prospective,
                g4_run_manifest_artifact=g4_artifact,
                g4_run_manifest=g4_manifest,
            )
        except RealT2IntegrationError as exc:
            _write_json(result_path, {
                **base,
                "RESULT": "VALIDATION_SOURCE_NOT_EVALUABLE",
                "terminal_state": (
                    "REAL_T2_SOURCE_ABSENT_OR_NOT_EVALUABLE"
                ),
                "reason": str(exc),
                "formal_setup_count": len(coordinator.observations),
                "focal_key": focal.focal_key,
                "focal_market_id": focal.structural.market_id,
                "focal_formal_setup_id": (
                    focal.structural.formal_setup_id
                ),
                "focal_bbo_admission_hash": (
                    causal_bbo.admission.admission_hash
                ),
                "focal_opportunity_switch": False,
                "candidate_switch": False,
            })
            return NOT_EVALUABLE

        prefix = tuple(
            event
            for event in coordinator.admissions
            if event.admission_ordinal <= causal_bbo.admission.admission_ordinal
        )
        restart_source = derive_restart_pivot_source(
            admissions=prefix,
            focal=focal,
            side=side,
        )
        if restart_source is None:
            raise RealT2IntegrationError("causal restart source is not evaluable")
        restart_source_artifact = RoleBoundSourceArtifact.create(
            role=T2SourceRole.RESTART_REFERENCE_SOURCE,
            name="causal-restart-source",
            exact_bytes=restart_source.source_bytes,
            references=(_reference(bbo_artifact),),
        )
        lineage = CausalLineage.create(
            source_e4_manifest_hash=manifest.manifest_hash,
            source_pit_snapshot_hash=snapshot.snapshot_hash,
            source_structural_artifact_hash=structural_artifact.artifact_hash,
            structural_component_manifest_hash=structural_artifact.artifact_hash,
            market_id=focal.structural.market_id,
            instrument_id=causal_bbo.admission.source.instrument_id,
            formal_setup_id=focal.structural.formal_setup_id,
            formal_setup_admission_ordinal=(
                focal.structural.formal_setup_admission_ordinal
            ),
            formal_setup_admission_ts=focal.structural.formal_setup_admission_ts,
            thesis_id=focal.thesis_id,
            activation_sequence_id=focal.package_id,
            attempt_lineage_id=f"attempt-{causal_bbo.admission.admission_hash[:24]}",
            restart_reference_id=restart_source.restart_reference_id,
            continuity_epoch=focal.continuity_epoch,
            admission_epoch=focal.admission_epoch,
            instrument_metadata_version=(
                focal_market.expression.instrument_metadata_version
            ),
            instrument_metadata_hash=focal_metadata_artifact.artifact_hash,
            validation_reference_id=(
                validation.validation_reference.validation_reference_id
            ),
            validation_reference_hash=validation.validation_reference.reference_hash,
        )
        lineage_artifact = RoleBoundSourceArtifact.create(
            role=T2SourceRole.CAUSAL_LINEAGE,
            name="focal-causal-lineage",
            exact_bytes=canonical_json_bytes(lineage.model_dump(mode="json")),
            references=(
                _reference(structural_artifact),
                _reference(restart_source_artifact),
                _reference(validation.validation_reference_artifact),
            ),
        )
        restart = materialize_restart_reference(
            source=restart_source,
            lineage=lineage,
            source_artifact_hash=restart_source_artifact.artifact_hash,
        )
        restart_artifact = RoleBoundSourceArtifact.create(
            role=T2SourceRole.RESTART_REFERENCE,
            name="causal-restart-reference",
            exact_bytes=canonical_json_bytes(restart.model_dump(mode="json")),
            references=(
                _reference(restart_source_artifact),
                _reference(lineage_artifact),
            ),
        )
        supplement_source = derive_evaluator_supplement_source(
            admissions=prefix,
            lineage=lineage,
            side=side,
        )
        if supplement_source is None:
            raise RealT2IntegrationError("causal evaluator supplement is not evaluable")
        supplement_source_artifact = RoleBoundSourceArtifact.create(
            role=T2SourceRole.EVALUATOR_SUPPLEMENT_SOURCE,
            name="causal-evaluator-supplement-source",
            exact_bytes=supplement_source.source_bytes,
            references=(_reference(lineage_artifact),),
        )
        supplement = materialize_evaluator_supplement(
            source=supplement_source,
            lineage=lineage,
            source_artifact_hash=supplement_source_artifact.artifact_hash,
        )
        supplement_artifact = RoleBoundSourceArtifact.create(
            role=T2SourceRole.EVALUATOR_SUPPLEMENT,
            name="causal-evaluator-supplement",
            exact_bytes=canonical_json_bytes(supplement.model_dump(mode="json")),
            references=(
                _reference(lineage_artifact),
                _reference(supplement_source_artifact),
            ),
        )
        lifecycle_records = strategy.capture_session.lifecycle_records
        lifecycle_artifacts = tuple(
            RoleBoundSourceArtifact.create(
                role=T2SourceRole.E4_LIFECYCLE,
                name=f"e4-lifecycle-{index:06d}",
                exact_bytes=canonical_json_bytes(record.model_dump(mode="json")),
            )
            for index, record in enumerate(lifecycle_records, 1)
        )
        if not lifecycle_artifacts:
            raise RealT2IntegrationError("E4 lifecycle source is absent")
        continuity_artifact = RoleBoundSourceArtifact.create(
            role=T2SourceRole.E4_CONTINUITY,
            name="e4-capture-health-and-checkpoint",
            exact_bytes=canonical_json_bytes(strategy.capture_health),
            references=tuple(_reference(item) for item in lifecycle_artifacts),
        )
        intent_admission = admit_hypothetical_order_intent(
            strategy_decision_id=structural_artifact.artifact_hash,
            candidate_hash=selected.candidate_hash,
            side=side,
            lineage=lineage,
            current_bbo=causal_bbo.admission,
            technical_quantity=Decimal(str(focal_native.size_increment)),
            size_decimals=int(focal_native.size_precision),
            activation_reference_hash=restart.reference_hash,
            validation=validation.validation_reference,
        )
        if intent_admission.intent is None:
            raise RealT2IntegrationError("canonical entry intent is not evaluable")
        intent = intent_admission.intent
        projection = project_native_replay(
            events=tuple(coordinator.admissions),
            market_id=focal.structural.market_id,
            expression_id=focal_market.expression.expression_id,
            instrument_id=focal.structural.instrument_id,
        )
        exit_trigger = select_first_exit_trigger(
            admissions=coordinator.admissions,
            focal=focal,
            side=side,
            entry_binding=causal_bbo,
            entry_executable_price=intent.executable_price,
            candidate=selected.config,
        )
        if exit_trigger is None:
            raise RealT2IntegrationError("no causal exit trigger exists before cutoff")
        round_trip = execute_provider_native_round_trip_state(
            projection=projection,
            intent=intent,
            entry_trigger_admission_hash=causal_bbo.admission.admission_hash,
            exit_trigger_admission_hash=exit_trigger.admission.admission_hash,
            provider_instrument=focal_native,
            catalog_path=evidence_root / "provider-round-trip-catalog",
        ).record
        entry_fill = Decimal(round_trip.entry.fill.last_px)
        exit_fill = Decimal(round_trip.exit.fill.last_px)
        entry_adverse = (
            max(Decimal("0"), entry_fill - intent.executable_price)
            if side.value == "LONG"
            else max(Decimal("0"), intent.executable_price - entry_fill)
        ) / intent.executable_price * Decimal("10000")
        exit_adverse = (
            max(Decimal("0"), exit_trigger.executable_price - exit_fill)
            if side.value == "LONG"
            else max(Decimal("0"), exit_fill - exit_trigger.executable_price)
        ) / exit_trigger.executable_price * Decimal("10000")
        round_trip_payload = round_trip.model_dump(mode="json")
        fee_artifact, fee = _cost_source(
            name="modelled-two-leg-fee",
            payload={
                "validation_reference_hash": validation.validation_reference.reference_hash,
                "round_trip": round_trip_payload,
                "entry_fee_bps": "4.5",
                "exit_fee_bps": "4.5",
            },
            provenance=CostProvenance.MODELLED,
            amount_bps=Decimal("9.0"),
        )
        spread_artifact, spread = _cost_source(
            name="executable-bbo-crossing",
            payload={"entry_bbo": causal_bbo.admission.admission_hash, "exit_bbo": exit_trigger.admission.admission_hash, "round_trip": round_trip_payload},
            provenance=CostProvenance.NOT_APPLICABLE,
            amount_bps=None,
        )
        slippage_total = entry_adverse + exit_adverse
        slippage_artifact, slippage = _cost_source(
            name="two-leg-provider-fill-slippage",
            payload={"entry_reference": str(intent.executable_price), "exit_reference": str(exit_trigger.executable_price), "round_trip": round_trip_payload},
            provenance=(CostProvenance.PROVEN_ZERO if slippage_total == 0 else CostProvenance.MODELLED),
            amount_bps=slippage_total,
        )
        impact_artifact, impact = _cost_source(
            name="exact-l1-size-and-flat-state",
            payload={"entry_bbo": causal_bbo.admission.admission_hash, "exit_bbo": exit_trigger.admission.admission_hash, "round_trip": round_trip_payload},
            provenance=CostProvenance.PROVEN_ZERO,
            amount_bps=Decimal("0"),
        )
        shortfall_artifact, shortfall = _cost_source(
            name="entry-provider-fill-shortfall",
            payload={"entry_reference": str(intent.executable_price), "entry_fill": str(entry_fill), "round_trip": round_trip_payload},
            provenance=(CostProvenance.PROVEN_ZERO if entry_adverse == 0 else CostProvenance.MODELLED),
            amount_bps=entry_adverse,
        )
        funding_response = HyperliquidPublicClient().funding_history_with_raw(
            coin=focal_market.identity.provider_coin,
            start_ms=(round_trip.entry.fill.ts_event + 999_999) // 1_000_000,
            end_ms=round_trip.exit.fill.ts_event // 1_000_000,
        )
        funding_assessment = assess_public_funding_history(
            raw_response=funding_response.raw_bytes,
            parsed_response=funding_response.parsed,
            coin=focal_market.identity.provider_coin,
            start_time_ms=(round_trip.entry.fill.ts_event + 999_999) // 1_000_000,
            end_time_ms=round_trip.exit.fill.ts_event // 1_000_000,
        )
        if funding_assessment.state != "NOT_APPLICABLE":
            raise RealT2IntegrationError(funding_assessment.reason)
        funding_artifact = RoleBoundSourceArtifact.create(
            role=T2SourceRole.COST_SOURCE,
            name="exact-public-funding-interval",
            exact_bytes=funding_response.raw_bytes,
        )
        funding = CostComponent(
            provenance=CostProvenance.NOT_APPLICABLE,
            source_hash=funding_artifact.artifact_hash,
        )
        outcome = ThesisOutcome(
            thesis_id=lineage.thesis_id,
            market_id=lineage.market_id,
            provider_state_source_hash=provider_round_trip_state_semantic_source_hash(round_trip),
            order_intent_hash=intent.order_intent_hash,
            decision="TAKE",
            attempt_count=1,
            fee=fee,
            spread=spread,
            slippage=slippage,
            impact_size_feasibility=impact,
            funding=funding,
            implementation_shortfall=shortfall,
        )
        outcome_artifact = RoleBoundSourceArtifact.create(
            role=T2SourceRole.THESIS_OUTCOME,
            name="focal-round-trip-thesis-outcome",
            exact_bytes=canonical_json_bytes(outcome.model_dump(mode="json")),
            references=(
                _reference(lineage_artifact),
                _reference(validation.validation_reference_artifact),
                *tuple(_reference(item) for item in (fee_artifact, spread_artifact, slippage_artifact, impact_artifact, funding_artifact, shortfall_artifact)),
            ),
        )
        source_artifacts = (
            e4_run_artifact,
            e4_pit_artifact,
            *lifecycle_artifacts,
            continuity_artifact,
            structural_artifact,
            prospective_artifact,
            lineage_artifact,
            restart_source_artifact,
            restart_artifact,
            supplement_source_artifact,
            supplement_artifact,
            selected_artifact,
            g4_artifact,
            provider_wire_artifact,
            *expression_artifacts,
            *registry_artifacts,
            *metadata_artifacts,
            *e4_admission_artifacts,
            validation.validation_source_artifact,
            validation.validation_reference_artifact,
            fee_artifact,
            spread_artifact,
            slippage_artifact,
            impact_artifact,
            funding_artifact,
            shortfall_artifact,
            outcome_artifact,
        )
        source_role_dir = evidence_root / "source-roles"
        source_role_dir.mkdir(parents=True, exist_ok=True)
        source_role_names: list[str] = []
        for artifact in source_artifacts:
            target = source_role_dir / (
                f"{artifact.role.value}--{artifact.name}.json"
            )
            _write_json(
                target, artifact.model_dump(mode="json")
            )
            source_role_names.append(
                str(target.relative_to(evidence_root))
            )

        required_root_roles = {
            role.value for role in T2SourceRole
        }
        materialized_roles = {
            artifact.role.value for artifact in source_artifacts
        }
        missing_roles = sorted(
            required_root_roles - materialized_roles
        )
        if missing_roles:
            raise RealT2IntegrationError(
                f"Rooted-T2 source roles remain incomplete: {missing_roles}"
            )
        acquisition_plan_hash = sha256_hex(
            (evidence_root / "acquisition-plan.json").read_bytes()
        )
        root = assemble_real_t2_root(
            artifacts=source_artifacts,
            governance_epoch=GOVERNANCE_EPOCH,
            acquisition_plan_hash=acquisition_plan_hash,
            exact_source_git_head=head,
            exact_source_git_tree=tree,
            strategy_package_identity=coordinator.package_manifest.manifest_hash,
        )
        _write_json(
            evidence_root / "rooted-t2-source-root.json",
            root.model_dump(mode="json"),
        )
        _write_json(result_path, {
            **base,
            "RESULT": "VALIDATION_SOURCE_MATERIALIZED",
            "terminal_state": (
                "ROOT_MATERIALIZATION_MISSING_EXACT_SOURCE_ROLES"
                if missing_roles
                else "ROOT_SOURCE_ROLES_COMPLETE"
            ),
            "formal_setup_count": len(coordinator.observations),
            "focal_key": focal.focal_key,
            "focal_market_id": focal.structural.market_id,
            "focal_formal_setup_id": (
                focal.structural.formal_setup_id
            ),
            "focal_structural_source": structural_path.name,
            "focal_bbo_admission_hash": (
                causal_bbo.admission.admission_hash
            ),
            "provider_instrument_metadata": metadata_names,
            "source_role_artifacts": source_role_names,
            "validation_source_artifact_hash": (
                validation.validation_source_artifact.artifact_hash
            ),
            "validation_reference_hash": (
                validation.validation_reference.reference_hash
            ),
            "validation_fully_materialized": (
                validation.validation_reference.fully_materialized
            ),
            "rooted_t2_source_root_hash": root.source_root_hash,
            "round_trip_evidence_hash": round_trip.evidence_hash,
            "round_trip_orders": round_trip.submitted_order_count,
            "round_trip_fills": round_trip.fill_count,
            "round_trip_terminal_flat": (
                round_trip.open_position_count == 0
            ),
            "fee_control_bps_one_way": "4.5",
            "round_trip_technical_fee_control_bps": "9.0",
            "actual_user_fee_rate_claim": False,
            "spread_separate_debit": (
                "NOT_APPLICABLE_EXECUTABLE_BBO_EMBEDS_CROSSING"
            ),
            "slippage_zero_scope": "CONTROL_ONLY",
            "latency_ms": "0",
            "latency_evidence_role": "CONTROL_ONLY",
            "missing_root_roles": missing_roles,
            "focal_opportunity_switch": False,
            "candidate_switch": False,
        })
        return NOT_EVALUABLE if missing_roles else 0
    except Exception as exc:
        _write_json(result_path, {
            **_result_base(head, tree, start_ns),
            "RESULT": "APPLICATION_OR_PROVIDER_RUNTIME_FAILURE",
            "terminal_state": "ATTEMPT_FAILED_NO_AUTOMATIC_RETRY",
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        return APPLICATION_FAILURE
    finally:
        if timer is not None:
            timer.cancel()
        if node is not None:
            node.dispose()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    if not _GIT_OID.fullmatch(args.expected_head):
        raise SystemExit("--expected-head must be one full Git OID")
    return run_single_attempt(
        evidence_root=args.evidence_root,
        result_path=args.result_path,
        expected_head=args.expected_head,
    )


if __name__ == "__main__":
    raise SystemExit(main())
