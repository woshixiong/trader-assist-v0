from __future__ import annotations

import json
import os
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


def _taken_bundle(
    tmp_path: Path,
    *,
    side: Side = Side.LONG,
    fast: bool = True,
    decision_journal: Path | None = None,
):
    output = _output(side, fast)
    plan = build_plan(
        strategy_output=output,
        reference=output.raw_entry_low,
        equity=Decimal("1000"),
        sz_decimals=3,
    )
    decision_journal = decision_journal or tmp_path / "decision.jsonl"
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


def _rehash(payload: dict[str, object]) -> dict[str, object]:
    import trader_assist_v0.first_launch.pilot_review as module

    digest = module._digest(payload)
    payload["report_id"] = payload["canonical_hash"] = digest
    return payload


def _payload(report: PilotReviewReportV1) -> dict[str, object]:
    return json.loads(report.canonical_json())


def _two_outcome_report(tmp_path: Path) -> PilotReviewReportV1:
    decisions = tmp_path / "decisions.jsonl"
    first_journal, first_bundle = _taken_bundle(
        tmp_path, decision_journal=decisions, side=Side.LONG, fast=True
    )
    second_journal, second_bundle = _taken_bundle(
        tmp_path, decision_journal=decisions, side=Side.SHORT, fast=False
    )
    assert first_journal == second_journal == decisions
    outcomes = tmp_path / "outcomes.jsonl"
    append_outcome(outcomes, outcome=_outcome(first_bundle, side=Side.LONG))
    append_outcome(outcomes, outcome=_outcome(second_bundle, side=Side.SHORT))
    return build_pilot_review(decisions, outcomes)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload["r_multiple_summary"].update({"total": "0"}),
        lambda payload: payload["r_multiple_summary"].update(
            {"count": 0, "total": "0", "minimum": None, "maximum": None}
        ),
        lambda payload: payload["mfe_summary"].update(
            {"count": 0, "total": "0", "minimum": None, "maximum": None}
        ),
        lambda payload: payload["mae_summary"].update(
            {"count": 0, "total": "0", "minimum": None, "maximum": None}
        ),
        lambda payload: payload["deviation_summary"].update(
            {"nonzero_entry_deviation": 0, "total_absolute_entry_deviation": "1"}
        ),
        lambda payload: payload["deviation_summary"].update(
            {"nonzero_quantity_deviation": 1, "total_absolute_quantity_deviation": "0"}
        ),
        lambda payload: payload["learning_finding_counts"].update({"ENTRY_DEVIATION": 0}),
        lambda payload: payload["learning_finding_counts"].update({"SIZE_DEVIATION": 0}),
        lambda payload: payload["learning_finding_counts"].update({"AMBIGUOUS_PATH": 1}),
        lambda payload: payload["learning_finding_counts"].update({"INSUFFICIENT_EVIDENCE": 1}),
        lambda payload: payload["financial_summary"].update(
            {"total_fees": "0", "total_net_pnl": "2"}
        ),
        lambda payload: payload["learning_finding_counts"].update({"FEE_DRAG": 0}),
    ],
)
def test_coherently_rehashed_aggregate_forgery_fails(tmp_path: Path, mutate) -> None:
    decision_journal, bundle = _taken_bundle(tmp_path)
    outcome_journal = tmp_path / "outcome.jsonl"
    append_outcome(outcome_journal, outcome=_outcome(bundle))
    report = build_pilot_review(decision_journal, outcome_journal)
    forged = _payload(report)
    mutate(forged)
    with pytest.raises(PilotReviewError):
        PilotReviewReportV1(_rehash(forged))


def test_coherently_rehashed_multi_observation_total_outside_bounds_fails(tmp_path: Path) -> None:
    report = _two_outcome_report(tmp_path)
    forged = _payload(report)
    summary = forged["r_multiple_summary"]
    assert isinstance(summary, dict) and summary["count"] == 2
    summary["total"] = "999"
    with pytest.raises(PilotReviewError, match="STATISTIC"):
        PilotReviewReportV1(_rehash(forged))


def test_plan_followed_mathematical_range_rejects_coherent_rehash(tmp_path: Path) -> None:
    decision_journal, bundle = _taken_bundle(tmp_path)
    outcomes = tmp_path / "outcomes.jsonl"
    append_outcome(outcomes, outcome=_outcome(bundle))
    forged = _payload(build_pilot_review(decision_journal, outcomes))
    deviation = forged["deviation_summary"]
    findings = forged["learning_finding_counts"]
    assert isinstance(deviation, dict) and isinstance(findings, dict)
    deviation["nonzero_entry_deviation"] = 1
    deviation["total_absolute_entry_deviation"] = "1"
    deviation["nonzero_quantity_deviation"] = 1
    deviation["total_absolute_quantity_deviation"] = "1"
    findings["ENTRY_DEVIATION"] = 1
    findings["SIZE_DEVIATION"] = 1
    findings["PLAN_FOLLOWED"] = 1
    with pytest.raises(PilotReviewError, match="FINDING"):
        PilotReviewReportV1(_rehash(forged))


