#!/usr/bin/env python3
# mypy: disable-error-code="import-not-found"
"""Bounded exact-rc5 Ordinary VNext G4 infrastructure qualification.

T0 controls qualify serializer/provider mechanics only. Formal causal claims
remain NOT_PROVEN unless a future accepted T2 artifact is explicitly consumed.
"""

from __future__ import annotations

import argparse
import json
import os
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_e4.contracts import (
    AdmittedEvent,
    DataKind,
    EvidenceState,
    SourceEvent,
)
from trader_assist_v0.nautilus_g4.catalog_bridge import build_replay_payload
from trader_assist_v0.nautilus_g4.runner import (
    RepresentativeMarketEvidence,
    assert_actual_representative_scale,
    assert_backtest_node_catalog_surface,
    assert_exact_nautilus_rc5,
    build_fill_model,
    candidate_state_isolation_plan,
    causal_claim_gate_states,
    formal_g4_acceptance,
    new_isolated_backtest_engine,
    project_provider_native_state,
)
from trader_assist_v0.vnext_g4.contracts import (
    AttemptStop,
    CandidateConfig,
    CandidateManifest,
    EntryActivation,
    EvidenceArtifactHash,
    ExecutionModelConfig,
    ExitPolicy,
    G4RunManifest,
    OrderPrimitive,
    ReentryPolicy,
    WinnerConfirmation,
)

STRUCTURAL_HASH = "a" * 64
CONTROL_MARKET = "b" * 64
REPRESENTATIVE_MARKET_FLOOR = 20


def _candidate(candidate_id: str = "qualification-reference") -> CandidateManifest:
    return CandidateManifest.create(
        candidate_id=candidate_id,
        structural_component_manifest_hash=STRUCTURAL_HASH,
        config=CandidateConfig(
            entry_activation=EntryActivation.EA1,
            attempt_stop=AttemptStop.AP0,
            room_to_cost_k=Decimal("2"),
            reentry_policy=ReentryPolicy.NO_REENTRY_REFERENCE,
            winner_confirmation=WinnerConfirmation.WC0,
            winner_progress_bps=Decimal("3"),
            exit_policy=ExitPolicy.X1,
            comparison_role=(
                "REFERENCE" if candidate_id.endswith("reference") else "CHALLENGER"
            ),
        ),
    )


