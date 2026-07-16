from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import canonical_json_bytes, decimal_to_canonical_string
from trader_assist_v0.first_launch.market_data import DataQualityState
from trader_assist_v0.first_launch.operator_demo import _candle, _output
from trader_assist_v0.first_launch.operator_review import (
    HumanDecision,
    append_decision,
    build_operator_card,
    create_shadow_order,
)
from trader_assist_v0.first_launch.outcome import (
    DecisionBundleV1,
    ManualExecutionImportV1,
    OutcomeError,
    append_outcome,
    build_decision_bundle,
    build_manual_execution_import,
    build_outcome,
    read_outcome_journal,
)
from trader_assist_v0.first_launch.strategy import Side, build_plan


def _bundle(tmp_path: Path, side: Side = Side.LONG, fast: bool = True):
    output = _output(side, fast)
    plan = build_plan(
        strategy_output=output,
        reference=output.raw_entry_low,
        equity=Decimal("1000"),
        sz_decimals=3,
    )
    card = build_operator_card(plan, now=plan.created_at, quality=DataQualityState.READY)
    shadow = create_shadow_order(card)
    decision = append_decision(
        tmp_path / f"{side.value}-{fast}.jsonl",
        card=card,
        shadow_order=shadow,
        decision=HumanDecision.TAKEN,
        timestamp=plan.created_at,
        reason="manual review",
    )
    return build_decision_bundle(
        card=card, shadow_order=shadow, decision_record=decision, plan=plan
    ), plan


def _import(bundle, side: Side, *, quantity: str = "1"):
    first = _candle(26 * 300_000)
    second = _candle(27 * 300_000, high="105", low="95")
    entry_time = datetime.fromtimestamp((first.open_time_ms + 1_000) / 1_000, tz=UTC)
    exit_time = datetime.fromtimestamp((second.open_time_ms + 1_000) / 1_000, tz=UTC)
    return (
        build_manual_execution_import(
            decision_hash=bundle.decision_hash,
            side=side,
            entry_fills=[
                {
                    "timestamp": entry_time.isoformat(),
                    "price": "100",
                    "quantity": quantity,
                    "fee": "0.1",
                }
            ],
            exit_fills=[
                {
                    "timestamp": exit_time.isoformat(),
                    "price": "102",
                    "quantity": quantity,
                    "fee": "0.2",
                }
            ],
        ),
        (first, second),
    )


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
@pytest.mark.parametrize("fast", [True, False])
def test_closed_manual_outcomes_are_hash_bound_and_separate_path(
    tmp_path: Path, side: Side, fast: bool
) -> None:
    bundle, plan = _bundle(tmp_path, side, fast)
    execution, candles = _import(bundle, side)
    outcome = build_outcome(bundle=bundle, manual_execution=execution, candles=candles)
    assert outcome.payload["actual_execution_outcome"] == "CLOSED_MANUAL_EXECUTION"
    assert outcome.payload["hypothetical_plan_path"] in {
        "STOP_FIRST",
        "TP1_FIRST",
        "TP2_REACHED",
        "NO_PLAN_LEVEL_HIT",
        "AMBIGUOUS_SAME_CANDLE",
    }
    assert outcome.payload["weighted_entry"] == "100"
    assert outcome.payload["weighted_exit"] == "102"
    expected_gross = Decimal("2") if side is Side.LONG else Decimal("-2")
    assert outcome.payload["gross_pnl"] == str(expected_gross)
    assert outcome.payload["net_pnl"] == str(expected_gross - Decimal("0.3"))
    assert outcome.payload["planned_risk"] == decimal_to_canonical_string(plan.planned_risk)
    assert DecisionBundleV1.from_json(bundle.canonical_json()) == bundle
    assert ManualExecutionImportV1.from_json(execution.canonical_json()) == execution


