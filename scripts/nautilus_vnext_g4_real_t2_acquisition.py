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
    materialize_fixed_markets_from_public_metadata,
    provider_instrument_metadata_document,
)

_GIT_OID = re.compile(r"^[0-9a-f]{40}$")
TASK_PACKET_SHA256 = "7688773c709ba2fa69999e5703c575541a90425ab6b1c49dbe8d9fc91fe6ded4"
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
        structural_path = evidence_root / "focal-structural-source.json"
        structural_path.write_text(focal.structural.model_dump_json(), encoding="utf-8")

        # Persist provider-native normalized metadata for every frozen market; absence
        # is NOT_EVALUABLE, never a default or reconstructed substitute.
        from nautilus_trader.model import CryptoPerpetual
        metadata_dir = evidence_root / "provider-instruments"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        metadata_names: list[str] = []
        for item in markets:
            normalized = coordinator.provider_instruments.get(item.identity.market_id)
            if normalized is None:
                _write_json(result_path, {
                    **base,
                    "RESULT": "MISSING_PROVIDER_NATIVE_INSTRUMENT",
                    "terminal_state": "REAL_T2_SOURCE_ABSENT_OR_NOT_EVALUABLE",
                    "market_id": item.identity.market_id,
                    "formal_setup_count": len(coordinator.observations),
                    "focal_key": focal.focal_key,
                })
                return NOT_EVALUABLE
            native = CryptoPerpetual.from_dict(normalized)
            document = provider_instrument_metadata_document(
                raw_provider_response=response.raw_bytes,
                materialization=item,
                provider_instrument=native,
            )
            target = metadata_dir / f"{item.identity.ordinal:02d}-{item.identity.provider_coin}.json"
            target.write_bytes(document)
            metadata_names.append(str(target.relative_to(evidence_root)))

        # Exact Validation/cost/G4 participation roles are intentionally never guessed.
        # The source-root assembler in t2_acquisition accepts them only after exact
        # existing owners have materialized every required source role.
        _write_json(result_path, {
            **base,
            "RESULT": "FOCAL_SOURCE_CAPTURED",
            "terminal_state": "ROOT_MATERIALIZATION_REQUIRES_EXACT_SOURCE_ROLES",
            "formal_setup_count": len(coordinator.observations),
            "focal_key": focal.focal_key,
            "focal_market_id": focal.structural.market_id,
            "focal_formal_setup_id": focal.structural.formal_setup_id,
            "focal_structural_source": structural_path.name,
            "provider_instrument_metadata": metadata_names,
            "focal_opportunity_switch": False,
            "candidate_switch": False,
        })
        return NOT_EVALUABLE
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
