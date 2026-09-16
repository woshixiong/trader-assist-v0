from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_e4.contracts import (
    DATA_VERSION,
    EXECUTION_MODEL_VERSION,
    LEGACY_NAUTILUS_VERSION,
    NAUTILUS_VERSION,
    WARMUP_5M_BARS,
    ApprovalProvenance,
    ApprovalTimingMode,
    EvidenceState,
    ExecutionChain,
    GuardDecision,
    GuardInputs,
    LifecycleKind,
    LifecycleRecord,
    LifecycleStatus,
    MarketExpression,
    PitUniverseSnapshot,
    RunManifest,
    StopChain,
    historical_pit_claim_state,
    strategy_history_state,
)
from trader_assist_v0.nautilus_e4.guard import evaluate_entry_guard
from trader_assist_v0.nautilus_e4.safety import assert_public_only

BASE_SHA = "2" * 40
TREE = "3" * 40
MARKET = sha256_hex(b"HYPERLIQUID|MAIN|ETH")
STATE = "4" * 64
_MANIFEST_DOMAIN = b"trader-assist-v0/e4/run-manifest/v1\0"


def expression(*, market_id: str = MARKET, coin: str = "ETH") -> MarketExpression:
    return MarketExpression(
        market_id=market_id,
        dex="MAIN",
        provider_coin=coin,
        instrument_id=f"{coin}-PERP.HYPERLIQUID",
        expression_id=f"expr-{coin}",
        listing_state=None,
        instrument_metadata_version="meta-v1",
        instrument_metadata_hash=sha256_hex(f"metadata-{coin}".encode()),
        fee_state_version="fee-v1",
        fee_state_hash=sha256_hex(f"fee-{coin}".encode()),
        growth_mode=None,
        deployer_fee_state=None,
    )


def snapshot() -> PitUniverseSnapshot:
    return PitUniverseSnapshot.create(observed_at_ns=1, expressions=(expression(),))


def manifest(**updates: object) -> RunManifest:
    values: dict[str, object] = {
        "run_id": "run-e4",
        "git_sha": BASE_SHA,
        "git_tree": TREE,
        "snapshot": snapshot(),
        "process_epoch": "process-1",
        "continuity_epoch": "continuity-1",
        "admission_epoch": "admission-1",
        "capture_configuration": {
            "expressions": [expression().model_dump(mode="json")],
            "prebuffer_seconds": 60,
            "post_terminal_micro_seconds": 1800,
            "post_terminal_context_seconds": 21600,
        },
        "subscription_policy": {"discovery": [MARKET], "watch": [MARKET]},
        "trial_ledger_id": "trial-v1",
    }
    values.update(updates)
    return RunManifest.create(**values)  # type: ignore[arg-type]


def guard_inputs(**updates: object) -> GuardInputs:
    values: dict[str, object] = {
        "spread_bps": Decimal("1"),
        "all_in_friction_bps": Decimal("2"),
        "remaining_room_bps": Decimal("8"),
        "minimum_room_to_cost": Decimal("3"),
        "bbo_state_valid": True,
        "data_evaluable": True,
        "intended_notional": Decimal("100"),
        "top_level_notional": Decimal("200"),
        "guard_config_version": "guard-v1",
    }
    values.update(updates)
    return GuardInputs.model_validate(values)


def test_pit_and_manifest_bind_exact_versions_current_state_and_zero_write() -> None:
    pit = snapshot()
    run = manifest()

    assert pit.snapshot_id == pit.snapshot_hash
    assert pit.history_provenance == "PROSPECTIVE_CURRENT_STATE"
    assert pit.expressions[0].listing_state is None
    assert historical_pit_claim_state(pit) is EvidenceState.NOT_EVALUABLE
    assert run.pit_snapshot_hash == pit.snapshot_hash
    assert run.nautilus_version == NAUTILUS_VERSION == "2.0.0rc5"
    assert run.data_version == DATA_VERSION
    assert run.execution_model_version == EXECUTION_MODEL_VERSION
    assert run.execution_model_limited is True
    assert run.private_api is run.exchange_write is run.real_exec_client_registered is False


def test_legacy_rc4_manifest_identity_remains_hash_verified_and_readable() -> None:
    raw = manifest().model_dump(mode="json")
    raw["nautilus_version"] = LEGACY_NAUTILUS_VERSION
    identity = {key: value for key, value in raw.items() if key != "manifest_hash"}
    raw["manifest_hash"] = sha256_hex(_MANIFEST_DOMAIN + canonical_json_bytes(identity))

    legacy = RunManifest.model_validate(raw)
    assert legacy.nautilus_version == "2.0.0rc4"
    assert RunManifest.model_validate_json(legacy.model_dump_json()) == legacy


