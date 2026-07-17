"""Deterministic, offline-only coverage reporting for First Launch journals."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

from trader_assist_v0.contracts.common import canonical_json_bytes, decimal_to_canonical_string
from trader_assist_v0.first_launch import operator_review
from trader_assist_v0.first_launch.operator_review import HumanDecision, JournalRecord
from trader_assist_v0.first_launch.outcome import OutcomeRecordV1, _outcome_journal_records

PILOT_REVIEW_VERSION = "1"
PILOT_REVIEW_HASH_DOMAIN = "trader-assist-v0/first-launch/pilot-review-report/v1"
_HASH_RE = re.compile(r"[0-9a-f]{64}\Z")
_DECIMAL_RE = re.compile(
    r"(?:0|[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]+|-(?:[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*))\Z"
)
_REPORT_FIELDS = frozenset(
    {
        "pilot_review_version",
        "report_id",
        "canonical_hash",
        "source_evidence",
        "decision_summary",
        "coverage_summary",
        "outcome_summary",
        "financial_summary",
        "deviation_summary",
        "r_multiple_summary",
        "mfe_summary",
        "mae_summary",
        "replay_summary",
        "learning_finding_counts",
        "unavailable_metrics",
        "authority_boundary",
    }
)
_UNAVAILABLE_METRICS = [
    "ACCOUNT_OBSERVATION_CONFIDENCE",
    "ALERT_LATENCY",
    "EXCHANGE_FILL_LATENCY",
    "SIGNAL_LATENCY",
    "SYSTEM_INCIDENTS",
    "WAIT_QUALITY",
]
_FINDINGS = [
    "PLAN_FOLLOWED",
    "ENTRY_DEVIATION",
    "SIZE_DEVIATION",
    "FEE_DRAG",
    "AMBIGUOUS_PATH",
    "INSUFFICIENT_EVIDENCE",
]
_PATHS = [
    "STOP_FIRST",
    "TP1_FIRST",
    "TP2_REACHED",
    "NO_PLAN_LEVEL_HIT",
    "AMBIGUOUS_SAME_CANDLE",
    "INSUFFICIENT_EVIDENCE",
]
_COVERAGE = ["COMPLETE", "INSUFFICIENT_EVIDENCE"]
_AUTHORITY_BOUNDARY: dict[str, object] = {
    "symbol": "ETH",
    "offline_only": True,
    "submission_status": "NOT_SUBMITTED",
    "manual_execution_required": True,
    "runtime_authorized": False,
    "account_authorized": False,
    "exchange_write_authorized": False,
    "strategy_change_authorized": False,
}


class PilotReviewError(ValueError):
    """A pilot-review input or report is outside offline-only authority."""


@dataclass(frozen=True)
class _SourceCapture:
    raw: bytes
    identity: tuple[int, int, int, int] | None


def _digest(payload: dict[str, object]) -> str:
    body = dict(payload)
    body.pop("report_id", None)
    body.pop("canonical_hash", None)
    return hashlib.sha256(
        PILOT_REVIEW_HASH_DOMAIN.encode("ascii") + b"\0" + canonical_json_bytes(body)
    ).hexdigest()


def _hash(value: object, code: str) -> str:
    if type(value) is not str or _HASH_RE.fullmatch(value) is None:
        raise PilotReviewError(code)
    return value


def _count(value: object, code: str) -> int:
    if type(value) is not int or value < 0:
        raise PilotReviewError(code)
    return value


def _decimal(value: object, code: str, *, nonnegative: bool = False) -> Decimal:
    if type(value) is not str or _DECIMAL_RE.fullmatch(value) is None:
        raise PilotReviewError(code)
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise PilotReviewError(code) from exc
    if not parsed.is_finite() or decimal_to_canonical_string(parsed) != value:
        raise PilotReviewError(code)
    if nonnegative and parsed < 0:
        raise PilotReviewError(code)
    return parsed


def _object(value: object, fields: set[str], code: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != fields:
        raise PilotReviewError(code)
    return cast(dict[str, object], value)


def _count_map(value: object, keys: list[str], code: str) -> dict[str, int]:
    source = _object(value, set(keys), code)
    return {key: _count(source[key], code) for key in keys}


def _decimal_map(
    value: object, keys: list[str], code: str, *, nonnegative: bool = False
) -> dict[str, Decimal]:
    source = _object(value, set(keys), code)
    return {key: _decimal(source[key], code, nonnegative=nonnegative) for key in keys}


def _report_object(raw: bytes) -> dict[str, object]:
    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=no_duplicates,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PilotReviewError("PILOT_REVIEW_JSON_INVALID") from exc
    if type(value) is not dict:
        raise PilotReviewError("PILOT_REVIEW_JSON_NOT_CANONICAL")
    try:
        canonical = canonical_json_bytes(value)
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise PilotReviewError("PILOT_REVIEW_JSON_INVALID") from exc
    if canonical != raw:
        raise PilotReviewError("PILOT_REVIEW_JSON_NOT_CANONICAL")
    return cast(dict[str, object], value)


def _identity(info: object) -> tuple[int, int, int, int]:
    stat_result = cast(Any, info)
    return (stat_result.st_dev, stat_result.st_ino, stat_result.st_size, stat_result.st_mtime_ns)


def _read_descriptor(fd: int, error: str) -> bytes:
    try:
        chunks: list[bytes] = []
        while chunk := os.read(fd, 64 * 1024):
            chunks.append(chunk)
        return b"".join(chunks)
    except OSError as exc:
        raise PilotReviewError(error) from exc


def _stable_regular_bytes(
    target: Path,
    *,
    error_prefix: str,
    expected: tuple[int, int, int, int] | None = None,
) -> _SourceCapture:
    """Read an exact regular file through a descriptor bound to its path identity."""
    try:
        before = target.lstat()
    except FileNotFoundError:
        if expected is None:
            return _SourceCapture(b"", None)
        raise PilotReviewError(f"PILOT_REVIEW_{error_prefix}_SOURCE_CHANGED") from None
    except OSError as exc:
        raise PilotReviewError(f"PILOT_REVIEW_{error_prefix}_SOURCE_READ_FAILED") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise PilotReviewError(f"PILOT_REVIEW_{error_prefix}_SOURCE_TARGET_INVALID")
    before_identity = _identity(before)
    if expected is not None and before_identity != expected:
        raise PilotReviewError(f"PILOT_REVIEW_{error_prefix}_SOURCE_CHANGED")
    try:
        fd = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise PilotReviewError(f"PILOT_REVIEW_{error_prefix}_SOURCE_CHANGED") from exc
    try:
        try:
            opened = os.fstat(fd)
        except OSError as exc:
            raise PilotReviewError(f"PILOT_REVIEW_{error_prefix}_SOURCE_READ_FAILED") from exc
        if not stat.S_ISREG(opened.st_mode):
            raise PilotReviewError(f"PILOT_REVIEW_{error_prefix}_SOURCE_TARGET_INVALID")
        identity = _identity(opened)
        if identity != before_identity or (expected is not None and identity != expected):
            raise PilotReviewError(f"PILOT_REVIEW_{error_prefix}_SOURCE_CHANGED")
        raw = _read_descriptor(fd, f"PILOT_REVIEW_{error_prefix}_SOURCE_READ_FAILED")
        try:
            after_read = os.fstat(fd)
        except OSError as exc:
            raise PilotReviewError(f"PILOT_REVIEW_{error_prefix}_SOURCE_READ_FAILED") from exc
        if _identity(after_read) != identity:
            raise PilotReviewError(f"PILOT_REVIEW_{error_prefix}_SOURCE_CHANGED")
        try:
            resolved = target.stat(follow_symlinks=False)
        except OSError as exc:
            raise PilotReviewError(f"PILOT_REVIEW_{error_prefix}_SOURCE_CHANGED") from exc
        if not stat.S_ISREG(resolved.st_mode) or _identity(resolved) != identity:
            raise PilotReviewError(f"PILOT_REVIEW_{error_prefix}_SOURCE_CHANGED")
        return _SourceCapture(raw, identity)
    finally:
        os.close(fd)


def _capture_journal(path: str | Path, *, outcome: bool) -> _SourceCapture:
    target = Path(path)
    error_prefix = "OUTCOME" if outcome else "DECISION"
    return _stable_regular_bytes(target, error_prefix=error_prefix)


def _verify_source(path: str | Path, capture: _SourceCapture, *, outcome: bool) -> None:
    target = Path(path)
    error_prefix = "OUTCOME" if outcome else "DECISION"
    if capture.identity is None:
        try:
            target.lstat()
        except FileNotFoundError:
            return
        except OSError as exc:
            raise PilotReviewError(f"PILOT_REVIEW_{error_prefix}_SOURCE_CHANGED") from exc
        raise PilotReviewError(f"PILOT_REVIEW_{error_prefix}_SOURCE_CHANGED")
    current = _stable_regular_bytes(target, error_prefix=error_prefix, expected=capture.identity)
    if current.raw != capture.raw:
        raise PilotReviewError(f"PILOT_REVIEW_{error_prefix}_SOURCE_CHANGED")


def _validated_inputs(
    decision_journal: str | Path, outcome_journal: str | Path
) -> tuple[
    _SourceCapture,
    tuple[JournalRecord, ...],
    _SourceCapture,
    tuple[dict[str, object], ...],
]:
    decisions_capture = _capture_journal(decision_journal, outcome=False)
    outcomes_capture = _capture_journal(outcome_journal, outcome=True)
    try:
        decisions = operator_review._validate_journal(decisions_capture.raw)
    except (ValueError, TypeError) as exc:
        raise PilotReviewError("PILOT_REVIEW_DECISION_JOURNAL_INVALID") from exc
    try:
        outcomes = _outcome_journal_records(outcomes_capture.raw)
    except (ValueError, TypeError) as exc:
        raise PilotReviewError("PILOT_REVIEW_OUTCOME_JOURNAL_INVALID") from exc
    _verify_source(decision_journal, decisions_capture, outcome=False)
    _verify_source(outcome_journal, outcomes_capture, outcome=True)
    return decisions_capture, decisions, outcomes_capture, outcomes


def _summary(values: list[Decimal]) -> dict[str, object]:
    if not values:
        return {"count": 0, "total": "0", "minimum": None, "maximum": None}
    return {
        "count": len(values),
        "total": decimal_to_canonical_string(sum(values, Decimal(0))),
        "minimum": decimal_to_canonical_string(min(values)),
        "maximum": decimal_to_canonical_string(max(values)),
    }


def _matched_outcomes(
    decisions: tuple[JournalRecord, ...], wrappers: tuple[dict[str, object], ...]
) -> tuple[dict[str, JournalRecord], list[OutcomeRecordV1]]:
    indexed = {record.record_hash: record for record in decisions}
    if len(indexed) != len(decisions):
        raise PilotReviewError("PILOT_REVIEW_DECISION_DUPLICATE_HASH")
    matched: list[OutcomeRecordV1] = []
    seen: set[str] = set()
    for wrapper in wrappers:
        outcome = OutcomeRecordV1(cast(dict[str, object], wrapper["outcome"]))
        decision_hash = _hash(wrapper.get("decision_hash"), "PILOT_REVIEW_OUTCOME_INVALID")
        if decision_hash != outcome.payload.get("decision_hash"):
            raise PilotReviewError("PILOT_REVIEW_OUTCOME_DECISION_MISMATCH")
        if decision_hash in seen:
            raise PilotReviewError("PILOT_REVIEW_OUTCOME_DUPLICATE_CORRESPONDENCE")
        seen.add(decision_hash)
        decision = indexed.get(decision_hash)
        if decision is None:
            raise PilotReviewError("PILOT_REVIEW_OUTCOME_ORPHAN")
        if decision.payload["decision"] != HumanDecision.TAKEN.value:
            raise PilotReviewError("PILOT_REVIEW_OUTCOME_DECISION_NOT_TAKEN")
        bundle = cast(dict[str, object], outcome.payload["derivation"])["bundle"]
        if type(bundle) is not dict or bundle.get("decision_record") != decision.payload:
            raise PilotReviewError("PILOT_REVIEW_EMBEDDED_DECISION_MISMATCH")
        matched.append(outcome)
    return indexed, matched


def _build_payload(
    decisions_raw: bytes,
    decisions: tuple[JournalRecord, ...],
    outcomes_raw: bytes,
    wrappers: tuple[dict[str, object], ...],
) -> dict[str, object]:
    indexed, outcomes = _matched_outcomes(decisions, wrappers)
    decision_counts = {key: 0 for key in ("taken", "skipped", "rejected", "fast", "standard")}
    for decision in decisions:
        value = cast(str, decision.payload["decision"])
        decision_counts[value.lower()] += 1
        speed = cast(str, decision.payload["signal_state"])
        decision_counts["fast" if speed == "TRIGGERED_FAST" else "standard"] += 1
    taken_hashes = {
        record_hash
        for record_hash, record in indexed.items()
        if record.payload["decision"] == HumanDecision.TAKEN.value
    }
    matched_hashes = {cast(str, outcome.payload["decision_hash"]) for outcome in outcomes}
    missing = len(taken_hashes - matched_hashes)
    outcome_counts = {
        key: 0
        for key in (
            "long",
            "short",
            "fast",
            "standard",
            "positive_net_pnl",
            "zero_net_pnl",
            "negative_net_pnl",
        )
    }
    coverage_counts = {key: 0 for key in _COVERAGE}
    path_counts = {key: 0 for key in _PATHS}
    finding_counts = {key: 0 for key in _FINDINGS}
    fees = Decimal(0)
    gross = Decimal(0)
    net = Decimal(0)
    nonzero_entry = 0
    nonzero_quantity = 0
    absolute_entry = Decimal(0)
    absolute_quantity = Decimal(0)
    r_values: list[Decimal] = []
    mfe_values: list[Decimal] = []
    mae_values: list[Decimal] = []
    for outcome in outcomes:
        outcome_payload = outcome.payload
        outcome_counts[cast(str, outcome_payload["side"]).lower()] += 1
        outcome_counts[cast(str, outcome_payload["speed"]).lower()] += 1
        net_value = _decimal(outcome_payload["net_pnl"], "PILOT_REVIEW_OUTCOME_INVALID")
        outcome_counts[
            "positive_net_pnl"
            if net_value > 0
            else "negative_net_pnl"
            if net_value < 0
            else "zero_net_pnl"
        ] += 1
        fees += _decimal(
            outcome_payload["total_fees"], "PILOT_REVIEW_OUTCOME_INVALID", nonnegative=True
        )
        gross += _decimal(outcome_payload["gross_pnl"], "PILOT_REVIEW_OUTCOME_INVALID")
        net += net_value
        entry = _decimal(outcome_payload["entry_deviation"], "PILOT_REVIEW_OUTCOME_INVALID")
        quantity = _decimal(outcome_payload["quantity_deviation"], "PILOT_REVIEW_OUTCOME_INVALID")
        if entry != 0:
            nonzero_entry += 1
            absolute_entry += abs(entry)
        if quantity != 0:
            nonzero_quantity += 1
            absolute_quantity += abs(quantity)
        r_values.append(_decimal(outcome_payload["r_multiple"], "PILOT_REVIEW_OUTCOME_INVALID"))
        for key, values in (("mfe", mfe_values), ("mae", mae_values)):
            if outcome_payload[key] is not None:
                values.append(_decimal(outcome_payload[key], "PILOT_REVIEW_OUTCOME_INVALID"))
        coverage = cast(str, outcome_payload["replay_coverage"])
        path = cast(str, outcome_payload["hypothetical_plan_path"])
        if coverage not in coverage_counts or path not in path_counts:
            raise PilotReviewError("PILOT_REVIEW_OUTCOME_INVALID")
        coverage_counts[coverage] += 1
        path_counts[path] += 1
        findings = outcome_payload["learning_findings"]
        if type(findings) is not list or any(
            type(item) is not str or item not in finding_counts for item in findings
        ):
            raise PilotReviewError("PILOT_REVIEW_FINDING_INVALID")
        if len(set(cast(list[str], findings))) != len(findings):
            raise PilotReviewError("PILOT_REVIEW_FINDING_INVALID")
        for finding in cast(list[str], findings):
            finding_counts[finding] += 1
    payload: dict[str, object] = {
        "pilot_review_version": PILOT_REVIEW_VERSION,
        "report_id": "",
        "canonical_hash": "",
        "source_evidence": {
            "decision_journal_sha256": hashlib.sha256(decisions_raw).hexdigest(),
            "outcome_journal_sha256": hashlib.sha256(outcomes_raw).hexdigest(),
            "decision_record_hashes": [record.record_hash for record in decisions],
            "outcome_ids": [cast(str, outcome.payload["outcome_id"]) for outcome in outcomes],
        },
        "decision_summary": {"total": len(decisions), **decision_counts},
        "coverage_summary": {
            "matched_outcomes": len(outcomes),
            "missing_taken_outcomes": missing,
            "numerator": len(outcomes),
            "denominator": decision_counts["taken"],
        },
        "outcome_summary": outcome_counts,
        "financial_summary": {
            "total_fees": decimal_to_canonical_string(fees),
            "total_gross_pnl": decimal_to_canonical_string(gross),
            "total_net_pnl": decimal_to_canonical_string(net),
        },
        "deviation_summary": {
            "nonzero_entry_deviation": nonzero_entry,
            "nonzero_quantity_deviation": nonzero_quantity,
            "total_absolute_entry_deviation": decimal_to_canonical_string(absolute_entry),
            "total_absolute_quantity_deviation": decimal_to_canonical_string(absolute_quantity),
        },
        "r_multiple_summary": _summary(r_values),
        "mfe_summary": _summary(mfe_values),
        "mae_summary": _summary(mae_values),
        "replay_summary": {"coverage_counts": coverage_counts, "path_counts": path_counts},
        "learning_finding_counts": finding_counts,
        "unavailable_metrics": list(_UNAVAILABLE_METRICS),
        "authority_boundary": dict(_AUTHORITY_BOUNDARY),
    }
    digest = _digest(payload)
    payload["report_id"] = digest
    payload["canonical_hash"] = digest
    return payload


def _validate_summary(value: object, matched: int, code: str) -> None:
    summary = _object(value, {"count", "total", "minimum", "maximum"}, code)
    count = _count(summary["count"], code)
    if count > matched:
        raise PilotReviewError(code)
    total = _decimal(summary["total"], code)
    minimum, maximum = summary["minimum"], summary["maximum"]
    if count == 0:
        if total != 0 or minimum is not None or maximum is not None:
            raise PilotReviewError(code)
        return
    low = _decimal(minimum, code) if minimum is not None else None
    high = _decimal(maximum, code) if maximum is not None else None
    if (
        low is None
        or high is None
        or low > high
        or (count == 1 and (total != low or total != high))
        or (count >= 2 and total < ((count - 1) * low) + high)
        or (count >= 2 and total > low + ((count - 1) * high))
    ):
        raise PilotReviewError(code)


def _validate_payload(payload: dict[str, object]) -> None:
    if (
        set(payload) != _REPORT_FIELDS
        or payload.get("pilot_review_version") != PILOT_REVIEW_VERSION
    ):
        raise PilotReviewError("PILOT_REVIEW_FIELDS_INVALID")
    report_id = _hash(payload.get("report_id"), "PILOT_REVIEW_HASH_INVALID")
    if report_id != payload.get("canonical_hash") or report_id != _digest(payload):
        raise PilotReviewError("PILOT_REVIEW_HASH_INVALID")
    evidence = _object(
        payload["source_evidence"],
        {
            "decision_journal_sha256",
            "outcome_journal_sha256",
            "decision_record_hashes",
            "outcome_ids",
        },
        "PILOT_REVIEW_SOURCE_INVALID",
    )
    _hash(evidence["decision_journal_sha256"], "PILOT_REVIEW_SOURCE_INVALID")
    _hash(evidence["outcome_journal_sha256"], "PILOT_REVIEW_SOURCE_INVALID")
    for key in ("decision_record_hashes", "outcome_ids"):
        values = evidence[key]
        if type(values) is not list:
            raise PilotReviewError("PILOT_REVIEW_SOURCE_INVALID")
        for value in values:
            _hash(value, "PILOT_REVIEW_SOURCE_INVALID")
        if len(set(cast(list[str], values))) != len(values):
            raise PilotReviewError("PILOT_REVIEW_SOURCE_INVALID")
    decisions = _count_map(
        payload["decision_summary"],
        ["total", "taken", "skipped", "rejected", "fast", "standard"],
        "PILOT_REVIEW_DECISION_SUMMARY_INVALID",
    )
    if (
        decisions["total"] != decisions["taken"] + decisions["skipped"] + decisions["rejected"]
        or decisions["total"] != decisions["fast"] + decisions["standard"]
        or decisions["total"] != len(cast(list[object], evidence["decision_record_hashes"]))
    ):
        raise PilotReviewError("PILOT_REVIEW_DECISION_SUMMARY_INVALID")
    coverage = _count_map(
        payload["coverage_summary"],
        ["matched_outcomes", "missing_taken_outcomes", "numerator", "denominator"],
        "PILOT_REVIEW_COVERAGE_INVALID",
    )
    if (
        coverage["numerator"] != coverage["matched_outcomes"]
        or coverage["denominator"] != decisions["taken"]
        or decisions["taken"] != coverage["matched_outcomes"] + coverage["missing_taken_outcomes"]
        or coverage["matched_outcomes"] != len(cast(list[object], evidence["outcome_ids"]))
    ):
        raise PilotReviewError("PILOT_REVIEW_COVERAGE_INVALID")
    outcomes = _count_map(
        payload["outcome_summary"],
        [
            "long",
            "short",
            "fast",
            "standard",
            "positive_net_pnl",
            "zero_net_pnl",
            "negative_net_pnl",
        ],
        "PILOT_REVIEW_OUTCOME_SUMMARY_INVALID",
    )
    matched = coverage["matched_outcomes"]
    if (
        outcomes["long"] + outcomes["short"] != matched
        or outcomes["fast"] + outcomes["standard"] != matched
        or outcomes["positive_net_pnl"] + outcomes["zero_net_pnl"] + outcomes["negative_net_pnl"]
        != matched
    ):
        raise PilotReviewError("PILOT_REVIEW_OUTCOME_SUMMARY_INVALID")
    financial = _decimal_map(
        payload["financial_summary"],
        ["total_fees", "total_gross_pnl", "total_net_pnl"],
        "PILOT_REVIEW_FINANCIAL_INVALID",
    )
    if (
        financial["total_fees"] < 0
        or financial["total_net_pnl"] != financial["total_gross_pnl"] - financial["total_fees"]
    ):
        raise PilotReviewError("PILOT_REVIEW_FINANCIAL_INVALID")
    positive = outcomes["positive_net_pnl"]
    zero = outcomes["zero_net_pnl"]
    negative = outcomes["negative_net_pnl"]
    net_total = financial["total_net_pnl"]
    if (
        (matched == 0 and net_total != 0)
        or (positive == 0 and negative == 0 and net_total != 0)
        or (positive > 0 and negative == 0 and net_total <= 0)
        or (negative > 0 and positive == 0 and net_total >= 0)
        or (zero == matched and net_total != 0)
        or (matched > 0 and positive == matched and net_total <= 0)
        or (matched > 0 and negative == matched and net_total >= 0)
    ):
        raise PilotReviewError("PILOT_REVIEW_FINANCIAL_INVALID")
    deviation = _object(
        payload["deviation_summary"],
        {
            "nonzero_entry_deviation",
            "nonzero_quantity_deviation",
            "total_absolute_entry_deviation",
            "total_absolute_quantity_deviation",
        },
        "PILOT_REVIEW_DEVIATION_INVALID",
    )
    deviation_counts: dict[str, int] = {}
    for count_key, total_key in (
        ("nonzero_entry_deviation", "total_absolute_entry_deviation"),
        ("nonzero_quantity_deviation", "total_absolute_quantity_deviation"),
    ):
        count = _count(deviation[count_key], "PILOT_REVIEW_DEVIATION_INVALID")
        total = _decimal(deviation[total_key], "PILOT_REVIEW_DEVIATION_INVALID", nonnegative=True)
        if count > matched or (count == 0) != (total == 0):
            raise PilotReviewError("PILOT_REVIEW_DEVIATION_INVALID")
        deviation_counts[count_key] = count
    replay = _object(
        payload["replay_summary"], {"coverage_counts", "path_counts"}, "PILOT_REVIEW_REPLAY_INVALID"
    )
    coverage_counts = _count_map(
        replay["coverage_counts"], _COVERAGE, "PILOT_REVIEW_REPLAY_INVALID"
    )
    path_counts = _count_map(replay["path_counts"], _PATHS, "PILOT_REVIEW_REPLAY_INVALID")
    if (
        sum(coverage_counts.values()) != matched
        or sum(path_counts.values()) != matched
        or coverage_counts["INSUFFICIENT_EVIDENCE"] != path_counts["INSUFFICIENT_EVIDENCE"]
        or coverage_counts["COMPLETE"] != sum(path_counts[key] for key in _PATHS[:-1])
    ):
        raise PilotReviewError("PILOT_REVIEW_REPLAY_INVALID")
    complete = coverage_counts["COMPLETE"]
    _validate_summary(payload["r_multiple_summary"], matched, "PILOT_REVIEW_STATISTIC_INVALID")
    _validate_summary(payload["mfe_summary"], matched, "PILOT_REVIEW_STATISTIC_INVALID")
    _validate_summary(payload["mae_summary"], matched, "PILOT_REVIEW_STATISTIC_INVALID")
    if (
        _count(
            _object(
                payload["r_multiple_summary"],
                {"count", "total", "minimum", "maximum"},
                "PILOT_REVIEW_STATISTIC_INVALID",
            )["count"],
            "PILOT_REVIEW_STATISTIC_INVALID",
        )
        != matched
        or _count(
            _object(
                payload["mfe_summary"],
                {"count", "total", "minimum", "maximum"},
                "PILOT_REVIEW_STATISTIC_INVALID",
            )["count"],
            "PILOT_REVIEW_STATISTIC_INVALID",
        )
        != complete
        or _count(
            _object(
                payload["mae_summary"],
                {"count", "total", "minimum", "maximum"},
                "PILOT_REVIEW_STATISTIC_INVALID",
            )["count"],
            "PILOT_REVIEW_STATISTIC_INVALID",
        )
        != complete
    ):
        raise PilotReviewError("PILOT_REVIEW_STATISTIC_INVALID")
    findings = _count_map(
        payload["learning_finding_counts"], _FINDINGS, "PILOT_REVIEW_FINDING_INVALID"
    )
    if any(value > matched for value in findings.values()):
        raise PilotReviewError("PILOT_REVIEW_FINDING_INVALID")
    if (
        findings["ENTRY_DEVIATION"] != deviation_counts["nonzero_entry_deviation"]
        or findings["SIZE_DEVIATION"] != deviation_counts["nonzero_quantity_deviation"]
        or findings["AMBIGUOUS_PATH"] != path_counts["AMBIGUOUS_SAME_CANDLE"]
        or findings["INSUFFICIENT_EVIDENCE"] != path_counts["INSUFFICIENT_EVIDENCE"]
        or findings["INSUFFICIENT_EVIDENCE"] != coverage_counts["INSUFFICIENT_EVIDENCE"]
        or (financial["total_fees"] == 0) != (findings["FEE_DRAG"] == 0)
    ):
        raise PilotReviewError("PILOT_REVIEW_FINDING_INVALID")
    lower = max(
        0,
        matched
        - deviation_counts["nonzero_entry_deviation"]
        - deviation_counts["nonzero_quantity_deviation"],
    )
    upper = matched - max(
        deviation_counts["nonzero_entry_deviation"],
        deviation_counts["nonzero_quantity_deviation"],
    )
    if not lower <= findings["PLAN_FOLLOWED"] <= upper:
        raise PilotReviewError("PILOT_REVIEW_FINDING_INVALID")
    if (
        payload["unavailable_metrics"] != _UNAVAILABLE_METRICS
        or payload["authority_boundary"] != _AUTHORITY_BOUNDARY
    ):
        raise PilotReviewError("PILOT_REVIEW_AUTHORITY_INVALID")


@dataclass(frozen=True)
class PilotReviewReportV1:
    """Canonical, evidence-bound aggregate of offline First Launch journals."""

    payload: dict[str, object]

    def __post_init__(self) -> None:
        _validate_payload(self.payload)

    @property
    def report_id(self) -> str:
        return cast(str, self.payload["report_id"])

    @property
    def canonical_hash(self) -> str:
        return cast(str, self.payload["canonical_hash"])

    def canonical_json(self) -> bytes:
        return canonical_json_bytes(self.payload)

    @classmethod
    def from_json(cls, raw: bytes) -> PilotReviewReportV1:
        return cls(_report_object(raw))


def build_pilot_review(
    decision_journal: str | Path, outcome_journal: str | Path
) -> PilotReviewReportV1:
    """Build an ETH-only report from two captured, validated local journals."""
    decision_capture, decisions, outcome_capture, wrappers = _validated_inputs(
        decision_journal, outcome_journal
    )
    report = PilotReviewReportV1(
        _build_payload(decision_capture.raw, decisions, outcome_capture.raw, wrappers)
    )
    _verify_source(decision_journal, decision_capture, outcome=False)
    _verify_source(outcome_journal, outcome_capture, outcome=True)
    return report


def render_pilot_review_terminal(report: PilotReviewReportV1) -> str:
    """Render a deterministic non-actionable terminal report."""
    if type(report) is not PilotReviewReportV1:
        raise PilotReviewError("PILOT_REVIEW_REPORT_INVALID")
    report.__post_init__()
    report_payload = report.payload
    source_evidence = cast(dict[str, object], report_payload["source_evidence"])
    coverage = cast(dict[str, object], report_payload["coverage_summary"])
    replay = cast(dict[str, object], report_payload["replay_summary"])

    def canonical(section: object) -> str:
        return canonical_json_bytes(section).decode("utf-8")

    return "\n".join(
        (
            "OFFLINE REVIEW ONLY — NOT SUBMITTED",
            f"Report identity: {report.report_id}",
            "Source evidence:",
            f"  decision_journal_sha256: {source_evidence['decision_journal_sha256']}",
            f"  outcome_journal_sha256: {source_evidence['outcome_journal_sha256']}",
            f"  decision_record_hashes: {canonical(source_evidence['decision_record_hashes'])}",
            f"  outcome_ids: {canonical(source_evidence['outcome_ids'])}",
            f"Decision summary: {canonical(report_payload['decision_summary'])}",
            f"Coverage: {coverage['numerator']}/{coverage['denominator']}",
            f"Outcome summary: {canonical(report_payload['outcome_summary'])}",
            f"Financial summary: {canonical(report_payload['financial_summary'])}",
            f"Deviation summary: {canonical(report_payload['deviation_summary'])}",
            f"R summary: {canonical(report_payload['r_multiple_summary'])}",
            f"MFE summary: {canonical(report_payload['mfe_summary'])}",
            f"MAE summary: {canonical(report_payload['mae_summary'])}",
            f"Replay coverage: {canonical(replay['coverage_counts'])}",
            f"Replay paths: {canonical(replay['path_counts'])}",
            f"Finding counts: {canonical(report_payload['learning_finding_counts'])}",
            f"Unavailable metrics: {canonical(report_payload['unavailable_metrics'])}",
            f"Authority boundary: {canonical(report_payload['authority_boundary'])}",
        )
    )