@pytest.mark.parametrize("journal_kind", ("decision", "outcome"))
def test_final_verification_rejects_equal_byte_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, journal_kind: str
) -> None:
    import trader_assist_v0.first_launch.pilot_review as module

    decision_journal, bundle = _taken_bundle(tmp_path)
    outcome_journal = tmp_path / "outcome.jsonl"
    append_outcome(outcome_journal, outcome=_outcome(bundle))
    target = decision_journal if journal_kind == "decision" else outcome_journal
    original = module._build_payload

    def replace(*args, **kwargs):
        replacement = target.with_name(target.name + ".replacement")
        replacement.write_bytes(target.read_bytes())
        replacement.replace(target)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "_build_payload", replace)
    with pytest.raises(PilotReviewError, match="SOURCE_CHANGED"):
        build_pilot_review(decision_journal, outcome_journal)


def test_final_verification_rejects_symlink_and_missing_source_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import trader_assist_v0.first_launch.pilot_review as module

    missing = tmp_path / "missing.jsonl"
    original = module._build_payload

    def create_missing(*args, **kwargs):
        missing.write_bytes(b"")
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "_build_payload", create_missing)
    with pytest.raises(PilotReviewError, match="SOURCE_CHANGED"):
        build_pilot_review(missing, tmp_path / "missing-outcomes")

    monkeypatch.setattr(module, "_build_payload", original)
    decision_journal, bundle = _taken_bundle(tmp_path)
    outcome_journal = tmp_path / "outcome.jsonl"
    append_outcome(outcome_journal, outcome=_outcome(bundle))

    def replace_with_symlink(*args, **kwargs):
        target = decision_journal.with_name("target.jsonl")
        target.write_bytes(decision_journal.read_bytes())
        decision_journal.unlink()
        decision_journal.symlink_to(target)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "_build_payload", replace_with_symlink)
    with pytest.raises(PilotReviewError, match="SOURCE_TARGET_INVALID"):
        build_pilot_review(decision_journal, outcome_journal)


def _reverse_objects(value: object) -> object:
    if isinstance(value, dict):
        return {key: _reverse_objects(value[key]) for key in reversed(value)}
    if isinstance(value, list):
        return [_reverse_objects(item) for item in value]
    return value


def test_terminal_is_canonical_and_renders_all_evidence_sections(tmp_path: Path) -> None:
    decision_journal, bundle = _taken_bundle(tmp_path)
    outcomes = tmp_path / "outcomes.jsonl"
    append_outcome(outcomes, outcome=_outcome(bundle))
    report = build_pilot_review(decision_journal, outcomes)
    reversed_payload = _reverse_objects(_payload(report))
    assert isinstance(reversed_payload, dict)
    reordered = PilotReviewReportV1(_rehash(reversed_payload))
    rendered = render_pilot_review_terminal(report)
    assert rendered == render_pilot_review_terminal(
        PilotReviewReportV1.from_json(report.canonical_json())
    )
    assert rendered == render_pilot_review_terminal(reordered)
    for token in (
        "OFFLINE REVIEW ONLY",
        "NOT SUBMITTED",
        "decision_journal_sha256",
        "outcome_journal_sha256",
        "decision_record_hashes",
        "outcome_ids",
        "Decision summary",
        "Coverage: 1/1",
        "Outcome summary",
        "Financial summary",
        "Deviation summary",
        "R summary",
        "MFE summary",
        "MAE summary",
        "Replay coverage",
        "Replay paths",
        "Finding counts",
        "Unavailable metrics",
        "Authority boundary",
    ):
        assert token in rendered
    assert "recommend" not in rendered.lower()


@pytest.mark.parametrize("summary_name", ("r_multiple_summary", "mfe_summary", "mae_summary"))
def test_summary_count_two_requires_realizable_extrema_total(
    tmp_path: Path, summary_name: str
) -> None:
    report = _two_outcome_report(tmp_path)
    forged = _payload(report)
    summary = forged[summary_name]
    assert isinstance(summary, dict) and summary["count"] == 2
    summary.update({"minimum": "0", "maximum": "10", "total": "5"})
    with pytest.raises(PilotReviewError, match="STATISTIC"):
        PilotReviewReportV1(_rehash(forged))

    summary["total"] = "10"
    assert PilotReviewReportV1(_rehash(forged)).payload[summary_name] == summary


def test_summary_count_three_extrema_inclusive_bounds_are_enforced() -> None:
    import trader_assist_v0.first_launch.pilot_review as module

    for total in ("9", "21"):
        with pytest.raises(PilotReviewError, match="STATISTIC"):
            module._validate_summary(
                {"count": 3, "total": total, "minimum": "0", "maximum": "10"},
                3,
                "PILOT_REVIEW_STATISTIC_INVALID",
            )
    module._validate_summary(
        {"count": 3, "total": "10", "minimum": "0", "maximum": "10"},
        3,
        "PILOT_REVIEW_STATISTIC_INVALID",
    )
    module._validate_summary(
        {"count": 3, "total": "20", "minimum": "0", "maximum": "10"},
        3,
        "PILOT_REVIEW_STATISTIC_INVALID",
    )