def test_pit_tamper_and_incompatible_versions_fail_closed() -> None:
    with pytest.raises(ValidationError, match="snapshot hash"):
        snapshot().model_copy(update={"observed_at_ns": 2}).model_validate(
            snapshot().model_copy(update={"observed_at_ns": 2})
        )
    raw = manifest().model_dump(mode="json")
    raw["strategy_version"] = "INCOMPATIBLE"
    with pytest.raises(ValidationError):
        RunManifest.model_validate(raw)


@pytest.mark.parametrize(
    ("updates", "decision", "reason"),
    (
        ({}, GuardDecision.PASS, None),
        ({"bbo_state_valid": False}, GuardDecision.NO_SUBMIT, "BBO_STATE_INVALID"),
        ({"data_evaluable": False}, GuardDecision.NO_SUBMIT, "DATA_NOT_EVALUABLE"),
        (
            {"intended_notional": Decimal("300")},
            GuardDecision.NO_SUBMIT,
            "UNSUPPORTED_L1_DEPTH",
        ),
        (
            {"remaining_room_bps": Decimal("5")},
            GuardDecision.NO_SUBMIT,
            "ROOM_TO_COST_BELOW_POLICY",
        ),
    ),
)
def test_pure_guard_pass_or_zero_write_no_submit(
    updates: dict[str, object], decision: GuardDecision, reason: str | None
) -> None:
    result = evaluate_entry_guard(guard_inputs(**updates))
    assert result.decision is decision
    assert result.venue_submitted is False and result.not_submitted is True
    if reason is not None:
        assert reason in result.reason_codes


def test_no_submit_is_terminal_and_not_attempt_failed() -> None:
    result = evaluate_entry_guard(guard_inputs(bbo_state_valid=False))
    chain = ExecutionChain(
        package_id="pkg-001",
        activation_ts=10,
        activation_market_state_id=STATE,
        approval_provenance=ApprovalProvenance.NOT_APPLICABLE,
        guard_eval_ts=11,
        guard_result=result,
        order_primitive="NOT_APPLICABLE",
        modeled_fill_state="NOT_MODELED",
        execution_model_version=EXECUTION_MODEL_VERSION,
        execution_model_limited=True,
    )
    assert chain.guard_result.decision is GuardDecision.NO_SUBMIT
    assert "ATTEMPT_FAILED" not in chain.guard_result.reason_codes
    with pytest.raises(ValidationError, match="terminal"):
        chain.model_copy(update={"order_submit_intent_ts": 12}).model_validate(
            chain.model_copy(update={"order_submit_intent_ts": 12})
        )


def test_execution_chain_binds_first_post_active_state_and_limitation() -> None:
    result = evaluate_entry_guard(guard_inputs())
    chain = ExecutionChain(
        package_id="pkg-001",
        armed_ts=8,
        activation_ts=10,
        activation_market_state_id=STATE,
        approval_provenance=ApprovalProvenance.SIMULATED,
        guard_eval_ts=11,
        guard_result=result,
        order_submit_intent_ts=12,
        hypothetical_order_active_ts=20,
        active_market_state_id="5" * 64,
        fill_market_state_ts=21,
        order_primitive="MARKETABLE",
        modeled_fill_state="FILLED",
        modeled_fill_ts=21,
        modeled_fill_price=Decimal("101"),
        modeled_fill_vwap=Decimal("101"),
        modeled_fill_qty=Decimal("0.1"),
        execution_model_version=EXECUTION_MODEL_VERSION,
        execution_model_limited=True,
    )
    assert chain.fill_market_state_ts >= chain.hypothetical_order_active_ts
    assert chain.execution_model_limited is True
    assert chain.not_submitted is True
    with pytest.raises(ValidationError, match="not causal"):
        ExecutionChain.model_validate(
            {**chain.model_dump(mode="json"), "fill_market_state_ts": 19}
        )


