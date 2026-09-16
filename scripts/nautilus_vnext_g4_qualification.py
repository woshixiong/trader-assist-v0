# mypy: disable-error-code="import-not-found"
"""Bounded exact-rc5 Ordinary VNext G4 technical qualification.

This script consumes accepted-format E4 evidence as immutable source authority,
constructs only rebuildable derived-cache identity, exercises the pure VNext policy
on a 20-market representative mechanics topology, and proves isolated Nautilus
simulation contexts. It does not submit or authorize any order.
"""

from __future__ import annotations

import argparse
import os
from decimal import Decimal
from pathlib import Path

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_e4.safety import assert_public_only
from trader_assist_v0.nautilus_e4.storage import EvidenceStore
from trader_assist_v0.nautilus_g4.catalog_bridge import (
    bind_e4_source,
    build_empty_provider_catalog,
)
from trader_assist_v0.nautilus_g4.runner import (
    assert_exact_rc5,
    build_isolated_candidate_contexts,
    dispose_candidate_contexts,
)
from trader_assist_v0.nautilus_pilot.strategy_package import StrategyPackageManifest
from trader_assist_v0.vnext_g4.contracts import (
    AttemptPolicy,
    EntryActivation,
    ExecutionModelConfig,
    ExitPolicy,
    G4RunManifest,
    ReentryPolicy,
    VNextCandidateConfig,
    VNextFeatureSnapshot,
    WinnerConfirmation,
)
from trader_assist_v0.vnext_g4.evaluator import evaluate_vnext
from trader_assist_v0.vnext_g4.reporting import build_report

PASS = 0
FAIL = 3


def _candidate(candidate_id: str, hurdle: int) -> VNextCandidateConfig:
    return VNextCandidateConfig.create(
        candidate_id=candidate_id,
        entry_activation=EntryActivation.EA0_FORMAL_TIME_CONTROL,
        attempt_policy=AttemptPolicy.AP1_FIXED_BPS,
        reentry_policy=ReentryPolicy.R1_ONE_FRESH_CAUSAL_ACTIVATION,
        winner_confirmation=WinnerConfirmation.WC0_PROGRESS,
        exit_policy=ExitPolicy.X1_STRUCTURAL_FULL_EXIT,
        room_to_cost_hurdle=hurdle,
        fixed_stop_bps=8,
        rv_multiplier=None,
        no_followthrough_seconds=None,
        winner_progress_bps=5,
        winner_persistence_seconds=None,
        giveback_numerator=None,
        giveback_denominator=None,
    )


def _feature(
    candidate: VNextCandidateConfig,
    index: int,
    source_manifest_hash: str,
) -> VNextFeatureSnapshot:
    return VNextFeatureSnapshot.create(
        market_id=sha256_hex(f"VNEXT-G4-SCALE-{index:02d}".encode()),
        expression_id=f"g4-scale-expr-{index:02d}",
        package_id=f"g4-scale-pkg-{candidate.candidate_id}-{index:02d}",
        candidate_hash=candidate.candidate_hash,
        source_e4_manifest_hash=source_manifest_hash,
        admission_ordinal=index + 1,
        decision_ts=1_000_000_000 + index,
        side="LONG" if index % 2 == 0 else "SHORT",
        structural_setup_confirmed=True,
        thesis_valid=True,
        data_evaluable=True,
        bbo_state_valid=True,
        predecision_window_complete=True,
        ea1_direct_reaccel=True,
        ea2_retest_reaccel=False,
        flow_imbalance_side_adjusted=Decimal("0.25"),
        flow_price_response_bps=Decimal("1"),
        remaining_room_bps=Decimal("12"),
        all_in_friction_bps=Decimal("2"),
        intended_notional=Decimal("100"),
        top_level_notional=Decimal("1000"),
        attempt_number=1,
        adverse_progress_bps=Decimal("1"),
        micro_rv_60s_bps=Decimal("8"),
        elapsed_attempt_seconds=15,
        no_followthrough_state=False,
        fresh_reentry_activation=False,
        favorable_progress_bps=Decimal("5"),
        favorable_persistence_seconds=60,
        fresh_favorable_structure=True,
        structural_stop_reached=False,
        structural_exit_reached=False,
        fixed_r_exit_reached=False,
        current_net_progress_bps=Decimal("5"),
        net_mfe_bps=Decimal("5"),
    )