def _execution() -> ExecutionModelConfig:
    return ExecutionModelConfig(
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


def _admitted(ordinal: int) -> AdmittedEvent:
    source = SourceEvent.create(
        market_id=CONTROL_MARKET,
        expression_id="formal-g4-control",
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id="ETH-USD-PERP.HYPERLIQUID",
        data_kind=DataKind.BAR,
        source_event_id=f"formal-g4-control-{ordinal}",
        native_trade_id=None,
        provider_aggressor_side=None,
        event_context="T0_SYNTHETIC_CONTROL",
        ts_event=ordinal * 10,
        ts_init=ordinal * 10 + 1,
        true_network_receive_ts=None,
        payload={"close": str(100 + ordinal)},
    )
    return AdmittedEvent.create(
        schema_version="E4_CAPTURE_V1",
        process_epoch="formal-g4-process",
        continuity_epoch="formal-g4-continuity",
        admission_epoch="formal-g4-admission",
        admission_ordinal=ordinal,
        admission_ts=ordinal * 10 + 2,
        source_identity=source.replay_identity,
        out_of_order=False,
        continuity_state=EvidenceState.COMPLETE,
        source=source,
    )


def _t0_serializer_probe() -> dict[str, object]:
    events = (_admitted(1), _admitted(2))
    payload = build_replay_payload(events)
    restarted = tuple(
        AdmittedEvent.model_validate_json(event.model_dump_json()) for event in events
    )
    restarted_payload = build_replay_payload(restarted)
    if payload != restarted_payload:
        raise AssertionError("T0 serializer restart changed the replay payload")
    return {
        "control_tier": "T0_SYNTHETIC_CONTROL",
        "control_only": True,
        "replay_payload_sha256": sha256_hex(payload),
        "event_count": len(events),
        "restart_replay_identical": True,
        "formal_causal_credit": False,
    }


def _controlled_backtest_node_probe(root: Path) -> dict[str, object]:
    """Run a non-promotional provider-native control and inspect Cache/Portfolio."""
    from nautilus_trader.backtest import BacktestEngine, BacktestNode
    from nautilus_trader.config import (
        BacktestDataConfig,
        BacktestEngineConfig,
        BacktestRunConfig,
        BacktestVenueConfig,
    )
    from nautilus_trader.model import (
        AccountType,
        BookType,
        Currency,
        OmsType,
        Price,
        Quantity,
        QuoteTick,
    )
    from nautilus_trader.persistence import ParquetDataCatalog
    from nautilus_trader.testkit.providers import TestInstrumentProvider
    from nautilus_trader.trading import EmaCrossConfig

    instrument = TestInstrumentProvider.default_fx_ccy("AUD/USD")
    catalog = ParquetDataCatalog(str(root))
    mids = tuple(
        Decimal(value)
        for value in (
            "1.00000",
            "1.00000",
            "1.00000",
            "1.00000",
            "1.00000",
            "1.00100",
            "1.00200",
            "1.00300",
            "1.00400",
            "1.00500",
            "1.00400",
            "1.00200",
            "1.00000",
            "0.99800",
            "0.99600",
            "0.99500",
            "0.99700",
            "1.00000",
            "1.00300",
            "1.00600",
        )
    )
    start_ns = 1_700_000_000_000_000_000
    ticks = [
        QuoteTick(
            instrument_id=instrument.id,
            bid_price=Price.from_str(f"{mid:.5f}"),
            ask_price=Price.from_str(f"{mid + Decimal('0.00010'):.5f}"),
            bid_size=Quantity.from_int(1_000_000),
            ask_size=Quantity.from_int(1_000_000),
            ts_event=start_ns + index * 1_000_000_000,
            ts_init=start_ns + index * 1_000_000_000,
        )
        for index, mid in enumerate(mids)
    ]
    catalog.write_instruments([instrument])
    catalog.write_quote_ticks(ticks)
    venue = BacktestVenueConfig(
        name=str(instrument.id.venue),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        book_type=BookType.L1_MBP,
        base_currency=Currency.from_str("USD"),
        starting_balances=["1_000_000 USD"],
    )
    data = BacktestDataConfig(
        data_type="QuoteTick",
        catalog_path=str(root),
        instrument_id=instrument.id,
        start_time=ticks[0].ts_init,
        end_time=ticks[-1].ts_init + 1,
    )
    config = BacktestRunConfig(
        venues=[venue],
        data=[data],
        engine=BacktestEngineConfig(),
        dispose_on_completion=False,
    )
    node = BacktestNode(configs=[config])
    try:
        node.build()
        node.add_builtin_strategy(
            config.id,
            "EmaCross",
            EmaCrossConfig(
                instrument_id=instrument.id,
                trade_size=Quantity.from_int(100_000),
                fast_period=2,
                slow_period=4,
            ),
        )
        results = node.run()
        engine = node.get_engine(config.id)
        if engine is None:
            raise AssertionError("BacktestNode did not retain its provider-native engine")
        if not isinstance(engine, BacktestEngine):
            raise AssertionError("BacktestNode engine is not provider-native")
        projection = project_provider_native_state(engine)
        if not projection.cache_type.startswith(
            "nautilus_trader."
        ) or not projection.portfolio_type.startswith("nautilus_trader."):
            raise AssertionError("provider state projection lacks Nautilus provenance")
        if projection.filled_order_count < 1:
            raise AssertionError("T0 provider control produced no provider-owned fill state")
        return {
            "control_tier": "T0_SYNTHETIC_CONTROL",
            "control_only": True,
            "formal_causal_credit": False,
            "backtest_result_count": len(results),
            "provider_state": projection.model_dump(mode="json"),
        }
    finally:
        node.dispose()


def _assert_sha256(value: object, *, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field} must be a SHA-256 hex string")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{field} must be a SHA-256 hex string") from exc
    return value


