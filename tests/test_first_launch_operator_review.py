from __future__ import annotations

import copy
import os
import subprocess
import sys
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import decimal_to_canonical_string
from trader_assist_v0.first_launch import __all__
from trader_assist_v0.first_launch.market_data import DataQualityState
from trader_assist_v0.first_launch.operator_demo import _output, _wait
from trader_assist_v0.first_launch.operator_review import (
    HumanDecision,
    OperatorReviewError,
    append_decision,
    build_operator_card,
    create_shadow_order,
    read_journal,
    render_terminal,
)
from trader_assist_v0.first_launch.strategy import Side, Signal, SignalState, build_plan


def _plan(side: Side = Side.LONG, fast: bool = True):
    output = _output(side, fast)
    return build_plan(
        strategy_output=output,
        reference=output.raw_entry_low,
        equity=Decimal("1000"),
        sz_decimals=3,
    )


def _card(side: Side = Side.LONG, fast: bool = True):
    plan = _plan(side, fast)
    return build_operator_card(plan, now=plan.created_at, quality=DataQualityState.READY)


def test_wait_and_long_short_fast_standard_matrix() -> None:
    wait = _wait()
    card = build_operator_card(wait, now=_plan().created_at, quality=DataQualityState.READY)
    assert not card.actionable and card.payload["lifecycle_state"] in {"WAIT", "WATCH"}
    for side in Side:
        for fast in (True, False):
            review = _card(side, fast)
            assert review.actionable
            assert review.payload["side"] == side.value
            assert review.payload["speed"] == ("FAST" if fast else "STANDARD")
            assert review.payload["submission_status"] == "NOT_SUBMITTED"


def test_card_is_exact_decimal_hashed_and_deterministic() -> None:
    plan = _plan()
    first = build_operator_card(plan, now=plan.created_at, quality=DataQualityState.READY)
    second = build_operator_card(plan, now=plan.created_at, quality=DataQualityState.READY)
    assert first.payload == second.payload and first.canonical_hash == second.canonical_hash
    assert first.payload["entry_low"] == "99"
    assert first.payload["planned_risk"] == decimal_to_canonical_string(plan.planned_risk)
    assert first.payload["risk_percent"] == decimal_to_canonical_string(
        plan.planned_risk / plan.account_equity * Decimal("100")
    )
    text = render_terminal(first)
    for label in (
        "OFFLINE REVIEW ONLY",
        "MANUAL EXECUTION REQUIRED",
        "NOT SUBMITTED",
        "DO NOT CHASE",
    ):
        assert label in text
    assert "MANUAL ORDER:" in text and "float" not in first.canonical_json().decode()


def test_nonready_expired_nonactionable_and_terminal_signals_fail_closed() -> None:
    plan = _plan()
    with pytest.raises(OperatorReviewError):
        build_operator_card(plan, now=plan.created_at, quality=DataQualityState.STALE)
    with pytest.raises(OperatorReviewError):
        build_operator_card(plan, now=plan.expires_at, quality=DataQualityState.READY)
    for state in (SignalState.TRIGGERED_FAST, SignalState.EXPIRED, SignalState.INVALIDATED):
        with pytest.raises(OperatorReviewError):
            build_operator_card(
                Signal(state, None, None, None, "manual"),
                now=plan.created_at,
                quality=DataQualityState.READY,
            )
    wait = build_operator_card(_wait(), now=plan.created_at, quality=DataQualityState.READY)
    with pytest.raises(OperatorReviewError):
        create_shadow_order(wait)


def test_mutated_plan_and_forged_card_or_shadow_are_rejected() -> None:
    plan = _plan()
    object.__setattr__(plan, "planned_risk", plan.planned_risk + Decimal("1"))
    with pytest.raises(OperatorReviewError):
        build_operator_card(plan, now=plan.created_at, quality=DataQualityState.READY)
    card = _card()
    with pytest.raises(OperatorReviewError):
        create_shadow_order(replace(card))
    shadow = create_shadow_order(card)
    with pytest.raises(OperatorReviewError):
        append_decision(
            Path("unused.jsonl"),
            card=card,
            shadow_order=copy.copy(shadow),
            decision=HumanDecision.TAKEN,
            timestamp=_plan().created_at,
            reason="copy is not issued",
        )