def test_multiple_fills_deviations_and_inclusive_replay_window(tmp_path: Path) -> None:
    bundle, _ = _bundle(tmp_path)
    one, two = _candle(26 * 300_000), _candle(27 * 300_000, high="106", low="94")
    start = datetime.fromtimestamp((one.open_time_ms + 1_000) / 1_000, tz=UTC)
    middle = datetime.fromtimestamp((one.open_time_ms + 2_000) / 1_000, tz=UTC)
    finish = datetime.fromtimestamp((two.open_time_ms + 1_000) / 1_000, tz=UTC)
    later = datetime.fromtimestamp((two.open_time_ms + 2_000) / 1_000, tz=UTC)
    execution = build_manual_execution_import(
        decision_hash=bundle.decision_hash,
        side=Side.LONG,
        entry_fills=[
            {"timestamp": start.isoformat(), "price": "100", "quantity": "1", "fee": "0"},
            {"timestamp": middle.isoformat(), "price": "102", "quantity": "2", "fee": "0"},
        ],
        exit_fills=[
            {"timestamp": finish.isoformat(), "price": "104", "quantity": "1", "fee": "0"},
            {"timestamp": later.isoformat(), "price": "106", "quantity": "2", "fee": "0"},
        ],
    )
    outcome = build_outcome(bundle=bundle, manual_execution=execution, candles=(one, two))
    assert outcome.payload["weighted_entry"] == "101.3333333333333333333333333"
    assert outcome.payload["weighted_exit"] == "105.3333333333333333333333333"
    assert outcome.payload["replay_candle_hashes"] == [one.canonical_hash, two.canonical_hash]
    assert {"ENTRY_DEVIATION", "SIZE_DEVIATION"} <= set(outcome.payload["learning_findings"])


def test_import_rejects_noncanonical_financials_duplicate_json_and_open_quantity(
    tmp_path: Path,
) -> None:
    bundle, _ = _bundle(tmp_path)
    execution, _ = _import(bundle, Side.LONG)
    bad = dict(execution.payload)
    bad["entry_fills"] = [dict(execution.payload["entry_fills"][0], price="1e2")]
    bad["manual_execution_id"] = bad["canonical_hash"] = "0" * 64
    with pytest.raises(OutcomeError):
        ManualExecutionImportV1(bad)
    duplicate = execution.canonical_json().replace(
        b'"symbol":"ETH"', b'"symbol":"ETH","symbol":"ETH"'
    )
    with pytest.raises(OutcomeError):
        ManualExecutionImportV1.from_json(duplicate)
    unequal = dict(execution.payload)
    unequal["exit_fills"] = [dict(execution.payload["exit_fills"][0], quantity="2")]
    unequal["manual_execution_id"] = unequal["canonical_hash"] = "0" * 64
    with pytest.raises(OutcomeError):
        ManualExecutionImportV1(unequal)


def test_missing_candles_are_insufficient_and_journal_is_append_only(tmp_path: Path) -> None:
    bundle, _ = _bundle(tmp_path)
    execution, _ = _import(bundle, Side.LONG)
    outcome = build_outcome(bundle=bundle, manual_execution=execution, candles=())
    assert outcome.payload["replay_coverage"] == "INSUFFICIENT_EVIDENCE"
    assert outcome.payload["hypothetical_plan_path"] == "INSUFFICIENT_EVIDENCE"
    assert outcome.payload["mfe"] is None and outcome.payload["mae"] is None
    journal = tmp_path / "outcome.jsonl"
    append_outcome(journal, outcome=outcome)
    assert read_outcome_journal(journal) == (outcome,)
    with pytest.raises(OutcomeError, match="DUPLICATE"):
        append_outcome(journal, outcome=outcome)
    journal.write_bytes(canonical_json_bytes({"bad": True}) + b"\n")
    with pytest.raises(OutcomeError):
        read_outcome_journal(journal)


