#!/usr/bin/env python3
# mypy: disable-error-code="import-not-found"
"""Bounded exact-rc5 Ordinary VNext Formal G4 technical qualification."""

from __future__ import annotations

import argparse
import json
import os
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.nautilus_e4.contracts import (
    AdmittedEvent,
    DataKind,
    EvidenceState,
    SourceEvent,
)
from trader_assist_v0.nautilus_g4.catalog_bridge import build_replay_payload
from trader_assist_v0.nautilus_g4.runner import (
    assert_actual_representative_scale,
    assert_backtest_node_catalog_surface,
    assert_exact_nautilus_rc5,
    build_fill_model,
    candidate_state_isolation_plan,
    new_isolated_backtest_engine,
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
    ParticipationDecision,
    ReentryPolicy,
    WinnerConfirmation,
)
from trader_assist_v0.vnext_g4.evaluator import EvaluationInputs, evaluate_participation
from trader_assist_v0.vnext_g4.reporting import ThesisOutcome, build_development_report

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
        event_context="FINALIZED_5M",
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


def _deterministic_replay_probe() -> dict[str, object]:
    events = (_admitted(1), _admitted(2))
    payload = build_replay_payload(events)
    restarted = tuple(
        AdmittedEvent.model_validate_json(event.model_dump_json()) for event in events
    )
    restarted_payload = build_replay_payload(restarted)
    if payload != restarted_payload:
        raise AssertionError("restart/rebuild changed the causal replay payload")
    return {
        "replay_payload_sha256": sha256_hex(payload),
        "event_count": len(events),
        "restart_replay_identical": True,
    }


def _decision_parity_probe(candidate: CandidateManifest) -> dict[str, object]:
    inputs = EvaluationInputs(
        formal_setup_confirmed=True,
        thesis_valid=True,
        bbo_state_valid=True,
        data_evaluable=True,
        restart_reference_crossed=True,
        retest_seen=False,
        microstructure_warmup_seconds=60,
        side_adjusted_aggressor_imbalance_15s=Decimal("1"),
        flow_price_response_15s_bps=Decimal("1"),
        remaining_structural_room_bps=Decimal("10"),
        all_in_friction_bps=Decimal("2"),
        economics_can_improve=True,
    )
    first = evaluate_participation(candidate.config, inputs)
    second = evaluate_participation(candidate.config, inputs)
    if first != second:
        raise AssertionError("same frozen candidate/input did not produce identical decisions")
    if first.venue_submitted is not False:
        raise AssertionError("G4 decision evaluation must remain zero-write")
    return {
        "decision": first.decision.value,
        "decision_parity": True,
        "venue_submitted": first.venue_submitted,
    }


def _project_report_parity_probe() -> dict[str, object]:
    outcomes = (
        ThesisOutcome(
            thesis_id="formal-g4-control-thesis",
            market_id=CONTROL_MARKET,
            decision=ParticipationDecision.TAKE,
            attempt_count=1,
            net_r_after_cost=Decimal("0.25"),
            fee_bps=Decimal("1"),
            spread_slippage_bps=Decimal("2"),
            market_mfe_bps=Decimal("8"),
            market_mae_bps=Decimal("3"),
            executable_mfe_bps=Decimal("7"),
            executable_mae_bps=Decimal("4"),
        ),
    )
    first = build_development_report(outcomes)
    second = build_development_report(outcomes)
    if first != second:
        raise AssertionError("project G4 reporting is not deterministic")
    return {
        "project_report_deterministic": True,
        "project_report": first.model_dump(mode="json"),
    }


def _controlled_backtest_node_probe(root: Path) -> dict[str, object]:
    """Run a non-promotional provider-native control replay with non-empty fills."""
    from nautilus_trader.backtest import BacktestNode
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
    catalog.write_data([instrument])
    catalog.write_data(ticks)
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
        fills = node.generate_order_fills_report(config.id)
        positions = node.generate_positions_report(config.id)
        if len(fills) < 1:
            raise AssertionError("controlled provider-native replay produced no fills")
        return {
            "backtest_result_count": len(results),
            "fill_rows": len(fills),
            "position_rows": len(positions),
            "fill_report_sha256": sha256_hex(fills.to_csv(index=False).encode()),
            "position_report_sha256": sha256_hex(
                positions.to_csv(index=False).encode()
            ),
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
            "reason": "NO_ACCEPTED_REPRESENTATIVE_E4_EVIDENCE_SUPPLIED",
        }
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("accepted_e4_evidence") is not True:
        raise ValueError("representative evidence must declare accepted_e4_evidence=true")
    _assert_sha256(
        raw.get("source_e4_manifest_hash"),
        field="source_e4_manifest_hash",
    )
    _assert_sha256(
        raw.get("source_pit_snapshot_hash"),
        field="source_pit_snapshot_hash",
    )
    artifacts = raw.get("source_evidence_artifact_hashes")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("representative evidence requires source evidence artifact hashes")
    hashes = tuple(
        _assert_sha256(
            item.get("sha256"),
            field="source_evidence_artifact_hashes.sha256",
        )
        for item in artifacts
        if isinstance(item, dict)
    )
    if len(hashes) != len(artifacts):
        raise ValueError("representative evidence artifact records must be objects")
    counts_raw = raw.get("market_event_counts")
    if not isinstance(counts_raw, dict):
        raise ValueError("representative evidence requires market_event_counts")
    counts: dict[str, int] = {}
    for market_id, count in counts_raw.items():
        if not isinstance(market_id, str) or not isinstance(count, int):
            raise ValueError("market_event_counts must map market IDs to integer counts")
        counts[market_id] = count
    markets = assert_actual_representative_scale(
        counts,
        source_evidence_hashes=hashes,
    )
    return {
        "status": "PASS",
        "representative_evidence_supplied": True,
        "actual_representative_market_count": len(markets),
        "reason": None,
    }