def test_approval_modes_preserved_and_observed_provenance_forbidden() -> None:
    common = dict(
        schema_version="E4_CAPTURE_V1",
        run_id="run-e4",
        object_id="armed-001",
        parent_id=None,
        package_id="pkg-001",
        market_id=MARKET,
        expression_id="expr-ETH",
        kind=LifecycleKind.ARMED,
        status=LifecycleStatus.ACTIVE,
        state_ts=10,
        reason_codes=("ARMED",),
        decision_state=None,
        approval_provenance=ApprovalProvenance.SIMULATED,
        expiry_ts=20,
        supersedes_id=None,
        last_admission_ordinal=1,
        evidence_state=EvidenceState.COMPLETE,
    )
    post = LifecycleRecord.create(
        **common, approval_timing_mode=ApprovalTimingMode.POST_ACTIVATION
    )
    pre = LifecycleRecord.create(
        **{**common, "object_id": "armed-002"},
        approval_timing_mode=ApprovalTimingMode.PREAUTHORIZED_ARMED,
    )
    assert post.approval_timing_mode != pre.approval_timing_mode
    with pytest.raises(ValidationError, match="observed Human approval"):
        LifecycleRecord.create(
            **{**common, "object_id": "armed-003", "approval_provenance": "OBSERVED"},
            approval_timing_mode=ApprovalTimingMode.POST_ACTIVATION,
        )


def test_stop_source_chain_identity_and_causal_timing_are_preserved() -> None:
    chain = StopChain(
        package_id="pkg-001",
        stop_decision_id="stop-001",
        stop_reference_id="6" * 64,
        trigger_id="7" * 64,
        trigger_ts=100,
        hypothetical_active_ts=110,
        executable_market_state_id="8" * 64,
        fill_market_state_ts=111,
        modeled_fill_state="FILLED",
        modeled_fill_ts=111,
        modeled_fill_price=Decimal("99"),
        modeled_fill_vwap=Decimal("99"),
        execution_model_version=EXECUTION_MODEL_VERSION,
        collar_config_version="collar-v1",
        execution_model_limited=True,
    )
    assert chain.stop_reference_id == "6" * 64
    assert chain.trigger_id == "7" * 64
    assert chain.not_submitted is True


def test_passive_touch_cannot_silently_become_realistic_fill() -> None:
    result = evaluate_entry_guard(guard_inputs())
    with pytest.raises(ValidationError, match="passive touch"):
        ExecutionChain(
            package_id="pkg-001",
            activation_ts=10,
            activation_market_state_id=STATE,
            approval_provenance=ApprovalProvenance.NOT_APPLICABLE,
            guard_eval_ts=11,
            guard_result=result,
            order_submit_intent_ts=12,
            hypothetical_order_active_ts=13,
            active_market_state_id="5" * 64,
            fill_market_state_ts=14,
            order_primitive="PASSIVE",
            modeled_fill_state="FILLED",
            modeled_fill_ts=14,
            modeled_fill_price=Decimal("101"),
            modeled_fill_vwap=Decimal("101"),
            modeled_fill_qty=Decimal("0.1"),
            execution_model_version=EXECUTION_MODEL_VERSION,
            execution_model_limited=True,
        )


def test_fill_model_and_limitation_must_be_explicit() -> None:
    result = evaluate_entry_guard(guard_inputs())
    with pytest.raises(ValidationError):
        ExecutionChain(
            package_id="pkg-001",
            activation_ts=10,
            activation_market_state_id=STATE,
            approval_provenance=ApprovalProvenance.NOT_APPLICABLE,
            guard_eval_ts=11,
            guard_result=result,
            order_primitive="MARKETABLE",
            modeled_fill_state="NONFILL",
        )


def test_raw_capture_before_2304_bars_cannot_be_strategy_evidence() -> None:
    assert strategy_history_state(WARMUP_5M_BARS - 1) is EvidenceState.NOT_EVALUABLE
    assert strategy_history_state(WARMUP_5M_BARS) is EvidenceState.COMPLETE


@pytest.mark.parametrize(
    "env",
    (
        {"HYPERLIQUID_API_KEY": "present"},
        {"HYPERLIQUID_PRIVATE_KEY": "present"},
        {"HYPERLIQUID_PK": "present"},
        {"HYPERLIQUID_TESTNET_PK": "present"},
        {"HYPERLIQUID_VAULT": "present"},
        {"HYPERLIQUID_TESTNET_VAULT": "present"},
        {"HYPERLIQUID_ACCOUNT_ADDRESS": "present"},
        {"NAUTILUS_HYPERLIQUID_WALLET_ADDRESS": "present"},
    ),
)
def test_forbidden_credential_environment_fails_closed(env: dict[str, str]) -> None:
    with pytest.raises(RuntimeError, match="forbidden exchange credential"):
        assert_public_only(env=env)


def test_public_only_config_has_hard_zero_write_proof() -> None:
    proof = assert_public_only(env={}, config={"data_clients": {"HYPERLIQUID": {}}})
    assert proof.model_dump() == {
        "real_exec_client_registered": False,
        "signing": False,
        "private_api": False,
        "exchange_write": False,
        "venue_submitted": False,
        "not_submitted": True,
    }
    with pytest.raises(RuntimeError, match="exec_clients"):
        assert_public_only(env={}, config={"exec_clients": {"HYPERLIQUID": {}}})