def _write_result(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_json_bytes(payload) + b"\n"
    path.write_bytes(encoded)
    print(encoded.decode().strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-path", type=Path, required=True)
    parser.add_argument("--derived-cache-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path, required=True)
    parser.add_argument("--exact-head", required=True)
    parser.add_argument("--exact-tree", required=True)
    args = parser.parse_args()

    try:
        if len(args.exact_head) != 40 or len(args.exact_tree) != 40:
            raise ValueError("exact head/tree must be 40-character Git object identities")
        zero_write = assert_public_only(env=os.environ)
        assert_exact_rc5()
        source_store = EvidenceStore(args.evidence_path)
        source_manifest = source_store.load_manifest()
        source_hashes_before = source_store.artifact_hashes()

        binding = bind_e4_source(
            evidence_root=args.evidence_path,
            cache_root=args.derived_cache_path,
            expected_manifest_hash=source_manifest.manifest_hash,
        )
        catalog = build_empty_provider_catalog(binding)
        assert catalog is not None

        execution = ExecutionModelConfig.create()
        candidates = (
            _candidate("ordinary-vnext-g4-reference", 3),
            _candidate("ordinary-vnext-g4-hurdle-control", 4),
        )
        contexts = build_isolated_candidate_contexts(
            candidates=candidates,
            execution=execution,
        )
        try:
            structural = StrategyPackageManifest.create(trade_os_release_sha=args.exact_head)
            g4_manifest = G4RunManifest.create(
                run_id=f"g4-qualification-{args.exact_head[:12]}",
                git_sha=args.exact_head,
                git_tree=args.exact_tree,
                source_e4_manifest_hash=source_manifest.manifest_hash,
                source_pit_snapshot_hash=source_manifest.pit_snapshot_hash,
                source_artifact_hashes=binding.source_artifact_hashes,
                structural_component_manifest_hash=structural.manifest_hash,
                candidate_hash=candidates[0].candidate_hash,
                execution_model_hash=execution.config_hash,
                trial_ledger_id="g4-qualification-trial-v1",
                evidence_cutoff_id="g4-qualification-cutoff-v1",
            )
            evaluations = tuple(
                evaluate_vnext(
                    candidates[0],
                    _feature(candidates[0], index, source_manifest.manifest_hash),
                )
                for index in range(20)
            )
            report = build_report(
                candidate_hash=candidates[0].candidate_hash,
                evaluations=evaluations,
                outcomes=(),
            )
            if report.evaluation_count != 20:
                raise AssertionError("representative mechanics topology did not retain 20 markets")
            if report.denominator["TAKE"] != 20:
                raise AssertionError(
                    "representative mechanics topology did not evaluate deterministically"
                )
            if any(item.order_intent != "MARKETABLE_ENTRY" for item in evaluations):
                raise AssertionError("unexpected hypothetical order-intent semantics")

            replay = tuple(
                evaluate_vnext(
                    candidates[0],
                    _feature(candidates[0], index, source_manifest.manifest_hash),
                )
                for index in range(20)
            )
            if tuple(item.record_hash for item in replay) != tuple(
                item.record_hash for item in evaluations
            ):
                raise AssertionError("same manifest/input did not reproduce evaluation identities")
            if len({id(item.node) for item in contexts}) != len(contexts):
                raise AssertionError("candidate Nautilus nodes are not isolated")

            source_hashes_after = source_store.artifact_hashes()
            if source_hashes_before != source_hashes_after:
                raise AssertionError("G4 qualification mutated accepted E4 source evidence")

            result: dict[str, object] = {
                "schema_version": "VNEXT_G4_QUALIFICATION_RESULT_V1",
                "status": "PASS",
                "exact_head": args.exact_head,
                "exact_tree": args.exact_tree,
                "nautilus_version": "2.0.0rc5",
                "g4_manifest_hash": g4_manifest.manifest_hash,
                "source_e4_manifest_hash": source_manifest.manifest_hash,
                "source_pit_snapshot_hash": source_manifest.pit_snapshot_hash,
                "source_artifact_set_hash": binding.source_artifact_set_hash,
                "derived_catalog_rebuildable": binding.rebuildable,
                "derived_catalog_authoritative_market_truth": binding.authoritative_market_truth,
                "candidate_contexts": len(contexts),
                "candidate_state_isolated": True,
                "representative_market_count": report.evaluation_count,
                "representative_scale_role": "TECHNICAL_MECHANICS_ONLY",
                "strategy_edge_claim": False,
                "pre_e5_confirmatory_evidence_open": False,
                "source_e4_evidence_mutated": False,
                "execution_model_hash": execution.config_hash,
                "implicit_fill_defaults": False,
                "passive_touch_is_fill": execution.passive_touch_is_fill,
                "trigger_price_is_fill": execution.trigger_price_is_fill,
                "l1_size_feasibility_required": execution.l1_size_feasibility_required,
                "zero_write_proof": zero_write.model_dump(mode="json"),
            }
        finally:
            dispose_candidate_contexts(contexts)
    except Exception as exc:
        _write_result(
            args.result_path,
            {
                "schema_version": "VNEXT_G4_QUALIFICATION_RESULT_V1",
                "status": "APPLICATION_FAILURE",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "strategy_edge_claim": False,
                "pre_e5_confirmatory_evidence_open": False,
                "exchange_write": False,
            },
        )
        return FAIL

    _write_result(args.result_path, result)
    return PASS


if __name__ == "__main__":
    raise SystemExit(main())