def test_journal_decisions_chain_and_duplicate_setup_rejection(tmp_path: Path) -> None:
    journal = tmp_path / "review.jsonl"
    cards = (_card(Side.LONG, True), _card(Side.SHORT, True), _card(Side.LONG, False))
    decisions = (HumanDecision.TAKEN, HumanDecision.SKIPPED, HumanDecision.REJECTED)
    records = []
    for sequence, (card, decision) in enumerate(zip(cards, decisions, strict=True), start=1):
        records.append(
            append_decision(
                journal,
                card=card,
                shadow_order=create_shadow_order(card),
                decision=decision,
                timestamp=_plan().created_at + timedelta(seconds=sequence),
                reason=f"review {sequence}",
            )
        )
    readback = read_journal(journal)
    assert [record.payload["decision"] for record in readback] == [item.value for item in decisions]
    assert [record.payload["sequence"] for record in readback] == [1, 2, 3]
    assert readback[1].payload["previous_record_hash"] == records[0].record_hash
    superseding = build_plan(
        strategy_output=_output(Side.LONG, True),
        reference=_output(Side.LONG, True).raw_entry_low,
        equity=Decimal("1000"),
        sz_decimals=3,
        supersedes_plan_id="a" * 64,
    )
    # A separately produced plan for the same strategy setup remains one decision only.
    duplicate = build_operator_card(
        superseding,
        now=superseding.created_at,
        quality=DataQualityState.READY,
    )
    with pytest.raises(OperatorReviewError, match="DUPLICATE_SETUP"):
        append_decision(
            journal,
            card=duplicate,
            shadow_order=create_shadow_order(duplicate),
            decision=HumanDecision.TAKEN,
            timestamp=superseding.created_at,
            reason="same setup different plan",
        )


@pytest.mark.parametrize(
    "raw",
    (
        b'{"unknown":true}\n',
        b'{"journal_version":"1"}\n',
        b"not-json\n",
        b"{}",
        b"\xff\n",
    ),
)
def test_journal_rejects_unknown_noncanonical_truncated_and_invalid_utf8(
    tmp_path: Path, raw: bytes
) -> None:
    journal = tmp_path / "bad.jsonl"
    journal.write_bytes(raw)
    with pytest.raises(OperatorReviewError):
        read_journal(journal)


def test_journal_reason_lock_symlink_nonregular_and_append_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    card = _card()
    shadow = create_shadow_order(card)
    journal = tmp_path / "review.jsonl"
    with pytest.raises(OperatorReviewError, match="REASON"):
        append_decision(
            journal,
            card=card,
            shadow_order=shadow,
            decision=HumanDecision.TAKEN,
            timestamp=_plan().created_at,
            reason="bad\nreason",
        )
    (tmp_path / "review.jsonl.lock").write_text("occupied", encoding="utf-8")
    with pytest.raises(OperatorReviewError, match="LOCKED"):
        append_decision(
            journal,
            card=card,
            shadow_order=shadow,
            decision=HumanDecision.TAKEN,
            timestamp=_plan().created_at,
            reason="locked",
        )
    (tmp_path / "review.jsonl.lock").unlink()
    append_decision(
        journal,
        card=card,
        shadow_order=shadow,
        decision=HumanDecision.TAKEN,
        timestamp=_plan().created_at,
        reason="valid",
    )
    before = journal.read_bytes()
    card2 = _card(Side.SHORT)
    import trader_assist_v0.first_launch.operator_review as review

    monkeypatch.setattr(
        review.os, "write", lambda _fd, _value: (_ for _ in ()).throw(OSError("fail"))
    )
    with pytest.raises(OperatorReviewError, match="APPEND_FAILED"):
        append_decision(
            journal,
            card=card2,
            shadow_order=create_shadow_order(card2),
            decision=HumanDecision.REJECTED,
            timestamp=_plan().created_at,
            reason="fail",
        )
    assert journal.read_bytes() == before
    directory = tmp_path / "directory"
    directory.mkdir()
    with pytest.raises(OperatorReviewError):
        read_journal(directory)
    link = tmp_path / "link.jsonl"
    os.symlink(journal, link)
    with pytest.raises(OperatorReviewError):
        read_journal(link)


def test_demo_cases_and_package_exports(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    environment = {**os.environ, "PYTHONPATH": str(root / "src")}
    for case in ("wait", "long-fast", "short-fast", "long-standard", "short-standard"):
        result = subprocess.run(
            [sys.executable, "-m", "trader_assist_v0.first_launch.operator_demo", "--case", case],
            cwd=root,
            env=environment,
            check=True,
            text=True,
            capture_output=True,
        )
        assert "DEMO | OFFLINE | NOT SUBMITTED" in result.stdout
    rejected = subprocess.run(
        [
            sys.executable,
            "-m",
            "trader_assist_v0.first_launch.operator_demo",
            "--case",
            "wait",
            "--decision",
            "TAKEN",
            "--journal",
            str(tmp_path / "wait.jsonl"),
        ],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
    )
    assert rejected.returncode != 0 and not (tmp_path / "wait.jsonl").exists()
    assert "build_operator_card" in __all__ and "_output" not in __all__