@pytest.mark.parametrize(
    ("high", "low", "expected"),
    (
        ("99", "96", "STOP_FIRST"),
        ("101", "99", "TP1_FIRST"),
        ("102", "99", "TP2_REACHED"),
        ("99", "98", "NO_PLAN_LEVEL_HIT"),
        ("101", "96", "AMBIGUOUS_SAME_CANDLE"),
    ),
)
def test_hypothetical_paths_never_change_actual_manual_pnl(
    tmp_path: Path, high: str, low: str, expected: str
) -> None:
    bundle, plan = _bundle(tmp_path)
    # The deterministic demo plan is near 99; use its frozen prices so every
    # category is based on levels from that exact immutable plan.
    high_value = {
        "99": plan.tp1 - Decimal("1"),
        "101": plan.tp1 + Decimal("1"),
        "102": plan.tp2 + Decimal("1"),
    }[high]
    low_value = {
        "96": plan.stop - Decimal("1"),
        "98": plan.stop + Decimal("0.1"),
        "99": plan.stop + Decimal("0.1"),
    }[low]
    candle = _candle(26 * 300_000, high=str(high_value), low=str(low_value))
    exit_candle = _candle(27 * 300_000, high="100", low="99")
    execution, _ = _import(bundle, Side.LONG)
    outcome = build_outcome(
        bundle=bundle, manual_execution=execution, candles=(candle, exit_candle)
    )
    assert outcome.payload["hypothetical_plan_path"] == expected
    assert outcome.payload["actual_execution_outcome"] == "CLOSED_MANUAL_EXECUTION"


def test_forged_card_and_non_taken_decision_cannot_close_a_manual_trade(tmp_path: Path) -> None:
    bundle, plan = _bundle(tmp_path)
    card = build_operator_card(plan, now=plan.created_at, quality=DataQualityState.READY)
    with pytest.raises(OutcomeError):
        build_decision_bundle(
            card=replace(card),
            shadow_order=create_shadow_order(card),
            decision_record=append_decision(
                tmp_path / "separate.jsonl",
                card=card,
                shadow_order=create_shadow_order(card),
                decision=HumanDecision.SKIPPED,
                timestamp=plan.created_at,
                reason="declined",
            ),
            plan=plan,
        )
    execution, candles = _import(bundle, Side.SHORT)
    with pytest.raises(OutcomeError, match="SIDE_MISMATCH"):
        build_outcome(bundle=bundle, manual_execution=execution, candles=candles)


@pytest.mark.parametrize(
    "field",
    [
        "gross_pnl",
        "net_pnl",
        "total_fees",
        "r_multiple",
        "hypothetical_plan_path",
        "learning_findings",
    ],
)
def test_refreshed_outcome_hash_cannot_replace_derivable_evidence(
    tmp_path: Path, field: str
) -> None:
    import trader_assist_v0.first_launch.outcome as module

    bundle, _ = _bundle(tmp_path)
    execution, candles = _import(bundle, Side.LONG)
    outcome = build_outcome(bundle=bundle, manual_execution=execution, candles=candles)
    forged = json.loads(outcome.canonical_json())
    forged[field] = "0" if field != "learning_findings" else []
    if field == "hypothetical_plan_path":
        forged[field] = "NO_PLAN_LEVEL_HIT"
    digest = module._digest(
        module.OUTCOME_HASH_DOMAIN, forged, omit=("outcome_id", "canonical_hash")
    )
    forged["outcome_id"] = forged["canonical_hash"] = digest
    with pytest.raises(OutcomeError, match="DERIVATION"):
        module.OutcomeRecordV1(forged)


def test_replacement_lock_is_never_removed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import trader_assist_v0.first_launch.outcome as module

    bundle, _ = _bundle(tmp_path)
    execution, _ = _import(bundle, Side.LONG)
    outcome = build_outcome(bundle=bundle, manual_execution=execution, candles=())
    journal = tmp_path / "outcomes.jsonl"
    lock = journal.with_name(journal.name + ".lock")
    original_write = module.os.write

    def replace_lock(fd: int, data: bytes) -> int:
        lock.unlink()
        lock.write_text("replacement", encoding="utf-8")
        return original_write(fd, data)

    monkeypatch.setattr(module.os, "write", replace_lock)
    with pytest.raises(OutcomeError, match="LOCK_IDENTITY_CHANGED"):
        append_outcome(journal, outcome=outcome)
    assert lock.read_text(encoding="utf-8") == "replacement"