def _set_sign_summary(
    payload: dict[str, object], *, positive: int, zero: int, negative: int, net: str
) -> None:
    outcome = payload["outcome_summary"]
    financial = payload["financial_summary"]
    assert isinstance(outcome, dict) and isinstance(financial, dict)
    outcome.update(
        {
            "positive_net_pnl": positive,
            "zero_net_pnl": zero,
            "negative_net_pnl": negative,
        }
    )
    fees = Decimal(str(financial["total_fees"]))
    net_value = Decimal(net)
    financial["total_net_pnl"] = net
    financial["total_gross_pnl"] = str(net_value + fees)


@pytest.mark.parametrize(
    "positive,zero,negative,net",
    (
        (1, 0, 0, "0"),
        (1, 0, 0, "-1"),
        (0, 0, 1, "0"),
        (0, 0, 1, "1"),
        (0, 1, 0, "1"),
    ),
)
def test_coherently_rehashed_pnl_sign_contradictions_fail(
    tmp_path: Path, positive: int, zero: int, negative: int, net: str
) -> None:
    decision_journal, bundle = _taken_bundle(tmp_path)
    outcomes = tmp_path / "outcomes.jsonl"
    append_outcome(outcomes, outcome=_outcome(bundle))
    forged = _payload(build_pilot_review(decision_journal, outcomes))
    _set_sign_summary(forged, positive=positive, zero=zero, negative=negative, net=net)
    with pytest.raises(PilotReviewError, match="FINANCIAL"):
        PilotReviewReportV1(_rehash(forged))


@pytest.mark.parametrize(
    "positive,zero,negative,net",
    ((1, 1, 0, "0"), (0, 1, 1, "0")),
)
def test_mixed_zero_pnl_sign_contradictions_fail(
    tmp_path: Path, positive: int, zero: int, negative: int, net: str
) -> None:
    forged = _payload(_two_outcome_report(tmp_path))
    _set_sign_summary(forged, positive=positive, zero=zero, negative=negative, net=net)
    with pytest.raises(PilotReviewError, match="FINANCIAL"):
        PilotReviewReportV1(_rehash(forged))


@pytest.mark.parametrize("journal_kind", ("decision", "outcome"))
def test_path_fingerprint_detects_same_inode_overwrite_at_observation_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, journal_kind: str
) -> None:
    import trader_assist_v0.first_launch.pilot_review as module

    source = tmp_path / f"{journal_kind}.jsonl"
    source.write_bytes(b"exact-bytes\n")
    original_stat = Path.stat
    nonfollowing_calls = 0

    def mutate_before_path_stat(self: Path, *, follow_symlinks: bool = True):
        nonlocal nonfollowing_calls
        if self == source and not follow_symlinks:
            nonfollowing_calls += 1
        if self == source and not follow_symlinks and nonfollowing_calls == 2:
            stamp = source.stat().st_mtime_ns + 1_000_000
            os.utime(source, ns=(stamp, stamp))
        return original_stat(self, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(module.Path, "stat", mutate_before_path_stat)
    with pytest.raises(PilotReviewError, match="SOURCE_CHANGED"):
        module._stable_regular_bytes(source, error_prefix=journal_kind.upper())


def test_path_fingerprint_detects_hard_link_metadata_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import trader_assist_v0.first_launch.pilot_review as module

    source = tmp_path / "decision.jsonl"
    alias = tmp_path / "decision-alias.jsonl"
    source.write_bytes(b"exact-bytes\n")
    os.link(source, alias)
    original_stat = Path.stat
    nonfollowing_calls = 0

    def mutate_via_alias(self: Path, *, follow_symlinks: bool = True):
        nonlocal nonfollowing_calls
        if self == source and not follow_symlinks:
            nonfollowing_calls += 1
        if self == source and not follow_symlinks and nonfollowing_calls == 2:
            stamp = alias.stat().st_mtime_ns + 1_000_000
            os.utime(alias, ns=(stamp, stamp))
        return original_stat(self, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(module.Path, "stat", mutate_via_alias)
    with pytest.raises(PilotReviewError, match="SOURCE_CHANGED"):
        module._stable_regular_bytes(source, error_prefix="DECISION")


def test_report_source_hashes_bind_exact_descriptor_captured_bytes(tmp_path: Path) -> None:
    import hashlib

    decision_journal, bundle = _taken_bundle(tmp_path)
    outcomes = tmp_path / "outcomes.jsonl"
    append_outcome(outcomes, outcome=_outcome(bundle))
    report = build_pilot_review(decision_journal, outcomes)
    evidence = report.payload["source_evidence"]
    assert isinstance(evidence, dict)
    assert (
        evidence["decision_journal_sha256"]
        == hashlib.sha256(decision_journal.read_bytes()).hexdigest()
    )
    assert evidence["outcome_journal_sha256"] == hashlib.sha256(outcomes.read_bytes()).hexdigest()