def _representative_scale_probe(path: Path | None) -> dict[str, object]:
    if path is None:
        return {
            "status": "NOT_PROVEN",
            "representative_evidence_supplied": False,
            "actual_representative_market_count": 0,
            "reason": "NO_ACCEPTED_T2_REPRESENTATIVE_EVIDENCE_SUPPLIED",
        }
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("representative evidence must be an object")
    artifact_hash = _assert_sha256(raw.get("artifact_hash"), field="artifact_hash")
    identity = {key: value for key, value in raw.items() if key != "artifact_hash"}
    if sha256_hex(canonical_json_bytes(identity)) != artifact_hash:
        raise ValueError("representative evidence artifact hash does not bind its contents")
    if raw.get("evidence_tier") != "T2_REAL_CAUSAL_G4_ARTIFACT":
        raise ValueError("representative evidence must be accepted T2 causal evidence")
    if raw.get("synthetic") is not False or raw.get("manual_substitution") is not False:
        raise ValueError("synthetic/manual evidence cannot count for G4E8")
    records_raw = raw.get("markets")
    if not isinstance(records_raw, list):
        raise ValueError("representative evidence requires source-bound market records")
    records = tuple(RepresentativeMarketEvidence.model_validate(item) for item in records_raw)
    markets = assert_actual_representative_scale(records)
    return {
        "status": "PASS",
        "representative_evidence_supplied": True,
        "actual_representative_market_count": len(markets),
        "reason": None,
    }


def _e4_probe_state(
    path: Path | None,
    *,
    expected_head: str,
    expected_tree: str,
) -> dict[str, object]:
    if path is None:
        return {"status": "NOT_PROVEN", "source_hash": None}
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("same-job E4 probe result must be an object")
    observation = raw.get("observation")
    required = (
        raw.get("status") == "PASS",
        raw.get("exact_head") == expected_head,
        raw.get("exact_tree") == expected_tree,
        raw.get("public_data_only") is True,
        raw.get("zero_credentials") is True,
        raw.get("zero_execution_client") is True,
        raw.get("zero_signing") is True,
        raw.get("zero_exchange_write") is True,
        isinstance(observation, dict),
        isinstance(observation, dict) and observation.get("quote_observed") is True,
        isinstance(observation, dict) and observation.get("trade_observed") is True,
        isinstance(observation, dict)
        and observation.get("finalized_bar_callback_observed") is True,
        isinstance(observation, dict)
        and observation.get("finalized_bar_evidence_persisted") is True,
    )
    if not all(required):
        return {
            "status": "NOT_PROVEN",
            "source_hash": sha256_hex(canonical_json_bytes(raw)),
        }
    return {
        "status": "PASS_REQUIRES_EXACT_HEAD_E4_CI",
        "source_hash": sha256_hex(canonical_json_bytes(raw)),
    }


