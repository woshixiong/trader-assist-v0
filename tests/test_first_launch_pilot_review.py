from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from trader_assist_v0.first_launch.market_data import DataQualityState
from trader_assist_v0.first_launch.operator_demo import _candle, _output
from trader_assist_v0.first_launch.operator_review import (
    HumanDecision,
    append_decision,
    build_operator_card,
    create_shadow_order,
)
from trader_assist_v0.first_launch.outcome import (
    append_outcome,
    build_decision_bundle,
    build_manual_execution_import,
    build_outcome,
)
from trader_assist_v0.first_launch.pilot_review import (
    PilotReviewError,
    PilotReviewReportV1,
    build_pilot_review,
    render_pilot_review_terminal,
)
from trader_assist_v0.first_launch.strategy import Side, build_plan


def _taken_bundle(tmp_path: Path, *, side: Side = Side.LONG, fast: bool = True):
    output = _output(side, fast)
    plan = build_plan(
        strategy_output=output,
        reference=output.raw_entry_low,
        equity=Decimal("1000"),
        sz_decimals=3,
    )
    decision_journal = tmp_path / "decision.jsonl"
    card = build_operator_card(plan, now=plan.created_at, quality=DataQualityState.READY)
    shadow = create_shadow_order(card)
    decision = append_decision(
        decision_journal,
        card=card,
        shadow_order=shadow,
        decision=HumanDecision.TAKEN,
        timestamp=plan.created_at,
        reason="manual review",
    )
    bundle = build_decision_bundle(
        card=card,
        shadow_order=shadow,
        decision_record=decision,
        plan=plan,
    )
    return decision_journal, bundle


def _outcome(bundle, *, side: Side = Side.LONG):
    first = _candle(26 * 300_000)
    second = _candle(27 * 300_000, high="105", low="95")
    from datetime import UTC, datetime

    entry = datetime.fromtimestamp((first.open_time_ms + 1_000) / 1_000, tz=UTC)
    exit = datetime.fromtimestamp((second.open_time_ms + 1_000) / 1_000, tz=UTC)
    execution = build_manual_execution_import(
        decision_hash=bundle.decision_hash,
        side=side,
        entry_fills=[
            {"timestamp": entry.isoformat(), "price": "100", "quantity": "1", "fee": "0.1"}
        ],
        exit_fills=[{"timestamp": exit.isoformat(), "price": "102", "quantity": "1", "fee": "0.2"}],
    )
    return build_outcome(bundle=bundle, manual_execution=execution, candles=(first, second))


def test_empty_journals_are_canonical_and_explicitly_offline(tmp_path: Path) -> None:
    report = build_pilot_review(tmp_path / "missing-decisions", tmp_path / "missing-outcomes")
    assert report.payload["coverage_summary"] == {
        "matched_outcomes": 0,
        "missing_taken_outcomes": 0,
        "numerator": 0,
        "denominator": 0,
    }
    assert report.payload["financial_summary"] == {
        "total_fees": "0",
        "total_gross_pnl": "0",
        "total_net_pnl": "0",
    }
    assert PilotReviewReportV1.from_json(report.canonical_json()) == report
    rendered = render_pilot_review_terminal(report)
    assert "OFFLINE REVIEW ONLY" in rendered and "NOT SUBMITTED" in rendered
    assert "Coverage: 0/0" in rendered


def test_matching_taken_outcome_is_byte_bound_and_deterministic(tmp_path: Path) -> None:
    decision_journal, bundle = _taken_bundle(tmp_path)
    outcome_journal = tmp_path / "outcome.jsonl"
    append_outcome(outcome_journal, outcome=_outcome(bundle))
    before = (decision_journal.read_bytes(), outcome_journal.read_bytes())
    first = build_pilot_review(decision_journal, outcome_journal)
    second = build_pilot_review(decision_journal, outcome_journal)
    assert first == second
    assert first.report_id == first.canonical_hash
    assert first.payload["coverage_summary"] == {
        "matched_outcomes": 1,
        "missing_taken_outcomes": 0,
        "numerator": 1,
        "denominator": 1,
    }
    assert first.payload["outcome_summary"]["long"] == 1
    assert first.payload["financial_summary"]["total_net_pnl"] == "1.7"
    assert (decision_journal.read_bytes(), outcome_journal.read_bytes()) == before


def test_missing_taken_outcome_is_not_a_zero_pnl_observation(tmp_path: Path) -> None:
    decision_journal, _ = _taken_bundle(tmp_path)
    report = build_pilot_review(decision_journal, tmp_path / "missing-outcomes")
    assert report.payload["coverage_summary"] == {
        "matched_outcomes": 0,
        "missing_taken_outcomes": 1,
        "numerator": 0,
        "denominator": 1,
    }
    assert report.payload["outcome_summary"]["zero_net_pnl"] == 0
    assert report.payload["r_multiple_summary"] == {
        "count": 0,
        "total": "0",
        "minimum": None,
        "maximum": None,
    }


def test_coherently_rehashed_false_authority_and_noncanonical_json_fail(tmp_path: Path) -> None:
    import trader_assist_v0.first_launch.pilot_review as module

    report = build_pilot_review(tmp_path / "missing-decisions", tmp_path / "missing-outcomes")
    forged = json.loads(report.canonical_json())
    boundary = forged["authority_boundary"]
    assert isinstance(boundary, dict)
    boundary["runtime_authorized"] = True
    digest = module._digest(forged)
    forged["report_id"] = forged["canonical_hash"] = digest
    with pytest.raises(PilotReviewError, match="AUTHORITY"):
        PilotReviewReportV1(forged)
    with pytest.raises(PilotReviewError, match="CANONICAL"):
        PilotReviewReportV1.from_json(report.canonical_json().replace(b"{", b"{ ", 1))


def test_symlinked_source_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target.jsonl"
    target.write_bytes(b"")
    link = tmp_path / "link.jsonl"
    link.symlink_to(target)
    with pytest.raises(PilotReviewError, match="TARGET_INVALID"):
        build_pilot_review(link, tmp_path / "missing-outcomes")