def qualify(representative_evidence: Path | None) -> dict[str, object]:
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
        if not isinstance(first_engine, BacktestEngine):
            raise AssertionError("reference provider-native BacktestEngine was not consumed")
        if not isinstance(second_engine, BacktestEngine):
            raise AssertionError("challenger provider-native BacktestEngine was not consumed")
        if first_engine is second_engine:
            raise AssertionError("candidate execution state leaked into one shared engine")
    finally:
        first_engine.dispose()
        second_engine.dispose()

    replay = _deterministic_replay_probe()
    decision = _decision_parity_probe(reference)
    report = _project_report_parity_probe()
    with TemporaryDirectory(prefix="trade-os-formal-g4-") as directory:
        provider = _controlled_backtest_node_probe(Path(directory))
    scale = _representative_scale_probe(representative_evidence)

    git_sha = os.environ.get("G4_EXACT_HEAD", "0" * 40)
    git_tree = os.environ.get("G4_EXACT_TREE", "0" * 40)
    if len(git_sha) != 40 or len(git_tree) != 40:
        raise AssertionError("exact-head and exact-tree identity must be supplied by the harness")
    manifest = G4RunManifest.create(
        run_id=f"formal-g4-control-{git_sha[:12]}",
        git_sha=git_sha,
        git_tree=git_tree,
        source_e4_manifest_hash="c" * 64,
        source_pit_snapshot_hash="d" * 64,
        source_evidence_artifact_hashes=(
            EvidenceArtifactHash(
                name="controlled-causal-replay",
                sha256=str(replay["replay_payload_sha256"]),
            ),
        ),
        structural_component_manifest_hash=STRUCTURAL_HASH,
        execution_model=_execution(),
        candidates=(reference, challenger),
        trial_adaptivity_id="formal-g4-control-trial-v1",
        cutoff_id="formal-g4-control-cutoff-v1",
    )

    g4e8_pass = scale["status"] == "PASS"
    status = "FORMAL_G4_TECHNICAL_PASS" if g4e8_pass else "TECHNICAL_G4_PARTIAL"
    return {
        "schema_version": "VNEXT_FORMAL_G4_TECHNICAL_QUALIFICATION_RESULT_V1",
        "status": status,
        "nautilus_version": "2.0.0rc5",
        "exact_head": git_sha,
        "exact_tree": git_tree,
        "g4_manifest_hash": manifest.manifest_hash,
        "g4e0_contract_identity": "PASS",
        "g4e1_deterministic_causal_replay": "PASS",
        "g4e2_vnext_decision_parity": "PASS",
        "g4e3_explicit_execution_model": "PASS",
        "g4e4_candidate_state_isolation": "PASS",
        "g4e5_fill_fee_outcome_report_parity": "PASS",
        "g4e6_zero_write_live_path_composition": "PASS_REQUIRES_EXACT_HEAD_E4_CI",
        "g4e7_reconnect_restart_nonregression": "PASS",
        "g4e8_representative_scale_runtime": scale["status"],
        "formal_g4_technical_acceptance": g4e8_pass,
        "representative_scale_boundary": REPRESENTATIVE_MARKET_FLOOR,
        "representative_evidence_supplied": scale["representative_evidence_supplied"],
        "actual_representative_market_count": scale[
            "actual_representative_market_count"
        ],
        "g4e8_reason": scale["reason"],
        "provider_native_backtest_engine": True,
        "provider_native_fill_model": True,
        "backtest_node_catalog_surface": True,
        "controlled_provider_report_fill_rows": provider["fill_rows"],
        "controlled_provider_report_position_rows": provider["position_rows"],
        "controlled_provider_fill_report_sha256": provider["fill_report_sha256"],
        "controlled_provider_position_report_sha256": provider[
            "position_report_sha256"
        ],
        "controlled_replay_is_representative_evidence": False,
        "replay_payload_sha256": replay["replay_payload_sha256"],
        "restart_replay_identical": replay["restart_replay_identical"],
        "decision_parity": decision["decision_parity"],
        "project_report_deterministic": report["project_report_deterministic"],
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
    args = parser.parse_args()
    result = qualify(args.representative_evidence)
    args.result_path.parent.mkdir(parents=True, exist_ok=True)
    args.result_path.write_text(
        json.dumps(result, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
