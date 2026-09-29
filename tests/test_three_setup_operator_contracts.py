"""Synthetic retained evidence used only by zero-write operator tests."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trader_assist_v0.multi_asset_shadow.shadow_records.records import (
    FormalSignal,
    ImmutableRecord,
    MarketEvent,
    PlanRecord,
    ProvenanceRecord,
    ShadowOrder,
    StrategyEvaluation,
)
from trader_assist_v0.multi_asset_shadow.shadow_records.store import EvidenceStore
from trader_assist_v0.operator.contracts import OperatorConfig, OperatorCredential


def make_source(
    path: Path, *, created_ms: int, instrument: str = "BTC-PERP",
    policy_version: str | None = None, opportunity_suffix: str = "",
) -> str:
    with EvidenceStore(path):
        pass
    stamp = datetime.fromtimestamp(created_ms / 1000, tz=UTC).isoformat()
    provenance = ProvenanceRecord.create(
        identity={"sample": "provenance" + opportunity_suffix},
        strategy_version="strategy-v1",
        parameter_version="params-v1",
        registry_version="registry-v1",
        registry_hash="r" * 64,
        cost_model_version="cost-v1",
        release_sha="a" * 40,
        recorded_at=stamp,
    )
    event = MarketEvent.create(
        identity={"sample": "event" + opportunity_suffix},
        market_id="market-1",
        event_kind="BREAKOUT_RETEST",
        event_time=stamp,
        kernel_market_event_id="kernel-opportunity-1" + opportunity_suffix,
        side="LONG",
        setup_family="BREAKOUT_RETEST",
    )
    evaluation = StrategyEvaluation.create(
        identity={"sample": "evaluation" + opportunity_suffix},
        evaluation_id="evaluation-1" + opportunity_suffix,
        market_id="market-1",
        latest_closed_5m_hash="b" * 64,
        evaluation_boundary_ms=created_ms,
        registry_version="registry-v1",
        registry_hash="r" * 64,
        strategy_version="strategy-v1",
        parameter_version="params-v1",
        input_ledger_hash="c" * 64,
        output_ledger_hash="d" * 64,
        output_ledger={},
        decisions=[],
    )
    signal = FormalSignal.create(
        identity={"sample": "signal" + opportunity_suffix},
        market_event_id=event.record_id,
        market_id="market-1",
        setup_family="BREAKOUT_RETEST",
        setup_mode="STANDARD",
        side="LONG",
        approval_status="APPROVED",
        tier="P1",
        confirmed_at=stamp,
        provenance_id=provenance.record_id,
        strategy_evaluation_id="evaluation-1" + opportunity_suffix,
    )
    sizing = {
        "reference_equity_usd": "200",
        "risk_pct_1": "1.0",
        "risk_pct_2": "2.0",
        "reference_qty_1pct": "0.02",
        "reference_qty_2pct": "0.04",
        "reference_notional_1pct": "2",
        "reference_notional_2pct": "4",
        "reference_size_only": "YES",
        "not_account_authoritative": "YES",
    }
    terms = {
        "planned_entry": "100",
        "stop": "90",
        "tp1": "110",
        "tp2": "120",
        "risk_reference_sizing": sizing,
    }
    plan = PlanRecord.create(
        identity={"sample": "plan" + opportunity_suffix},
        signal_id=signal.record_id,
        created_at=stamp,
        provenance_id=provenance.record_id,
        **terms,
    )
    shadow = ShadowOrder.create(
        identity={"sample": "shadow" + opportunity_suffix},
        signal_id=signal.record_id,
        plan_id=plan.record_id,
        market_event_id=event.record_id,
        market_id="market-1",
        instrument_id=instrument,
        setup_family="BREAKOUT_RETEST",
        setup_mode="STANDARD",
        side="LONG",
        provenance_id=provenance.record_id,
        strategy_version="strategy-v1",
        parameter_version="params-v1",
        registry_version="registry-v1",
        registry_hash="r" * 64,
        cost_model_version="cost-v1",
        created_at=stamp,
        submission_status="NOT_SUBMITTED",
        **(
            {"policy_version": policy_version, "max_approved_entry": "101"}
            if policy_version is not None else {}
        ),
        **terms,
    )
    records: tuple[ImmutableRecord, ...] = (provenance, event, evaluation, signal, plan, shadow)
    with sqlite3.connect(path) as connection:
        connection.executemany(
            "INSERT INTO immutable_records VALUES (?, ?, ?, ?, ?)",
            [
                (
                    record.record_id,
                    record.record_type,
                    record.canonical_hash,
                    record._identity_json,
                    record._payload_json,
                )
                for record in records
            ],
        )
    return shadow.record_id


def make_config(
    tmp_path: Path, *, scenario: str | None = "1pct", mode: str = "POST_ACTIVATION"
) -> OperatorConfig:
    return OperatorConfig.model_validate(
        {
            "runtime_evidence_path": str(tmp_path / "runtime.sqlite"),
            "operator_ledger_path": str(tmp_path / "operator.sqlite"),
            "credential_path": str(tmp_path / "credential.json"),
            "allowed_hosts": ["operator.test"],
            "allowed_origin": "https://operator.test",
            "reference_scenario": scenario,
            "approval_mode": mode,
        }
    )


def make_credential() -> OperatorCredential:
    return OperatorCredential(
        access_token="A" * 48,
        session_signing_secret="B" * 48,
    )


def test_operator_config_rejects_shared_db_or_nonloopback(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    with pytest.raises(ValueError, match="distinct"):
        OperatorConfig.model_validate(
            {**config.model_dump(), "operator_ledger_path": config.runtime_evidence_path}
        )
    with pytest.raises(ValueError, match="loopback"):
        OperatorConfig.model_validate({**config.model_dump(), "bind_host": "0.0.0.0"})


def test_credential_separation() -> None:
    with pytest.raises(ValueError, match="separate"):
        OperatorCredential(access_token="A" * 48, session_signing_secret="A" * 48)
