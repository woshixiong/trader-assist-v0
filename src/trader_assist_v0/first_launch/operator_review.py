"""Offline-only operator review cards and an append-only human decision journal."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import weakref
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, cast

from trader_assist_v0.contracts.common import canonical_json_bytes, decimal_to_canonical_string
from trader_assist_v0.first_launch.market_data import DataQualityState
from trader_assist_v0.first_launch.strategy import (
    PlanError,
    Side,
    Signal,
    SignalState,
    StrategyOutput,
    TradePlan,
    lifecycle_state,
)

CARD_VERSION: Literal["1"] = "1"
JOURNAL_VERSION: Literal["1"] = "1"
SUBMISSION_STATUS: Literal["NOT_SUBMITTED"] = "NOT_SUBMITTED"
CARD_HASH_DOMAIN = "trader-assist-v0/first-launch/operator-review-card/v1"
SHADOW_HASH_DOMAIN = "trader-assist-v0/first-launch/shadow-order/v1"
JOURNAL_HASH_DOMAIN = "trader-assist-v0/first-launch/operator-review-journal/v1"
_HASH_RE = re.compile(r"[0-9a-f]{64}")
_MAX_REASON_LENGTH = 240
_ISSUED: dict[int, tuple[weakref.ReferenceType[object], str]] = {}


class OperatorReviewError(ValueError):
    """An object is outside the offline operator-review authority."""


class HumanDecision(StrEnum):
    TAKEN = "TAKEN"
    SKIPPED = "SKIPPED"
    REJECTED = "REJECTED"


def _sha256(domain: str, payload: dict[str, object]) -> str:
    material = domain.encode("ascii") + b"\0" + canonical_json_bytes(payload)
    return hashlib.sha256(material).hexdigest()


def _issue(value: object, fingerprint: str) -> object:
    key = id(value)

    def _release(reference: weakref.ReferenceType[object]) -> None:
        current = _ISSUED.get(key)
        if current is not None and current[0] is reference:
            del _ISSUED[key]

    _ISSUED[key] = (weakref.ref(value, _release), fingerprint)
    return value


def _is_issued(value: object, fingerprint: str) -> bool:
    issued = _ISSUED.get(id(value))
    return issued is not None and issued[0]() is value and issued[1] == fingerprint


def _exact_utc(value: object, error: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is not UTC:
        raise OperatorReviewError(error)
    return value


def _decimal(value: object, error: str) -> Decimal:
    if type(value) is not Decimal or not value.is_finite():
        raise OperatorReviewError(error)
    try:
        decimal_to_canonical_string(value)
    except (ValueError, ArithmeticError) as exc:
        raise OperatorReviewError(error) from exc
    return value


def _decimal_string(value: Decimal) -> str:
    return decimal_to_canonical_string(_decimal(value, "DECIMAL_INVALID"))


def _hash(value: object, error: str) -> str:
    if type(value) is not str or _HASH_RE.fullmatch(value) is None:
        raise OperatorReviewError(error)
    return value


def _signal_state(value: object, error: str) -> SignalState:
    if type(value) is not SignalState:
        raise OperatorReviewError(error)
    return value


def _quality(value: object) -> DataQualityState:
    if type(value) is not DataQualityState:
        raise OperatorReviewError("DATA_QUALITY_STATE_INVALID")
    return value


def _validate_plan(plan: object, *, now: datetime, quality: DataQualityState) -> SignalState:
    if type(plan) is not TradePlan:
        raise OperatorReviewError("TRADE_PLAN_AUTHORITY_INVALID")
    now = _exact_utc(now, "REVIEW_TIME_INVALID")
    quality = _quality(quality)
    try:
        # The production post-init performs issuance, correspondence, provenance,
        # identifier/hash, precision and financial consistency validation.
        plan.__post_init__()
        output = plan.strategy_output
        if type(output) is not StrategyOutput:
            raise PlanError("TRADE_PLAN_STRATEGY_AUTHORITY_INVALID")
        state = lifecycle_state(output, now=now, reference=plan.reference, quality=quality)
    except (PlanError, AttributeError, TypeError, ValueError) as exc:
        raise OperatorReviewError("TRADE_PLAN_AUTHORITY_INVALID") from exc
    return state


def _validate_display_signal(signal: object) -> Signal:
    if type(signal) is not Signal:
        raise OperatorReviewError("SIGNAL_AUTHORITY_INVALID")
    state = _signal_state(signal.state, "SIGNAL_AUTHORITY_INVALID")
    if state not in {SignalState.WAIT, SignalState.WATCH, SignalState.PREPARE}:
        raise OperatorReviewError("SIGNAL_STATE_NOT_DISPLAYABLE")
    if signal.side is not None and type(signal.side) is not Side:
        raise OperatorReviewError("SIGNAL_AUTHORITY_INVALID")
    if signal.speed is not None and signal.speed not in {"FAST", "STANDARD"}:
        raise OperatorReviewError("SIGNAL_AUTHORITY_INVALID")
    if signal.setup_id is not None:
        _hash(signal.setup_id, "SIGNAL_AUTHORITY_INVALID")
    if (
        type(signal.reason) is not str
        or not signal.reason
        or len(signal.reason) > _MAX_REASON_LENGTH
    ):
        raise OperatorReviewError("SIGNAL_AUTHORITY_INVALID")
    return signal


def _card_fingerprint(card: OperatorReviewCard) -> str:
    return _sha256(CARD_HASH_DOMAIN, card.payload)


@dataclass(frozen=True)
class OperatorReviewCard:
    """A canonically hashed, process-issued offline review surface."""

    card_id: str
    canonical_hash: str
    payload: dict[str, object]

    def __post_init__(self) -> None:
        _hash(self.card_id, "CARD_IDENTIFIER_INVALID")
        _hash(self.canonical_hash, "CARD_HASH_INVALID")
        if type(self.payload) is not dict or set(self.payload) != _CARD_FIELDS:
            raise OperatorReviewError("CARD_PAYLOAD_INVALID")
        if self.card_id != self.canonical_hash or self.card_id != _card_fingerprint(self):
            raise OperatorReviewError("CARD_HASH_INVALID")

    @property
    def actionable(self) -> bool:
        return self.payload["card_kind"] == "TRADE_PLAN"

    def canonical_json(self) -> bytes:
        return canonical_json_bytes(self.payload)


_CARD_FIELDS = frozenset(
    {
        "card_version",
        "card_kind",
        "submission_status",
        "manual_execution_required",
        "lifecycle_state",
        "data_quality_state",
        "signal_state",
        "symbol",
        "side",
        "speed",
        "setup_family",
        "setup_id",
        "plan_id",
        "plan_canonical_hash",
        "strategy_version",
        "configuration_version",
        "trade_plan_version",
        "decision_trigger_identity",
        "decision_trigger_open_time_ms",
        "decision_trigger_canonical_hash",
        "decision_trigger_received_at",
        "entry_low",
        "entry_high",
        "planned_entry",
        "chase_limit",
        "stop",
        "tp1",
        "tp2",
        "quantity",
        "notional",
        "planned_risk",
        "account_equity",
        "risk_percent",
        "created_at",
        "expires_at",
        "do_not_chase",
        "reason",
    }
)


def _make_card(payload: dict[str, object]) -> OperatorReviewCard:
    digest = _sha256(CARD_HASH_DOMAIN, payload)
    card = OperatorReviewCard(digest, digest, payload)
    return cast(OperatorReviewCard, _issue(card, _card_fingerprint(card)))


def _validated_card(value: object) -> OperatorReviewCard:
    if type(value) is not OperatorReviewCard:
        raise OperatorReviewError("CARD_AUTHORITY_INVALID")
    card = value
    try:
        card.__post_init__()
        if not _is_issued(card, _card_fingerprint(card)):
            raise OperatorReviewError("CARD_AUTHORITY_INVALID")
    except (AttributeError, TypeError, ValueError) as exc:
        raise OperatorReviewError("CARD_AUTHORITY_INVALID") from exc
    return card


def build_operator_card(
    value: TradePlan | Signal, *, now: datetime, quality: DataQualityState
) -> OperatorReviewCard:
    """Create a display-only card from a production-issued plan or benign Signal."""
    if type(value) is Signal:
        signal = _validate_display_signal(value)
        quality = _quality(quality)
        payload: dict[str, object] = {
            "card_version": CARD_VERSION,
            "card_kind": "SIGNAL",
            "submission_status": SUBMISSION_STATUS,
            "manual_execution_required": True,
            "lifecycle_state": signal.state.value,
            "data_quality_state": quality.value,
            "signal_state": signal.state.value,
            "symbol": "ETH",
            "side": None if signal.side is None else signal.side.value,
            "speed": signal.speed,
            "setup_family": None,
            "setup_id": signal.setup_id,
            "plan_id": None,
            "plan_canonical_hash": None,
            "strategy_version": None,
            "configuration_version": None,
            "trade_plan_version": None,
            "decision_trigger_identity": None,
            "decision_trigger_open_time_ms": None,
            "decision_trigger_canonical_hash": None,
            "decision_trigger_received_at": None,
            "entry_low": None,
            "entry_high": None,
            "planned_entry": None,
            "chase_limit": None,
            "stop": None,
            "tp1": None,
            "tp2": None,
            "quantity": None,
            "notional": None,
            "planned_risk": None,
            "account_equity": None,
            "risk_percent": None,
            "created_at": None,
            "expires_at": None,
            "do_not_chase": "DO NOT CHASE",
            "reason": signal.reason,
        }
        return _make_card(payload)

    plan = cast(TradePlan, value)
    state = _validate_plan(plan, now=now, quality=quality)
    if state not in {SignalState.TRIGGERED_FAST, SignalState.TRIGGERED_STANDARD}:
        raise OperatorReviewError("TRADE_PLAN_NOT_ACTIONABLE")
    risk_percent = (
        _decimal(plan.planned_risk, "TRADE_PLAN_AUTHORITY_INVALID")
        / _decimal(plan.account_equity, "TRADE_PLAN_AUTHORITY_INVALID")
        * Decimal("100")
    )
    payload = {
        "card_version": CARD_VERSION,
        "card_kind": "TRADE_PLAN",
        "submission_status": SUBMISSION_STATUS,
        "manual_execution_required": True,
        "lifecycle_state": state.value,
        "data_quality_state": quality.value,
        "signal_state": state.value,
        "symbol": plan.symbol,
        "side": plan.side.value,
        "speed": plan.speed,
        "setup_family": plan.family.value,
        "setup_id": plan.setup_id,
        "plan_id": plan.plan_id,
        "plan_canonical_hash": plan.canonical_hash,
        "strategy_version": plan.strategy_version,
        "configuration_version": plan.configuration_version,
        "trade_plan_version": plan.trade_plan_version,
        "decision_trigger_identity": list(plan.decision_trigger_identity),
        "decision_trigger_open_time_ms": plan.decision_trigger_open_time_ms,
        "decision_trigger_canonical_hash": plan.decision_trigger_canonical_hash,
        "decision_trigger_received_at": plan.decision_trigger_received_at.isoformat(),
        "entry_low": _decimal_string(plan.entry_low),
        "entry_high": _decimal_string(plan.entry_high),
        "planned_entry": _decimal_string(plan.planned_entry),
        "chase_limit": _decimal_string(plan.chase_limit),
        "stop": _decimal_string(plan.stop),
        "tp1": _decimal_string(plan.tp1),
        "tp2": _decimal_string(plan.tp2),
        "quantity": _decimal_string(plan.quantity),
        "notional": _decimal_string(plan.notional),
        "planned_risk": _decimal_string(plan.planned_risk),
        "account_equity": _decimal_string(plan.account_equity),
        "risk_percent": _decimal_string(risk_percent),
        "created_at": plan.created_at.isoformat(),
        "expires_at": plan.expires_at.isoformat(),
        "do_not_chase": plan.do_not_chase,
        "reason": plan.strategy_reason,
    }
    return _make_card(payload)


def render_terminal(card: OperatorReviewCard) -> str:
    """Render deterministic, display-only terminal text; it never submits anything."""
    card = _validated_card(card)
    p = card.payload
    lines = [
        "OFFLINE REVIEW ONLY",
        "MANUAL EXECUTION REQUIRED",
        "NOT SUBMITTED",
        "DO NOT CHASE",
        f"CARD {card.card_id}",
        f"STATE {p['lifecycle_state']} | QUALITY {p['data_quality_state']}",
    ]
    if not card.actionable:
        lines.extend((f"SIGNAL {p['signal_state']}", f"REASON {p['reason']}"))
        return "\n".join(lines)
    lines.extend(
        (
            f"{p['symbol']} {p['side']} {p['speed']} {p['setup_family']}",
            f"SETUP {p['setup_id']}",
            f"PLAN {p['plan_id']} HASH {p['plan_canonical_hash']}",
            f"ENTRY {p['entry_low']}..{p['entry_high']} @ {p['planned_entry']}",
            f"MAX ENTRY {p['chase_limit']} | STOP {p['stop']}",
            f"TP1 {p['tp1']} | TP2 {p['tp2']}",
            f"QTY {p['quantity']} | NOTIONAL {p['notional']}",
            f"RISK {p['planned_risk']} ({p['risk_percent']}%)",
            f"CREATED {p['created_at']} | EXPIRES {p['expires_at']}",
            "MANUAL ORDER: "
            + f"{p['symbol']} {p['side']} entry={p['planned_entry']} max_entry={p['chase_limit']} "
            + f"stop={p['stop']} tp1={p['tp1']} tp2={p['tp2']} quantity={p['quantity']}",
        )
    )
    return "\n".join(lines)


@dataclass(frozen=True)
class ShadowOrder:
    """A local proposal only; it represents neither an order nor a position."""

    shadow_order_id: str
    canonical_hash: str
    card_id: str
    card_hash: str
    setup_id: str
    setup_hash: str
    plan_id: str
    plan_hash: str
    manual_fields: dict[str, str]
    submission_status: Literal["NOT_SUBMITTED"] = SUBMISSION_STATUS
    manual_execution_required: Literal[True] = True

    def payload(self) -> dict[str, object]:
        return {
            "card_id": self.card_id,
            "card_hash": self.card_hash,
            "setup_id": self.setup_id,
            "setup_hash": self.setup_hash,
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "manual_fields": self.manual_fields,
            "submission_status": self.submission_status,
            "manual_execution_required": self.manual_execution_required,
        }

    def __post_init__(self) -> None:
        for value in (
            self.shadow_order_id,
            self.canonical_hash,
            self.card_id,
            self.card_hash,
            self.setup_id,
            self.setup_hash,
            self.plan_id,
            self.plan_hash,
        ):
            _hash(value, "SHADOW_ORDER_INVALID")
        if (
            type(self.manual_fields) is not dict
            or set(self.manual_fields) != _MANUAL_FIELD_NAMES
            or any(type(value) is not str for value in self.manual_fields.values())
            or self.submission_status != SUBMISSION_STATUS
            or self.manual_execution_required is not True
            or self.setup_hash != self.setup_id
            or self.plan_hash != self.plan_id
            or self.shadow_order_id != self.canonical_hash
            or self.shadow_order_id != _sha256(SHADOW_HASH_DOMAIN, self.payload())
        ):
            raise OperatorReviewError("SHADOW_ORDER_INVALID")


_MANUAL_FIELD_NAMES = frozenset(
    {
        "symbol",
        "side",
        "speed",
        "planned_entry",
        "chase_limit",
        "stop",
        "tp1",
        "tp2",
        "quantity",
        "notional",
    }
)


def _shadow_fingerprint(value: ShadowOrder) -> str:
    return _sha256(SHADOW_HASH_DOMAIN, value.payload())


def _validated_shadow(value: object) -> ShadowOrder:
    if type(value) is not ShadowOrder:
        raise OperatorReviewError("SHADOW_ORDER_AUTHORITY_INVALID")
    shadow = value
    try:
        shadow.__post_init__()
        if not _is_issued(shadow, _shadow_fingerprint(shadow)):
            raise OperatorReviewError("SHADOW_ORDER_AUTHORITY_INVALID")
    except (AttributeError, TypeError, ValueError) as exc:
        raise OperatorReviewError("SHADOW_ORDER_AUTHORITY_INVALID") from exc
    return shadow


def create_shadow_order(card: OperatorReviewCard) -> ShadowOrder:
    card = _validated_card(card)
    p = card.payload
    if (
        not card.actionable
        or p["lifecycle_state"]
        not in {
            SignalState.TRIGGERED_FAST.value,
            SignalState.TRIGGERED_STANDARD.value,
        }
        or p["data_quality_state"] != DataQualityState.READY.value
    ):
        raise OperatorReviewError("CARD_NOT_ACTIONABLE")
    manual = {key: cast(str, p[key]) for key in _MANUAL_FIELD_NAMES}
    raw = {
        "card_id": card.card_id,
        "card_hash": card.canonical_hash,
        "setup_id": cast(str, p["setup_id"]),
        "setup_hash": cast(str, p["setup_id"]),
        "plan_id": cast(str, p["plan_id"]),
        "plan_hash": cast(str, p["plan_canonical_hash"]),
        "manual_fields": manual,
        "submission_status": SUBMISSION_STATUS,
        "manual_execution_required": True,
    }
    digest = _sha256(SHADOW_HASH_DOMAIN, raw)
    shadow = ShadowOrder(
        digest,
        digest,
        card.card_id,
        card.canonical_hash,
        cast(str, p["setup_id"]),
        cast(str, p["setup_id"]),
        cast(str, p["plan_id"]),
        cast(str, p["plan_canonical_hash"]),
        manual,
    )
    return cast(ShadowOrder, _issue(shadow, _shadow_fingerprint(shadow)))


@dataclass(frozen=True)
class JournalRecord:
    payload: dict[str, object]

    @property
    def record_hash(self) -> str:
        return cast(str, self.payload["record_hash"])


_JOURNAL_FIELDS = frozenset(
    {
        "journal_version",
        "sequence",
        "previous_record_hash",
        "record_hash",
        "timestamp",
        "reason",
        "card_id",
        "card_hash",
        "setup_id",
        "setup_hash",
        "plan_id",
        "plan_hash",
        "shadow_order_id",
        "shadow_order_hash",
        "decision",
        "signal_state",
        "data_quality_state",
        "manual_execution_required",
        "submission_status",
    }
)


def _strict_json(raw: bytes) -> dict[str, object]:
    try:
        text = raw.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise OperatorReviewError("JOURNAL_JSON_INVALID") from exc
    if type(value) is not dict:
        raise OperatorReviewError("JOURNAL_JSON_INVALID")
    if canonical_json_bytes(value) != raw:
        raise OperatorReviewError("JOURNAL_JSON_NOT_CANONICAL")
    return cast(dict[str, object], value)


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("non-finite JSON")


def _reason(value: object) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > _MAX_REASON_LENGTH
        or "\r" in value
        or "\n" in value
    ):
        raise OperatorReviewError("JOURNAL_REASON_INVALID")
    return value


def _record_digest(payload: dict[str, object]) -> str:
    body = dict(payload)
    body.pop("record_hash", None)
    return _sha256(JOURNAL_HASH_DOMAIN, body)


def _validate_record(payload: dict[str, object], *, sequence: int, previous: str) -> JournalRecord:
    if set(payload) != _JOURNAL_FIELDS:
        raise OperatorReviewError("JOURNAL_FIELDS_INVALID")
    if (
        payload["journal_version"] != JOURNAL_VERSION
        or type(payload["sequence"]) is not int
        or payload["sequence"] != sequence
    ):
        raise OperatorReviewError("JOURNAL_SEQUENCE_INVALID")
    if payload["previous_record_hash"] != previous:
        raise OperatorReviewError("JOURNAL_CHAIN_INVALID")
    for field in (
        "previous_record_hash",
        "record_hash",
        "card_id",
        "card_hash",
        "setup_id",
        "setup_hash",
        "plan_id",
        "plan_hash",
        "shadow_order_id",
        "shadow_order_hash",
    ):
        _hash(payload[field], "JOURNAL_HASH_INVALID")
    _reason(payload["reason"])
    timestamp = payload["timestamp"]
    if type(timestamp) is not str:
        raise OperatorReviewError("JOURNAL_TIMESTAMP_INVALID")
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise OperatorReviewError("JOURNAL_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is not UTC or parsed.isoformat() != timestamp:
        raise OperatorReviewError("JOURNAL_TIMESTAMP_INVALID")
    if payload["decision"] not in {item.value for item in HumanDecision}:
        raise OperatorReviewError("JOURNAL_DECISION_INVALID")
    if payload["signal_state"] not in {
        SignalState.TRIGGERED_FAST.value,
        SignalState.TRIGGERED_STANDARD.value,
    }:
        raise OperatorReviewError("JOURNAL_SIGNAL_STATE_INVALID")
    if payload["data_quality_state"] != DataQualityState.READY.value:
        raise OperatorReviewError("JOURNAL_QUALITY_INVALID")
    if (
        payload["manual_execution_required"] is not True
        or payload["submission_status"] != SUBMISSION_STATUS
    ):
        raise OperatorReviewError("JOURNAL_SUBMISSION_INVALID")
    if payload["record_hash"] != _record_digest(payload):
        raise OperatorReviewError("JOURNAL_RECORD_HASH_INVALID")
    return JournalRecord(payload)


def _journal_bytes(path: Path) -> bytes:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return b""
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise OperatorReviewError("JOURNAL_TARGET_INVALID")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise OperatorReviewError("JOURNAL_READ_FAILED") from exc


def _validate_journal(raw: bytes) -> tuple[JournalRecord, ...]:
    if not raw:
        return ()
    if not raw.endswith(b"\n"):
        raise OperatorReviewError("JOURNAL_TRUNCATED")
    records: list[JournalRecord] = []
    previous = "0" * 64
    setups: set[str] = set()
    for sequence, line in enumerate(raw[:-1].split(b"\n"), start=1):
        if not line:
            raise OperatorReviewError("JOURNAL_TRUNCATED")
        record = _validate_record(_strict_json(line), sequence=sequence, previous=previous)
        setup_id = cast(str, record.payload["setup_id"])
        if setup_id in setups:
            raise OperatorReviewError("JOURNAL_DUPLICATE_SETUP")
        setups.add(setup_id)
        previous = record.record_hash
        records.append(record)
    return tuple(records)


def read_journal(journal: str | Path) -> tuple[JournalRecord, ...]:
    """Read a local journal only after validating every prior byte and record."""
    return _validate_journal(_journal_bytes(Path(journal)))


def _acquire_lock(path: Path) -> tuple[int, Path]:
    lock = path.with_name(path.name + ".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise OperatorReviewError("JOURNAL_LOCKED") from exc
    except OSError as exc:
        raise OperatorReviewError("JOURNAL_LOCK_FAILED") from exc
    return fd, lock


def _journal_descriptor_identity(fd: int) -> tuple[int, int]:
    try:
        info = os.fstat(fd)
    except OSError as exc:
        raise OperatorReviewError("JOURNAL_APPEND_FAILED") from exc
    if not stat.S_ISREG(info.st_mode):
        raise OperatorReviewError("JOURNAL_TARGET_INVALID")
    return (info.st_dev, info.st_ino)


def _journal_descriptor_bytes(fd: int) -> bytes:
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        while chunk := os.read(fd, 64 * 1024):
            chunks.append(chunk)
    except OSError as exc:
        raise OperatorReviewError("JOURNAL_READ_FAILED") from exc
    return b"".join(chunks)


def _path_matches_descriptor(path: Path, identity: tuple[int, int]) -> bool:
    try:
        info = path.stat(follow_symlinks=False)
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode) and (info.st_dev, info.st_ino) == identity


def _rollback_journal_descriptor(fd: int, original_size: int) -> None:
    try:
        os.ftruncate(fd, original_size)
        os.fsync(fd)
    except OSError as exc:
        raise OperatorReviewError("JOURNAL_APPEND_ROLLBACK_FAILED") from exc


def append_decision(
    journal: str | Path,
    *,
    card: OperatorReviewCard,
    shadow_order: ShadowOrder,
    decision: HumanDecision,
    timestamp: datetime,
    reason: str,
) -> JournalRecord:
    """Append one terminal human decision with a hash-chain and exclusive local lock."""
    card = _validated_card(card)
    shadow = _validated_shadow(shadow_order)
    if type(decision) is not HumanDecision:
        raise OperatorReviewError("JOURNAL_DECISION_INVALID")
    timestamp = _exact_utc(timestamp, "JOURNAL_TIMESTAMP_INVALID")
    reason = _reason(reason)
    p = card.payload
    if not card.actionable or p["data_quality_state"] != DataQualityState.READY.value:
        raise OperatorReviewError("CARD_NOT_ACTIONABLE")
    if p["lifecycle_state"] not in {
        SignalState.TRIGGERED_FAST.value,
        SignalState.TRIGGERED_STANDARD.value,
    }:
        raise OperatorReviewError("CARD_NOT_ACTIONABLE")
    if (
        shadow.card_id != card.card_id
        or shadow.card_hash != card.canonical_hash
        or shadow.setup_id != p["setup_id"]
        or shadow.setup_hash != p["setup_id"]
        or shadow.plan_id != p["plan_id"]
        or shadow.plan_hash != p["plan_canonical_hash"]
    ):
        raise OperatorReviewError("SHADOW_CARD_MISMATCH")
    path = Path(journal)
    lock_fd, lock = _acquire_lock(path)
    try:
        try:
            fd = os.open(
                path,
                os.O_CREAT | os.O_RDWR | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
        except OSError as exc:
            raise OperatorReviewError("JOURNAL_APPEND_FAILED") from exc
        try:
            identity = _journal_descriptor_identity(fd)
            old_bytes = _journal_descriptor_bytes(fd)
            records = _validate_journal(old_bytes)
            setup_id = cast(str, p["setup_id"])
            if any(record.payload["setup_id"] == setup_id for record in records):
                raise OperatorReviewError("JOURNAL_DUPLICATE_SETUP")
            payload: dict[str, object] = {
                "journal_version": JOURNAL_VERSION,
                "sequence": len(records) + 1,
                "previous_record_hash": records[-1].record_hash if records else "0" * 64,
                "record_hash": "",
                "timestamp": timestamp.isoformat(),
                "reason": reason,
                "card_id": card.card_id,
                "card_hash": card.canonical_hash,
                "setup_id": setup_id,
                "setup_hash": setup_id,
                "plan_id": cast(str, p["plan_id"]),
                "plan_hash": cast(str, p["plan_canonical_hash"]),
                "shadow_order_id": shadow.shadow_order_id,
                "shadow_order_hash": shadow.canonical_hash,
                "decision": decision.value,
                "signal_state": p["lifecycle_state"],
                "data_quality_state": p["data_quality_state"],
                "manual_execution_required": True,
                "submission_status": SUBMISSION_STATUS,
            }
            payload["record_hash"] = _record_digest(payload)
            record = _validate_record(
                payload,
                sequence=len(records) + 1,
                previous=cast(str, payload["previous_record_hash"]),
            )
            encoded = canonical_json_bytes(payload) + b"\n"
            original_size = len(old_bytes)
            if not _path_matches_descriptor(path, identity):
                raise OperatorReviewError("JOURNAL_IDENTITY_CHANGED")
            try:
                written = os.write(fd, encoded)
                if written != len(encoded):
                    raise OSError("partial journal append")
                os.fsync(fd)
            except OSError as exc:
                _rollback_journal_descriptor(fd, original_size)
                raise OperatorReviewError("JOURNAL_APPEND_FAILED") from exc
            try:
                _validate_journal(_journal_descriptor_bytes(fd))
            except OperatorReviewError as exc:
                _rollback_journal_descriptor(fd, original_size)
                raise OperatorReviewError("JOURNAL_APPEND_FAILED") from exc
            if not _path_matches_descriptor(path, identity):
                _rollback_journal_descriptor(fd, original_size)
                raise OperatorReviewError("JOURNAL_IDENTITY_CHANGED")
            return record
        finally:
            os.close(fd)
    finally:
        os.close(lock_fd)
        try:
            lock.unlink()
        except FileNotFoundError:
            pass