def qualify(
    representative_evidence: Path | None,
    e4_probe_result: Path | None,
) -> dict[str, object]:
    from nautilus_trader.backtest import BacktestEngine
    from nautilus_trader.execution import ProbabilisticFillModel

    assert_exact_nautilus_rc5()
    assert_backtest_node_catalog_surface()
    reference = _candidate()
    challenger = _candidate("qualification-challenger")
    if len(candidate_state_isolation_plan((reference, challenger))) != 2:
        raise AssertionError("candidate isolation plan did not retain both identities")
    fill_model = build_fill_model(_execution())
    if not isinstance(fill_model, ProbabilisticFillModel):
        raise AssertionError("provider-native ProbabilisticFillModel was not consumed")

    first_engine = new_isolated_backtest_engine(reference)
    second_engine = new_isolated_backtest_engine(challenger)
    try:
        if not isinstance(first_engine, BacktestEngine) or not isinstance(
            second_engine, BacktestEngine
        ):
            raise AssertionError("provider-native BacktestEngine was not consumed")
        if first_engine is second_engine:
            raise AssertionError("candidate execution state leaked into one shared engine")
    finally:
        first_engine.dispose()
        second_engine.dispose()

    serializer = _t0_serializer_probe()
    with TemporaryDirectory(prefix="trade-os-formal-g4-") as directory:
        provider = _controlled_backtest_node_probe(Path(directory))
    scale = _representative_scale_probe(representative_evidence)

    git_sha = os.environ.get("G4_EXACT_HEAD", "0" * 40)
    git_tree = os.environ.get("G4_EXACT_TREE", "0" * 40)
    if len(git_sha) != 40 or len(git_tree) != 40:
        raise AssertionError("exact-head and exact-tree identity must be supplied by the harness")
    e4_probe = _e4_probe_state(
        e4_probe_result,
        expected_head=git_sha,
        expected_tree=git_tree,
    )
    manifest = G4RunManifest.create(
        run_id=f"formal-g4-control-{git_sha[:12]}",
        git_sha=git_sha,
        git_tree=git_tree,
        source_e4_manifest_hash="c" * 64,
        source_pit_snapshot_hash="d" * 64,
        source_evidence_artifact_hashes=(
            EvidenceArtifactHash(
                name="t0-serializer-control",
                sha256=str(serializer["replay_payload_sha256"]),
            ),
        ),
        structural_component_manifest_hash=STRUCTURAL_HASH,
        execution_model=_execution(),
        candidates=(reference, challenger),
        trial_adaptivity_id="formal-g4-control-trial-v1",
        cutoff_id="formal-g4-control-cutoff-v1",
    )

    provider_state = provider["provider_state"]
    assert isinstance(provider_state, dict)
    causal_gates = causal_claim_gate_states(
        evidence_tier="T0_SYNTHETIC_CONTROL",
        synthetic=True,
        manual_substitution=False,
        deterministic_replay_proven=True,
        semantic_derivation_proven=False,
        validation_materialized=False,
        canonical_order_intent_proven=False,
        provider_outcome_cost_provenance_complete=False,
        restart_equivalence_proven=True,
    )
    ladder = {
        "G4E0": "PASS",
        "G4E1": causal_gates["G4E1"],
        "G4E2": causal_gates["G4E2"],
        "G4E3": "PASS",
        "G4E4": "PASS",
        "G4E5": causal_gates["G4E5"],
        "G4E6": str(e4_probe["status"]),
        "G4E7": causal_gates["G4E7"],
        "G4E8": str(scale["status"]),
    }
    return {
        "schema_version": "VNEXT_FORMAL_G4_TECHNICAL_QUALIFICATION_RESULT_V2R2",
        "status": "TECHNICAL_G4_PARTIAL",
        "nautilus_version": "2.0.0rc5",
        "exact_head": git_sha,
        "exact_tree": git_tree,
        "g4_manifest_hash": manifest.manifest_hash,
        "g4e0_contract_identity": "PASS",
        "g4e1_deterministic_causal_replay": causal_gates["G4E1"],
        "g4e2_vnext_decision_parity": causal_gates["G4E2"],
        "g4e3_explicit_execution_model": "PASS",
        "g4e4_candidate_state_isolation": "PASS",
        "g4e5_fill_fee_outcome_report_parity": causal_gates["G4E5"],
        "g4e6_zero_write_live_path_composition": e4_probe["status"],
        "g4e7_reconnect_restart_nonregression": causal_gates["G4E7"],
        "g4e8_representative_scale_runtime": scale["status"],
        "formal_g4_technical_acceptance": formal_g4_acceptance(ladder),
        "representative_scale_boundary": REPRESENTATIVE_MARKET_FLOOR,
        "representative_evidence_supplied": scale["representative_evidence_supplied"],
        "actual_representative_market_count": scale[
            "actual_representative_market_count"
        ],
        "g4e8_reason": scale["reason"],
        "t2_real_causal_artifact_supplied": False,
        "t2_absence_reason": "NO_ACCEPTED_T2_REAL_CAUSAL_G4_ARTIFACT_SUPPLIED",
        "provider_native_backtest_engine": True,
        "provider_native_fill_model": True,
        "backtest_node_catalog_surface": True,
        "provider_state_source_api": provider_state["source_api"],
        "controlled_provider_order_count": provider_state["order_count"],
        "controlled_provider_filled_order_count": provider_state["filled_order_count"],
        "controlled_provider_position_count": provider_state["position_count"],
        "controlled_provider_account_count": provider_state["account_count"],
        "controlled_provider_state_hash": provider_state["state_hash"],
        "controlled_replay_is_representative_evidence": False,
        "t0_controls_are_formal_causal_proof": False,
        "t0_serializer_restart_identical": serializer["restart_replay_identical"],
        "same_job_e4_probe_result_hash": e4_probe["source_hash"],
        "derived_cache_is_authoritative_market_truth": False,
        "strategy_edge_proven": False,
        "confirmatory_e5_open": False,
        "private_api": False,
        "signing": False,
        "exchange_write": False,
        "venue_submitted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-path", type=Path, required=True)
    parser.add_argument("--representative-evidence", type=Path)
    parser.add_argument("--e4-probe-result", type=Path)
    args = parser.parse_args()
    result = qualify(args.representative_evidence, args.e4_probe_result)
    args.result_path.parent.mkdir(parents=True, exist_ok=True)
    args.result_path.write_text(
        json.dumps(result, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
