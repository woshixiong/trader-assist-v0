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
    PHASE0C_MARKET_SET_HASH,
    REAL_T2_ACQUISITION_NS,
    REAL_T2_ACQUISITION_SECONDS,
    REAL_T2_TASK_ID,
    RealT2IntegrationError,
    RealT2StrategyCoordinator,
    expected_external_bar_type,
    frozen_task5d_prospective_candidate,
    materialize_fixed_markets_from_public_metadata,
    materialize_task5d_g4_manifest,
    materialize_task5d_validation_source,
    position_side_for_focal,
    provider_instrument_metadata_document,
    select_focal_causal_bbo,
)
from trader_assist_v0.nautilus_g4.t2_shadow import (
    RoleBoundSourceArtifact,
    SourceReference,
    T2SourceRole,
)

_GIT_OID = re.compile(r"^[0-9a-f]{40}$")
TASK_PACKET_SHA256 = "9be069776518f311872e0e1cde25efc74a6f1a4f97726a1f36ab4ef865107250"
RESULT_SCHEMA = "TASK5D_REAL_T2_ACQUISITION_RESULT_V1"
NOT_EVALUABLE = 2
APPLICATION_FAILURE = 3


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
        causal_bbo = select_focal_causal_bbo(
            admissions=coordinator.admissions,
            focal=focal,
            side=side,
        )
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

        source_artifacts = (
            e4_run_artifact,
            e4_pit_artifact,
            structural_artifact,
            prospective_artifact,
            selected_artifact,
            g4_artifact,
            provider_wire_artifact,
            *expression_artifacts,
            *registry_artifacts,
            *metadata_artifacts,
            *e4_admission_artifacts,
            validation.validation_source_artifact,
            validation.validation_reference_artifact,
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