@pytest.mark.parametrize("key", ("private_key", "vault_address", "account_address"))
def test_actual_hyperliquid_credential_config_names_fail_closed(key: str) -> None:
    with pytest.raises(RuntimeError, match=key):
        assert_public_only(env={}, config={"data_clients": {"HYPERLIQUID": {key: "x"}}})


def test_host_and_probe_have_no_order_signing_or_private_api_surface() -> None:
    root = Path(__file__).resolve().parents[1]
    paths = (
        root / "src/trader_assist_v0/nautilus_e4/host.py",
        root / "scripts/e4_nautilus_public_data_probe.py",
    )
    prohibited = {
        "submit_order",
        "submit_order_list",
        "cancel_order",
        "cancel_all_orders",
        "modify_order",
        "sign",
        "sign_order",
    }
    names: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names |= {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        names |= {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert prohibited.isdisjoint(names)
    assert {"connect", "reconnect", "resubscribe"}.isdisjoint(names)
    host_source = paths[0].read_text(encoding="utf-8")
    probe_source = paths[1].read_text(encoding="utf-8")
    assert "StreamingConfig" not in host_source
    assert "TradingNode" not in host_source
    assert "LiveNode.builder(" in host_source
    assert "node.add_strategy(strategy)" in probe_source
    assert "handle = node.handle()" in probe_source


def test_public_provider_workflow_is_bounded_and_requires_observed_data() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/nautilus-e4-ci.yml").read_text(
        encoding="utf-8"
    )
    probe = (root / "scripts/e4_nautilus_public_data_probe.py").read_text(
        encoding="utf-8"
    )
    assert "timeout 150s" in workflow
    assert "--run-seconds 90" in workflow
    assert "--ci-instrument-id ETH-USD-PERP.HYPERLIQUID" in workflow
    assert 'result["status"] == "PASS"' in workflow
    assert "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02" in workflow
    assert "PROVIDER_DATA_INCOMPLETE" in probe
    assert "APPLICATION_FAILURE" in probe
    assert "HARNESS_INFRASTRUCTURE_FAILURE" in workflow
    assert "BOUNDED_PUBLIC_ONLY_COMPLETED" not in probe
    assert "_external_minute_bar_type(args.ci_instrument_id)" in probe
    assert "BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST)" in probe
    for required_proof in (
        "PUBLIC_HYPERLIQUID_DATA_ONLY",
        "QUOTE_OBSERVED",
        "TRADE_OBSERVED",
        "BAR_SUBSCRIPTION_REGISTERED",
        "FINALIZED_BAR_CALLBACK_OBSERVED",
        "FINALIZED_BAR_EVIDENCE_PERSISTED",
    ):
        assert required_proof in probe


def test_host_uses_explicit_exact_version_identity_surfaces_and_durable_bar_flush() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/trader_assist_v0/nautilus_e4/host.py").read_text(
        encoding="utf-8"
    )
    assert "assert_exact_nautilus_version" in source
    assert "manifest/runtime Nautilus version mismatch" in source
    start = source.index("    def _expression_for(")
    end = source.index("\n\n\ndef build_public_data_node", start)
    mapping = source[start:end]
    assert "isinstance(event, QuoteTick)" in mapping
    assert "isinstance(event, TradeTick)" in mapping
    assert "isinstance(event, Bar)" in mapping
    assert "event.bar_type.instrument_id" in mapping
    assert 'getattr(event, "instrument_id"' not in mapping
    assert "unsupported provider event type" in mapping

    bar_start = source.index("    def on_bar(")
    bar_end = source.index("    def on_socket_state(", bar_start)
    callback = source[bar_start:bar_end]
    assert "self._session.ingest(" in callback
    assert "self._session.persist_durable_evidence(" in callback
    assert callback.index("self._session.ingest(") < callback.index(
        "self._session.persist_durable_evidence("
    )


def test_host_checkpoints_interrupted_state_before_teardown_artifacts() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/trader_assist_v0/nautilus_e4/host.py").read_text(
        encoding="utf-8"
    )
    start = source.index("    def on_stop(self) -> None:")
    end = source.index("    def _expression_for", start)
    callback = source[start:end]
    assert callback.index("self._session.interrupt") < callback.index(
        "self._session.persist_runtime_checkpoint"
    )
    assert callback.index("self._session.persist_runtime_checkpoint") < callback.index(
        "self._session.write_operational_artifacts"
    )
