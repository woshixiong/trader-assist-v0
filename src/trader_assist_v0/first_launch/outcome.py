"""Offline-only matching of a human decision with a completed manual ETH trade.

This module deliberately has no transport, credentials, account, or exchange API
surface.  Its inputs are canonical local files and parser-issued candle objects.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal, cast

from trader_assist_v0.contracts.common import canonical_json_bytes, decimal_to_canonical_string
from trader_assist_v0.first_launch.configuration import RiskConfiguration
from trader_assist_v0.first_launch.market_data import (
    Candle,
    MarketDataError,
    _validated_candle,
    candle_from_websocket,
    evidence_from_raw,
)
from trader_assist_v0.first_launch.operator_review import (
    _CARD_FIELDS,
    _MANUAL_FIELD_NAMES,
    CARD_HASH_DOMAIN,
    SHADOW_HASH_DOMAIN,
    HumanDecision,
    JournalRecord,
    OperatorReviewCard,
    OperatorReviewError,
    ShadowOrder,
    _validate_record,
    _validated_card,
    _validated_shadow,
)
from trader_assist_v0.first_launch.strategy import (
    CONFIGURATION_VERSION,
    HISTORICAL_TRADE_PLAN_HASH_DOMAIN,
    HISTORICAL_TRADE_PLAN_VERSION,
    STRATEGY_VERSION,
    TRADE_PLAN_HASH_DOMAIN,
    TRADE_PLAN_VERSION,
    Side,
    TradePlan,
    VolatilityRegime,
    _round_price,
    size_plan,
    size_plan_v3,
)

DECISION_BUNDLE_VERSION: Literal["1"] = "1"
MANUAL_EXECUTION_VERSION: Literal["1"] = "1"
OUTCOME_VERSION: Literal["1"] = "1"
OUTCOME_JOURNAL_VERSION: Literal["1"] = "1"
DECISION_BUNDLE_HASH_DOMAIN = "trader-assist-v0/first-launch/decision-bundle/v1"
MANUAL_EXECUTION_HASH_DOMAIN = "trader-assist-v0/first-launch/manual-execution-import/v1"
OUTCOME_HASH_DOMAIN = "trader-assist-v0/first-launch/outcome-record/v1"
OUTCOME_JOURNAL_HASH_DOMAIN = "trader-assist-v0/first-launch/outcome-journal/v1"
_HASH_RE = re.compile(r"[0-9a-f]{64}")
_POSITIVE_RE = re.compile(r"(?:[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)\Z")
_NONNEGATIVE_RE = re.compile(r"(?:0|[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]+)\Z")
_FINITE_RE = re.compile(
    r"(?:0|[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]+|-(?:[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*))\Z"
)
_FILL_FIELDS = frozenset({"timestamp", "price", "quantity", "fee"})
_IMPORT_FIELDS = frozenset(
    {
        "manual_execution_version",
        "manual_execution_id",
        "canonical_hash",
        "decision_hash",
        "symbol",
        "side",
        "entry_fills",
        "exit_fills",
        "manual_execution_required",
        "submission_status",
    }
)
_BUNDLE_FIELDS = frozenset(
    {
        "decision_bundle_version",
        "bundle_id",
        "canonical_hash",
        "operator_card",
        "shadow_order",
        "decision_record",
        "trade_plan",
        "setup_id",
        "setup_hash",
        "plan_id",
        "plan_hash",
        "planned_risk",
    }
)


class OutcomeError(ValueError):
    """An outcome input is outside the offline First Launch authority."""


def _digest(domain: str, payload: dict[str, object], *, omit: tuple[str, ...] = ()) -> str:
    body = dict(payload)
    for field in omit:
        body.pop(field, None)
    return hashlib.sha256(domain.encode("ascii") + b"\0" + canonical_json_bytes(body)).hexdigest()


def _hash(value: object, error: str) -> str:
    if type(value) is not str or _HASH_RE.fullmatch(value) is None:
        raise OutcomeError(error)
    return value


def _timestamp(value: object, error: str) -> datetime:
    if type(value) is not str:
        raise OutcomeError(error)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise OutcomeError(error) from exc
    if parsed.tzinfo is not UTC or parsed.isoformat() != value:
        raise OutcomeError(error)
    return parsed


def _decimal(value: object, *, positive: bool, error: str) -> Decimal:
    if type(value) is Decimal:
        if not value.is_finite():
            raise OutcomeError(error)
        if (positive and value <= 0) or (not positive and value < 0):
            raise OutcomeError(error)
        return value
    if (
        type(value) is not str
        or (_POSITIVE_RE if positive else _NONNEGATIVE_RE).fullmatch(value) is None
    ):
        raise OutcomeError(error)
    try:
        parsed = Decimal(value)
        if not parsed.is_finite() or decimal_to_canonical_string(parsed) != value:
            raise OutcomeError(error)
    except (InvalidOperation, ValueError) as exc:
        if isinstance(exc, OutcomeError):
            raise
        raise OutcomeError(error) from exc
    if (positive and parsed <= 0) or (not positive and parsed < 0):
        raise OutcomeError(error)
    return parsed


def _signed_decimal(value: object, error: str) -> Decimal:
    if type(value) is Decimal:
        if not value.is_finite():
            raise OutcomeError(error)
        return value
    if type(value) is not str or _FINITE_RE.fullmatch(value) is None:
        raise OutcomeError(error)
    try:
        parsed = Decimal(value)
        if not parsed.is_finite() or decimal_to_canonical_string(parsed) != value:
            raise OutcomeError(error)
    except (InvalidOperation, ValueError) as exc:
        if isinstance(exc, OutcomeError):
            raise
        raise OutcomeError(error) from exc
    return parsed


def _strict_object(raw: bytes, error: str, *, canonical: bool = True) -> dict[str, object]:
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
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise OutcomeError(error) from exc
    if type(value) is not dict or (canonical and canonical_json_bytes(value) != raw):
        raise OutcomeError(error)
    return cast(dict[str, object], value)


def _card_payload(card: OperatorReviewCard) -> dict[str, object]:
    try:
        card = _validated_card(card)
    except (AttributeError, TypeError, ValueError) as exc:
        raise OutcomeError("BUNDLE_CARD_INVALID") from exc
    payload = card.payload
    if (
        card.card_id != _digest(CARD_HASH_DOMAIN, payload)
        or payload.get("card_kind") != "TRADE_PLAN"
        or payload.get("symbol") != "ETH"
    ):
        raise OutcomeError("BUNDLE_CARD_INVALID")
    return {"card_id": card.card_id, "canonical_hash": card.canonical_hash, "payload": payload}


def _shadow_payload(shadow: ShadowOrder) -> dict[str, object]:
    try:
        shadow = _validated_shadow(shadow)
    except (AttributeError, TypeError, ValueError) as exc:
        raise OutcomeError("BUNDLE_SHADOW_INVALID") from exc
    return {
        "shadow_order_id": shadow.shadow_order_id,
        "canonical_hash": shadow.canonical_hash,
        **shadow.payload(),
    }


def _decision_payload(record: JournalRecord) -> dict[str, object]:
    if type(record) is not JournalRecord or type(record.payload) is not dict:
        raise OutcomeError("BUNDLE_DECISION_INVALID")
    payload = record.payload
    try:
        _validate_record(
            payload,
            sequence=cast(int, payload.get("sequence")),
            previous=cast(str, payload.get("previous_record_hash")),
        )
    except (OperatorReviewError, TypeError, ValueError) as exc:
        raise OutcomeError("BUNDLE_DECISION_INVALID") from exc
    return payload


def _plan_payload(plan: TradePlan) -> dict[str, object]:
    if type(plan) is not TradePlan:
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    try:
        plan.__post_init__()
    except (AttributeError, TypeError, ValueError) as exc:
        raise OutcomeError("BUNDLE_PLAN_INVALID") from exc
    payload = plan.payload()
    if (
        plan.plan_id != _digest(_plan_domain(payload.get("trade_plan_version")), payload)
        or plan.plan_id != plan.canonical_hash
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    return cast(dict[str, object], json.loads(canonical_json_bytes(payload)))


def _bundle_time(value: object, error: str) -> datetime:
    if type(value) is not str:
        raise OutcomeError(error)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return _timestamp(normalized, error)


def _plan_domain(version: object) -> str:
    if version == HISTORICAL_TRADE_PLAN_VERSION:
        return HISTORICAL_TRADE_PLAN_HASH_DOMAIN
    if version == TRADE_PLAN_VERSION:
        return TRADE_PLAN_HASH_DOMAIN
    raise OutcomeError("BUNDLE_PLAN_INVALID")


def _validate_v2_plan_semantics(plan: dict[str, object]) -> tuple[str, dict[str, Decimal]]:
    """Validate every serialised financial value without process-local issuance."""
    required = {
        "trade_plan_version",
        "strategy_version",
        "configuration_version",
        "symbol",
        "setup_id",
        "provenance",
        "speed",
        "decision_trigger_identity",
        "decision_trigger_open_time_ms",
        "decision_trigger_canonical_hash",
        "decision_trigger_received_at",
        "strategy_reason",
        "strategy_do_not_chase",
        "material_extreme",
        "raw_entry_low",
        "raw_entry_high",
        "raw_chase_limit",
        "raw_stop",
        "strategy_created_at",
        "strategy_expires_at",
        "supersedes_plan_id",
        "reference",
        "entry_low",
        "entry_high",
        "planned_entry",
        "chase_limit",
        "stop",
        "tp1",
        "tp2",
        "quantity",
        "notional",
        "account_equity",
        "risk_budget",
        "planned_risk",
        "sz_decimals",
        "do_not_chase",
    }
    if (
        set(plan) != required
        or plan.get("symbol") != "ETH"
        or plan.get("speed") not in {"FAST", "STANDARD"}
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    if (
        plan.get("trade_plan_version"),
        plan.get("strategy_version"),
        plan.get("configuration_version"),
    ) != (HISTORICAL_TRADE_PLAN_VERSION, STRATEGY_VERSION, CONFIGURATION_VERSION):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    provenance = plan.get("provenance")
    if type(provenance) is not dict or provenance.get("side") not in {"LONG", "SHORT"}:
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    side = cast(str, provenance["side"])
    if (
        plan.get("setup_id")
        != hashlib.sha256(
            canonical_json_bytes(
                {
                    "strategy_version": STRATEGY_VERSION,
                    "configuration_version": CONFIGURATION_VERSION,
                    "provenance": provenance,
                }
            )
        ).hexdigest()
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    if (
        plan.get("setup_id")
        != hashlib.sha256(
            canonical_json_bytes(
                {
                    "strategy_version": STRATEGY_VERSION,
                    "configuration_version": CONFIGURATION_VERSION,
                    "provenance": provenance,
                }
            )
        ).hexdigest()
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    if (
        plan.get("strategy_reason") != "CONFIRMED"
        or plan.get("strategy_do_not_chase") != "DO NOT CHASE"
        or plan.get("do_not_chase") != "DO NOT CHASE"
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    values = {
        name: _decimal(plan.get(name), positive=True, error="BUNDLE_PLAN_INVALID")
        for name in (
            "reference",
            "entry_low",
            "entry_high",
            "planned_entry",
            "chase_limit",
            "stop",
            "tp1",
            "tp2",
            "quantity",
            "notional",
            "account_equity",
            "risk_budget",
            "planned_risk",
            "raw_entry_low",
            "raw_entry_high",
            "raw_chase_limit",
            "raw_stop",
            "material_extreme",
        )
    }
    if (
        not values["entry_low"] <= values["planned_entry"] <= values["entry_high"]
        or values["notional"] != values["quantity"] * values["planned_entry"]
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    if (
        side == "LONG"
        and not values["stop"] < values["planned_entry"] < values["tp1"] < values["tp2"]
    ) or (
        side == "SHORT"
        and not values["tp2"] < values["tp1"] < values["planned_entry"] < values["stop"]
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    decimals = plan.get("sz_decimals")
    if type(decimals) is not int or isinstance(decimals, bool) or not 0 <= decimals <= 18:
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    try:
        risk = size_plan(
            side=Side(side),
            entry=values["planned_entry"],
            stop=values["stop"],
            equity=values["account_equity"],
            sz_decimals=decimals,
        )
    except ValueError as exc:
        raise OutcomeError("BUNDLE_PLAN_INVALID") from exc
    if (values["quantity"], values["notional"], values["risk_budget"], values["planned_risk"]) != (
        risk.quantity,
        risk.notional,
        risk.risk_budget,
        risk.planned_risk,
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    target = "down" if side == "LONG" else "up"
    distance = abs(values["planned_entry"] - values["stop"])
    expected = (
        _round_price(
            values["planned_entry"] + distance
            if side == "LONG"
            else values["planned_entry"] - distance,
            decimals,
            target,
        ),
        _round_price(
            values["planned_entry"] + 2 * distance
            if side == "LONG"
            else values["planned_entry"] - 2 * distance,
            decimals,
            target,
        ),
    )
    if (values["tp1"], values["tp2"]) != expected:
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    created, expiry = (
        _bundle_time(plan.get("strategy_created_at"), "BUNDLE_PLAN_INVALID"),
        _bundle_time(plan.get("strategy_expires_at"), "BUNDLE_PLAN_INVALID"),
    )
    if expiry <= created:
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    return side, values


def _validate_v3_plan_semantics(plan: dict[str, object]) -> tuple[str, dict[str, Decimal]]:
    """Validate the v3 additions independently of process-local plan issuance."""
    v2_keys = {
        "trade_plan_version",
        "strategy_version",
        "configuration_version",
        "symbol",
        "setup_id",
        "provenance",
        "speed",
        "decision_trigger_identity",
        "decision_trigger_open_time_ms",
        "decision_trigger_canonical_hash",
        "decision_trigger_received_at",
        "strategy_reason",
        "strategy_do_not_chase",
        "material_extreme",
        "raw_entry_low",
        "raw_entry_high",
        "raw_chase_limit",
        "raw_stop",
        "strategy_created_at",
        "strategy_expires_at",
        "supersedes_plan_id",
        "reference",
        "entry_low",
        "entry_high",
        "planned_entry",
        "chase_limit",
        "stop",
        "tp1",
        "tp2",
        "quantity",
        "notional",
        "account_equity",
        "risk_budget",
        "planned_risk",
        "sz_decimals",
        "do_not_chase",
    }
    additions = {
        "effective_raw_chase_limit",
        "signal_id",
        "volatility_regime",
        "current_atr",
        "previous_48_median_atr",
        "atr_ratio",
        "selected_decision_span",
        "overlay_action",
        "overlay_reason",
        "candle_cutoff_identity",
        "candle_cutoff_close_time_ms",
        "plan_evaluation_cutoff",
        "mark_price",
        "mid_price",
        "context_summary",
        "context_hash",
        "configured_risk_per_trade_pct",
        "base_risk_budget",
        "risk_multiplier",
        "effective_risk_budget",
        "configured_max_notional",
        "system_hard_notional_cap",
        "effective_max_notional",
        "risk_configuration_version",
        "risk_configuration_hash",
        "configuration_account_equity_text",
        "configuration_risk_pct_text",
        "configuration_max_notional_text",
        "manual_execution_required",
        "submission_status",
        "volatility_snapshot",
        "overlay_payload",
        "overlay_hash",
    }
    if set(plan) != v2_keys | additions or plan.get("trade_plan_version") != TRADE_PLAN_VERSION:
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    # The old structural validator is intentionally not used: its static v2 version and
    # hard-coded 0.25% sizing are historical compatibility only.
    provenance = plan.get("provenance")
    if type(provenance) is not dict or provenance.get("side") not in {"LONG", "SHORT"}:
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    side = cast(str, provenance["side"])
    decimals = plan.get("sz_decimals")
    if type(decimals) is not int or isinstance(decimals, bool) or not 0 <= decimals <= 18:
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    values = {
        name: _decimal(plan.get(name), positive=True, error="BUNDLE_PLAN_INVALID")
        for name in (
            "reference",
            "entry_low",
            "entry_high",
            "planned_entry",
            "chase_limit",
            "stop",
            "tp1",
            "tp2",
            "quantity",
            "notional",
            "account_equity",
            "risk_budget",
            "planned_risk",
            "raw_entry_low",
            "raw_entry_high",
            "raw_chase_limit",
            "effective_raw_chase_limit",
            "raw_stop",
            "material_extreme",
            "current_atr",
            "previous_48_median_atr",
            "atr_ratio",
            "mark_price",
            "configured_risk_per_trade_pct",
            "base_risk_budget",
            "risk_multiplier",
            "effective_risk_budget",
            "system_hard_notional_cap",
            "effective_max_notional",
        )
    }
    configured_max = plan.get("configured_max_notional")
    if configured_max is not None:
        values["configured_max_notional"] = _decimal(
            configured_max, positive=True, error="BUNDLE_PLAN_INVALID"
        )
    if (
        plan.get("volatility_regime") not in {"LOW", "NORMAL", "HIGH"}
        or plan.get("selected_decision_span") not in {5, 30, 60}
        or plan.get("manual_execution_required") is not True
        or plan.get("submission_status") != "NOT_SUBMITTED"
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    snapshot = plan.get("volatility_snapshot")
    snapshot_keys = {
        "current_atr",
        "previous_48_median_atr",
        "atr_ratio",
        "regime",
        "candle_cutoff_identity",
        "candle_cutoff_close_time_ms",
        "candle_identities",
        "candle_hashes",
    }
    if type(snapshot) is not dict or set(snapshot) != snapshot_keys:
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    source = cast(dict[str, object], snapshot)
    source_ids, source_hashes = source.get("candle_identities"), source.get("candle_hashes")
    if (
        type(source_ids) is not list
        or type(source_hashes) is not list
        or len(source_ids) != 64
        or len(source_hashes) != 64
        or any(type(item) is not list or len(item) != 3 for item in source_ids)
        or any(type(item) is not str or _HASH_RE.fullmatch(item) is None for item in source_hashes)
        or source.get("candle_cutoff_identity") != source_ids[-1]
        or source.get("candle_cutoff_close_time_ms") != plan.get("candle_cutoff_close_time_ms")
        or source.get("candle_cutoff_identity") != plan.get("candle_cutoff_identity")
        or source.get("regime") != plan.get("volatility_regime")
        or any(
            source.get(name) != plan.get(name)
            for name in ("current_atr", "previous_48_median_atr", "atr_ratio")
        )
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    source_current = _decimal(source.get("current_atr"), positive=True, error="BUNDLE_PLAN_INVALID")
    source_median = _decimal(
        source.get("previous_48_median_atr"), positive=True, error="BUNDLE_PLAN_INVALID"
    )
    source_ratio = _decimal(source.get("atr_ratio"), positive=True, error="BUNDLE_PLAN_INVALID")
    expected_regime = (
        "LOW"
        if source_ratio < Decimal("0.75")
        else "NORMAL"
        if source_ratio <= Decimal("1.50")
        else "HIGH"
        if source_ratio <= Decimal("2.25")
        else "EXTREME"
    )
    if source_ratio != source_current / source_median or source.get("regime") != expected_regime:
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    if (
        type(plan.get("overlay_hash")) is not str
        or _HASH_RE.fullmatch(cast(str, plan["overlay_hash"])) is None
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    overlay = plan.get("overlay_payload")
    if (
        type(overlay) is not dict
        or hashlib.sha256(canonical_json_bytes(overlay)).hexdigest() != plan.get("overlay_hash")
        or overlay.get("regime") != plan.get("volatility_regime")
        or overlay.get("selected_decision_span") != plan.get("selected_decision_span")
        or overlay.get("action") != plan.get("overlay_action")
        or overlay.get("reason") != plan.get("overlay_reason")
        or overlay.get("effective_raw_chase_limit") != plan.get("effective_raw_chase_limit")
        or overlay.get("reference_price") != plan.get("reference")
        or overlay.get("volatility_hash")
        != hashlib.sha256(canonical_json_bytes(source)).hexdigest()
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    multiplier = Decimal("0.75") if plan["volatility_regime"] == "HIGH" else Decimal("1")
    if (
        values["risk_multiplier"] != multiplier
        or values["base_risk_budget"]
        != values["account_equity"] * (values["configured_risk_per_trade_pct"] / Decimal("100"))
        or values["effective_risk_budget"] != values["base_risk_budget"] * multiplier
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    # Independently execute the reviewed configuration and fee-aware sizing path;
    # caps alone are not authority for a serialized decision.
    try:
        configuration = RiskConfiguration(
            cast(str, plan.get("risk_configuration_version")),
            Decimal(cast(str, plan.get("configuration_account_equity_text"))),
            Decimal(cast(str, plan.get("configuration_risk_pct_text"))),
            (
                None
                if plan.get("configuration_max_notional_text") is None
                else Decimal(cast(str, plan.get("configuration_max_notional_text")))
            ),
            cast(str, plan.get("risk_configuration_hash")),
        )
        expected_risk, _ = size_plan_v3(
            side=Side(side),
            entry=values["planned_entry"],
            stop=values["stop"],
            configuration=configuration,
            regime=VolatilityRegime(cast(str, plan["volatility_regime"])),
            sz_decimals=decimals,
        )
    except (ValueError, TypeError) as exc:
        raise OutcomeError("BUNDLE_PLAN_INVALID") from exc
    if (values["quantity"], values["notional"], values["risk_budget"], values["planned_risk"]) != (
        expected_risk.quantity,
        expected_risk.notional,
        expected_risk.risk_budget,
        expected_risk.planned_risk,
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    if values["system_hard_notional_cap"] != values["account_equity"] * Decimal("25"):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    expected_cap = (
        values["system_hard_notional_cap"]
        if configured_max is None
        else min(values["configured_max_notional"], values["system_hard_notional_cap"])
    )
    if (
        values["effective_max_notional"] != expected_cap
        or values["notional"] != values["quantity"] * values["planned_entry"]
        or values["notional"] > expected_cap
        or values["planned_risk"] > values["effective_risk_budget"]
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    if (
        type(plan.get("signal_id")) is not str
        or len(cast(str, plan["signal_id"])) != 64
        or type(plan.get("risk_configuration_hash")) is not str
        or len(cast(str, plan["risk_configuration_hash"])) != 64
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    expected_signal = hashlib.sha256(
        canonical_json_bytes(
            {
                "strategy_version": STRATEGY_VERSION,
                "setup_id": plan.get("setup_id"),
                "decision_trigger_identity": plan.get("decision_trigger_identity"),
                "decision_trigger_canonical_hash": plan.get("decision_trigger_canonical_hash"),
                "speed": plan.get("speed"),
                "state": "TRIGGERED_FAST" if plan.get("speed") == "FAST" else "TRIGGERED_STANDARD",
                "regime": plan.get("volatility_regime"),
                "selected_decision_span": plan.get("selected_decision_span"),
                "overlay_action": plan.get("overlay_action"),
                "overlay_reason": plan.get("overlay_reason"),
                "effective_raw_chase_limit": plan.get("effective_raw_chase_limit"),
                "candle_cutoff_close_time_ms": plan.get("candle_cutoff_close_time_ms"),
            }
        )
    ).hexdigest()
    if plan.get("signal_id") != expected_signal:
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    context = plan.get("context_summary")
    if (
        type(context) is not dict
        or context.get("canonical_hash") != plan.get("context_hash")
        or type(context.get("current")) is not dict
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    current = cast(dict[str, object], context["current"])
    if current.get("mark_price") != plan.get("mark_price") or current.get("mid_price") != plan.get(
        "mid_price"
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    context_body = {
        "current": {
            key: current.get(key)
            for key in (
                "mark_price",
                "mid_price",
                "open_interest",
                "funding",
                "source_time_ms",
                "received_at",
                "receive_sequence",
                "evidence_hash",
                "reference_price",
                "mark_mid_basis_bps",
            )
        },
        "current_hash": context.get("current_hash"),
        "baseline_5m": context.get("baseline_5m"),
        "baseline_5m_hash": context.get("baseline_5m_hash"),
        "baseline_15m": context.get("baseline_15m"),
        "baseline_15m_hash": context.get("baseline_15m_hash"),
        "summary_cutoff": context.get("summary_cutoff"),
        "oi_delta_5m": context.get("oi_delta_5m"),
        "oi_pct_delta_5m": context.get("oi_pct_delta_5m"),
        "oi_delta_15m": context.get("oi_delta_15m"),
        "oi_pct_delta_15m": context.get("oi_pct_delta_15m"),
        "funding_delta_5m": context.get("funding_delta_5m"),
        "funding_delta_15m": context.get("funding_delta_15m"),
        "classification_5m": context.get("classification_5m"),
        "classification_15m": context.get("classification_15m"),
        "selection_proof": context.get("selection_proof"),
        "selection_proof_hashes": context.get("selection_proof_hashes"),
    }
    if hashlib.sha256(canonical_json_bytes(context_body)).hexdigest() != plan.get("context_hash"):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    if (
        context.get("summary_cutoff") != plan.get("plan_evaluation_cutoff")
        or current.get("reference_price") != plan.get("reference")
        or current.get("canonical_hash") is not None
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    expected_configuration = RiskConfiguration.digest(
        cast(str, plan.get("risk_configuration_version")),
        Decimal(cast(str, plan.get("configuration_account_equity_text"))),
        Decimal(cast(str, plan.get("configuration_risk_pct_text"))),
        (
            None
            if plan.get("configuration_max_notional_text") is None
            else Decimal(cast(str, plan.get("configuration_max_notional_text")))
        ),
    )
    if plan.get("risk_configuration_hash") != expected_configuration:
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    return side, values


def _validate_plan_semantics(plan: dict[str, object]) -> tuple[str, dict[str, Decimal]]:
    version = plan.get("trade_plan_version")
    if version == HISTORICAL_TRADE_PLAN_VERSION:
        return _validate_v2_plan_semantics(plan)
    if version == TRADE_PLAN_VERSION:
        return _validate_v3_plan_semantics(plan)
    raise OutcomeError("BUNDLE_PLAN_INVALID")


def _expected_card_from_plan(
    plan: dict[str, object], *, plan_id: str, side: str, values: dict[str, Decimal]
) -> dict[str, object]:
    """Reproduce the complete deterministic TradePlan card payload."""
    provenance = cast(dict[str, object], plan["provenance"])
    speed = cast(str, plan["speed"])
    state = "TRIGGERED_FAST" if speed == "FAST" else "TRIGGERED_STANDARD"
    trigger = _bundle_time(
        plan["decision_trigger_received_at"], "BUNDLE_SEMANTIC_CORRESPONDENCE_INVALID"
    )
    created = _bundle_time(plan["strategy_created_at"], "BUNDLE_SEMANTIC_CORRESPONDENCE_INVALID")
    expires = _bundle_time(plan["strategy_expires_at"], "BUNDLE_SEMANTIC_CORRESPONDENCE_INVALID")
    return {
        "card_version": "1",
        "card_kind": "TRADE_PLAN",
        "submission_status": "NOT_SUBMITTED",
        "manual_execution_required": True,
        "lifecycle_state": state,
        "data_quality_state": "READY",
        "signal_state": state,
        "symbol": "ETH",
        "side": side,
        "speed": speed,
        "setup_family": provenance["family"],
        "setup_id": plan["setup_id"],
        "plan_id": plan_id,
        "plan_canonical_hash": plan_id,
        "strategy_version": STRATEGY_VERSION,
        "configuration_version": CONFIGURATION_VERSION,
        "trade_plan_version": plan["trade_plan_version"],
        "decision_trigger_identity": plan["decision_trigger_identity"],
        "decision_trigger_open_time_ms": plan["decision_trigger_open_time_ms"],
        "decision_trigger_canonical_hash": plan["decision_trigger_canonical_hash"],
        "decision_trigger_received_at": trigger.isoformat(),
        "entry_low": decimal_to_canonical_string(values["entry_low"]),
        "entry_high": decimal_to_canonical_string(values["entry_high"]),
        "planned_entry": decimal_to_canonical_string(values["planned_entry"]),
        "chase_limit": decimal_to_canonical_string(values["chase_limit"]),
        "stop": decimal_to_canonical_string(values["stop"]),
        "tp1": decimal_to_canonical_string(values["tp1"]),
        "tp2": decimal_to_canonical_string(values["tp2"]),
        "quantity": decimal_to_canonical_string(values["quantity"]),
        "notional": decimal_to_canonical_string(values["notional"]),
        "planned_risk": decimal_to_canonical_string(values["planned_risk"]),
        "account_equity": decimal_to_canonical_string(values["account_equity"]),
        "risk_percent": decimal_to_canonical_string(
            values["planned_risk"] / values["account_equity"] * Decimal("100")
        ),
        "created_at": created.isoformat(),
        "expires_at": expires.isoformat(),
        "do_not_chase": "DO NOT CHASE",
        "reason": "CONFIRMED",
    }


def _validate_bundle(payload: dict[str, object]) -> None:
    if (
        set(payload) != _BUNDLE_FIELDS
        or payload.get("decision_bundle_version") != DECISION_BUNDLE_VERSION
    ):
        raise OutcomeError("BUNDLE_FIELDS_INVALID")
    if payload.get("bundle_id") != payload.get("canonical_hash") or payload["bundle_id"] != _digest(
        DECISION_BUNDLE_HASH_DOMAIN, payload, omit=("bundle_id", "canonical_hash")
    ):
        raise OutcomeError("BUNDLE_HASH_INVALID")
    card = payload.get("operator_card")
    shadow = payload.get("shadow_order")
    decision = payload.get("decision_record")
    plan = payload.get("trade_plan")
    if not all(type(value) is dict for value in (card, shadow, decision, plan)):
        raise OutcomeError("BUNDLE_COMPONENT_INVALID")
    card = cast(dict[str, object], card)
    shadow = cast(dict[str, object], shadow)
    decision = cast(dict[str, object], decision)
    plan = cast(dict[str, object], plan)
    if (
        set(card) != {"card_id", "canonical_hash", "payload"}
        or type(card.get("payload")) is not dict
    ):
        raise OutcomeError("BUNDLE_CARD_INVALID")
    card_body = cast(dict[str, object], card["payload"])
    if (
        set(card_body) != _CARD_FIELDS
        or card.get("card_id") != card.get("canonical_hash")
        or card["card_id"] != _digest(CARD_HASH_DOMAIN, card_body)
    ):
        raise OutcomeError("BUNDLE_CARD_INVALID")
    required_shadow = {
        "shadow_order_id",
        "canonical_hash",
        "card_id",
        "card_hash",
        "setup_id",
        "setup_hash",
        "plan_id",
        "plan_hash",
        "manual_fields",
        "submission_status",
        "manual_execution_required",
    }
    if set(shadow) != required_shadow or shadow.get("shadow_order_id") != shadow.get(
        "canonical_hash"
    ):
        raise OutcomeError("BUNDLE_SHADOW_INVALID")
    shadow_body = dict(shadow)
    shadow_body.pop("shadow_order_id")
    shadow_body.pop("canonical_hash")
    if shadow["shadow_order_id"] != _digest(SHADOW_HASH_DOMAIN, shadow_body):
        raise OutcomeError("BUNDLE_SHADOW_INVALID")
    if (
        type(shadow.get("manual_fields")) is not dict
        or set(cast(dict[str, object], shadow["manual_fields"])) != _MANUAL_FIELD_NAMES
    ):
        raise OutcomeError("BUNDLE_SHADOW_INVALID")
    try:
        _validate_record(
            decision,
            sequence=cast(int, decision.get("sequence")),
            previous=cast(str, decision.get("previous_record_hash")),
        )
    except (OperatorReviewError, TypeError, ValueError) as exc:
        raise OutcomeError("BUNDLE_DECISION_INVALID") from exc
    side, plan_values = _validate_plan_semantics(plan)
    expected_card = _expected_card_from_plan(
        plan, plan_id=cast(str, payload["plan_id"]), side=side, values=plan_values
    )
    manual = cast(dict[str, object], shadow["manual_fields"])
    expected_manual = {
        "symbol": "ETH",
        "side": side,
        "speed": plan["speed"],
        **{
            name: decimal_to_canonical_string(plan_values[name])
            for name in (
                "planned_entry",
                "chase_limit",
                "stop",
                "tp1",
                "tp2",
                "quantity",
                "notional",
            )
        },
    }
    if card_body != expected_card or any(
        manual.get(key) != value for key, value in expected_manual.items()
    ):
        raise OutcomeError("BUNDLE_SEMANTIC_CORRESPONDENCE_INVALID")
    if (
        plan.get("symbol") != "ETH"
        or payload.get("plan_id") != payload.get("plan_hash")
        or payload["plan_id"] != _digest(_plan_domain(plan.get("trade_plan_version")), plan)
    ):
        raise OutcomeError("BUNDLE_PLAN_INVALID")
    for key in ("setup_id", "setup_hash", "plan_id", "plan_hash"):
        _hash(payload.get(key), "BUNDLE_IDENTIFIERS_INVALID")
    if (
        payload["setup_id"] != payload["setup_hash"]
        or card_body.get("setup_id") != payload["setup_id"]
        or card_body.get("plan_id") != payload["plan_id"]
        or card_body.get("plan_canonical_hash") != payload["plan_hash"]
        or shadow.get("card_id") != card.get("card_id")
        or shadow.get("card_hash") != card.get("canonical_hash")
        or shadow.get("setup_id") != payload["setup_id"]
        or shadow.get("setup_hash") != payload["setup_hash"]
        or shadow.get("plan_id") != payload["plan_id"]
        or shadow.get("plan_hash") != payload["plan_hash"]
        or decision.get("card_id") != card.get("card_id")
        or decision.get("card_hash") != card.get("canonical_hash")
        or decision.get("setup_id") != payload["setup_id"]
        or decision.get("setup_hash") != payload["setup_hash"]
        or decision.get("plan_id") != payload["plan_id"]
        or decision.get("plan_hash") != payload["plan_hash"]
        or plan.get("setup_id") != payload["setup_id"]
        or payload.get("planned_risk") != decimal_to_canonical_string(plan_values["planned_risk"])
    ):
        raise OutcomeError("BUNDLE_CORRESPONDENCE_INVALID")
    _decimal(payload.get("planned_risk"), positive=True, error="BUNDLE_PLANNED_RISK_INVALID")


@dataclass(frozen=True)
class DecisionBundleV1:
    """Canonical, independently readable binding of the pre-execution decision."""

    payload: dict[str, object]

    def __post_init__(self) -> None:
        _validate_bundle(self.payload)

    @property
    def bundle_id(self) -> str:
        return cast(str, self.payload["bundle_id"])

    @property
    def canonical_hash(self) -> str:
        return cast(str, self.payload["canonical_hash"])

    @property
    def decision_hash(self) -> str:
        return cast(str, cast(dict[str, object], self.payload["decision_record"])["record_hash"])

    def canonical_json(self) -> bytes:
        return canonical_json_bytes(self.payload)

    @classmethod
    def from_json(cls, raw: bytes) -> DecisionBundleV1:
        return cls(_strict_object(raw, "BUNDLE_JSON_INVALID"))


def build_decision_bundle(
    *,
    card: OperatorReviewCard,
    shadow_order: ShadowOrder,
    decision_record: JournalRecord,
    plan: TradePlan,
) -> DecisionBundleV1:
    """Freeze the exact identities that a later manual fill import must match."""
    card_data, shadow_data, decision, plan_data = (
        _card_payload(card),
        _shadow_payload(shadow_order),
        _decision_payload(decision_record),
        _plan_payload(plan),
    )
    if decision.get("decision") not in {item.value for item in HumanDecision}:
        raise OutcomeError("BUNDLE_DECISION_INVALID")
    payload: dict[str, object] = {
        "decision_bundle_version": DECISION_BUNDLE_VERSION,
        "bundle_id": "",
        "canonical_hash": "",
        "operator_card": card_data,
        "shadow_order": shadow_data,
        "decision_record": decision,
        "trade_plan": plan_data,
        "setup_id": plan.setup_id,
        "setup_hash": plan.setup_id,
        "plan_id": plan.plan_id,
        "plan_hash": plan.canonical_hash,
        "planned_risk": decimal_to_canonical_string(plan.planned_risk),
    }
    digest = _digest(DECISION_BUNDLE_HASH_DOMAIN, payload, omit=("bundle_id", "canonical_hash"))
    payload["bundle_id"] = digest
    payload["canonical_hash"] = digest
    return DecisionBundleV1(payload)


def _validate_fill(value: object) -> tuple[datetime, Decimal, Decimal, Decimal]:
    if type(value) is not dict or set(value) != _FILL_FIELDS:
        raise OutcomeError("MANUAL_FILL_FIELDS_INVALID")
    fill = cast(dict[str, object], value)
    return (
        _timestamp(fill["timestamp"], "MANUAL_FILL_TIMESTAMP_INVALID"),
        _decimal(fill["price"], positive=True, error="MANUAL_FILL_PRICE_INVALID"),
        _decimal(fill["quantity"], positive=True, error="MANUAL_FILL_QUANTITY_INVALID"),
        _decimal(fill["fee"], positive=False, error="MANUAL_FILL_FEE_INVALID"),
    )


def _validate_import(payload: dict[str, object]) -> None:
    if (
        set(payload) != _IMPORT_FIELDS
        or payload.get("manual_execution_version") != MANUAL_EXECUTION_VERSION
    ):
        raise OutcomeError("MANUAL_IMPORT_FIELDS_INVALID")
    if payload.get("manual_execution_id") != payload.get("canonical_hash") or payload[
        "manual_execution_id"
    ] != _digest(
        MANUAL_EXECUTION_HASH_DOMAIN, payload, omit=("manual_execution_id", "canonical_hash")
    ):
        raise OutcomeError("MANUAL_IMPORT_HASH_INVALID")
    if (
        payload.get("symbol") != "ETH"
        or payload.get("side") not in {Side.LONG.value, Side.SHORT.value}
        or payload.get("manual_execution_required") is not True
        or payload.get("submission_status") != "NOT_SUBMITTED"
    ):
        raise OutcomeError("MANUAL_IMPORT_AUTHORITY_INVALID")
    _hash(payload.get("decision_hash"), "MANUAL_IMPORT_DECISION_INVALID")
    entries, exits = payload.get("entry_fills"), payload.get("exit_fills")
    if type(entries) is not list or type(exits) is not list or not entries or not exits:
        raise OutcomeError("MANUAL_IMPORT_CLOSED_TRADE_REQUIRED")
    entry_values = [_validate_fill(item) for item in entries]
    exit_values = [_validate_fill(item) for item in exits]
    all_fills = [*entry_values, *exit_values]
    if any(later[0] <= earlier[0] for earlier, later in pairwise(all_fills)):
        raise OutcomeError("MANUAL_FILL_TIMESTAMPS_NOT_ORDERED")
    if sum(item[2] for item in entry_values) != sum(item[2] for item in exit_values):
        raise OutcomeError("MANUAL_IMPORT_RESIDUAL_OPEN_QUANTITY")


@dataclass(frozen=True)
class ManualExecutionImportV1:
    """A fully closed, manually entered ETH fill import; never an order command."""

    payload: dict[str, object]

    def __post_init__(self) -> None:
        _validate_import(self.payload)

    @property
    def decision_hash(self) -> str:
        return cast(str, self.payload["decision_hash"])

    def canonical_json(self) -> bytes:
        return canonical_json_bytes(self.payload)

    @classmethod
    def from_json(cls, raw: bytes) -> ManualExecutionImportV1:
        return cls(_strict_object(raw, "MANUAL_IMPORT_JSON_INVALID"))


def build_manual_execution_import(
    *,
    decision_hash: str,
    side: Side,
    entry_fills: list[dict[str, str]],
    exit_fills: list[dict[str, str]],
) -> ManualExecutionImportV1:
    payload: dict[str, object] = {
        "manual_execution_version": MANUAL_EXECUTION_VERSION,
        "manual_execution_id": "",
        "canonical_hash": "",
        "decision_hash": decision_hash,
        "symbol": "ETH",
        "side": side.value,
        "entry_fills": entry_fills,
        "exit_fills": exit_fills,
        "manual_execution_required": True,
        "submission_status": "NOT_SUBMITTED",
    }
    digest = _digest(
        MANUAL_EXECUTION_HASH_DOMAIN, payload, omit=("manual_execution_id", "canonical_hash")
    )
    payload["manual_execution_id"] = digest
    payload["canonical_hash"] = digest
    return ManualExecutionImportV1(payload)


def _fills(
    payload: dict[str, object], name: str
) -> list[tuple[datetime, Decimal, Decimal, Decimal]]:
    return [_validate_fill(item) for item in cast(list[object], payload[name])]


def _replay_window(
    candles: tuple[Candle, ...], start: datetime, end: datetime
) -> tuple[tuple[Candle, ...], str]:
    try:
        valid = tuple(_validated_candle(candle) for candle in candles)
    except MarketDataError:
        return (), "INSUFFICIENT_EVIDENCE"
    by_open: dict[int, Candle] = {}
    conflict = False
    for candle in valid:
        if candle.interval != "5m" or candle.identity[0] != "ETH":
            return (), "INSUFFICIENT_EVIDENCE"
        existing = by_open.get(candle.open_time_ms)
        if existing is not None:
            conflict = conflict or existing.canonical_hash != candle.canonical_hash
            return (), "INSUFFICIENT_EVIDENCE"
        by_open[candle.open_time_ms] = candle
    start_ms, end_ms = int(start.timestamp() * 1000), int(end.timestamp() * 1000)
    first = next(
        (item for item in valid if item.open_time_ms <= start_ms < item.close_time_ms), None
    )
    last = next((item for item in valid if item.open_time_ms <= end_ms < item.close_time_ms), None)
    if first is None or last is None or conflict:
        return (), "INSUFFICIENT_EVIDENCE"
    expected = range(first.open_time_ms, last.open_time_ms + 1, 300_000)
    if any(point not in by_open for point in expected):
        return (), "INSUFFICIENT_EVIDENCE"
    window = tuple(by_open[point] for point in expected)
    return window, "COMPLETE"


def _path(plan: dict[str, object], side: str, candles: tuple[Candle, ...], coverage: str) -> str:
    if coverage != "COMPLETE":
        return "INSUFFICIENT_EVIDENCE"
    stop = _decimal(plan.get("stop"), positive=True, error="BUNDLE_PLAN_INVALID")
    tp1 = _decimal(plan.get("tp1"), positive=True, error="BUNDLE_PLAN_INVALID")
    tp2 = _decimal(plan.get("tp2"), positive=True, error="BUNDLE_PLAN_INVALID")
    for candle in candles:
        stop_hit = candle.low <= stop if side == Side.LONG.value else candle.high >= stop
        tp1_hit = candle.high >= tp1 if side == Side.LONG.value else candle.low <= tp1
        tp2_hit = candle.high >= tp2 if side == Side.LONG.value else candle.low <= tp2
        if stop_hit and (tp1_hit or tp2_hit):
            return "AMBIGUOUS_SAME_CANDLE"
        if stop_hit:
            return "STOP_FIRST"
        if tp2_hit:
            return "TP2_REACHED"
        if tp1_hit:
            return "TP1_FIRST"
    return "NO_PLAN_LEVEL_HIT"


def _findings(
    *,
    planned_entry: Decimal,
    actual_entry: Decimal,
    planned_quantity: Decimal,
    actual_quantity: Decimal,
    fees: Decimal,
    path: str,
    coverage: str,
) -> list[str]:
    findings: list[str] = []
    if actual_entry == planned_entry and actual_quantity == planned_quantity:
        findings.append("PLAN_FOLLOWED")
    if actual_entry != planned_entry:
        findings.append("ENTRY_DEVIATION")
    if actual_quantity != planned_quantity:
        findings.append("SIZE_DEVIATION")
    if fees > 0:
        findings.append("FEE_DRAG")
    if path == "AMBIGUOUS_SAME_CANDLE":
        findings.append("AMBIGUOUS_PATH")
    if coverage != "COMPLETE":
        findings.append("INSUFFICIENT_EVIDENCE")
    return findings


_OUTCOME_FIELDS = frozenset(
    {
        "outcome_version",
        "outcome_id",
        "canonical_hash",
        "bundle_id",
        "bundle_hash",
        "decision_hash",
        "card_id",
        "card_hash",
        "shadow_order_id",
        "shadow_order_hash",
        "setup_id",
        "setup_hash",
        "plan_id",
        "plan_hash",
        "symbol",
        "side",
        "speed",
        "planned_quantity",
        "actual_quantity",
        "weighted_entry",
        "weighted_exit",
        "entry_deviation",
        "quantity_deviation",
        "total_fees",
        "gross_pnl",
        "net_pnl",
        "planned_risk",
        "r_multiple",
        "mfe",
        "mae",
        "actual_execution_outcome",
        "hypothetical_plan_path",
        "replay_coverage",
        "replay_start_open_time_ms",
        "replay_end_open_time_ms",
        "replay_candle_hashes",
        "learning_findings",
        "manual_execution_id",
        "manual_execution_hash",
        "submission_status",
        "manual_execution_required",
        "derivation",
    }
)


def _validate_outcome(payload: dict[str, object]) -> None:
    if set(payload) != _OUTCOME_FIELDS or payload.get("outcome_version") != OUTCOME_VERSION:
        raise OutcomeError("OUTCOME_FIELDS_INVALID")
    if payload.get("outcome_id") != payload.get("canonical_hash") or payload[
        "outcome_id"
    ] != _digest(OUTCOME_HASH_DOMAIN, payload, omit=("outcome_id", "canonical_hash")):
        raise OutcomeError("OUTCOME_HASH_INVALID")
    if payload.get("symbol") != "ETH" or payload.get("side") not in {"LONG", "SHORT"}:
        raise OutcomeError("OUTCOME_AUTHORITY_INVALID")
    for field in (
        "planned_quantity",
        "actual_quantity",
        "weighted_entry",
        "weighted_exit",
        "planned_risk",
    ):
        _decimal(payload.get(field), positive=True, error="OUTCOME_FINANCIAL_INVALID")
    for field in (
        "entry_deviation",
        "quantity_deviation",
        "total_fees",
        "gross_pnl",
        "net_pnl",
        "r_multiple",
        "mfe",
        "mae",
    ):
        if payload.get(field) is not None:
            _signed_decimal(payload.get(field), "OUTCOME_FINANCIAL_INVALID")
    if payload.get("actual_execution_outcome") != "CLOSED_MANUAL_EXECUTION":
        raise OutcomeError("OUTCOME_AUTHORITY_INVALID")
    if payload.get("hypothetical_plan_path") not in {
        "STOP_FIRST",
        "TP1_FIRST",
        "TP2_REACHED",
        "NO_PLAN_LEVEL_HIT",
        "AMBIGUOUS_SAME_CANDLE",
        "INSUFFICIENT_EVIDENCE",
    }:
        raise OutcomeError("OUTCOME_PATH_INVALID")
    derivation = payload.get("derivation")
    if type(derivation) is not dict or set(derivation) != {
        "bundle",
        "manual_execution",
        "candle_evidence",
    }:
        raise OutcomeError("OUTCOME_DERIVATION_INVALID")
    try:
        bundle = DecisionBundleV1(cast(dict[str, object], derivation["bundle"]))
        manual = ManualExecutionImportV1(cast(dict[str, object], derivation["manual_execution"]))
        candles = read_candle_evidence(
            canonical_json_bytes(
                {"candle_evidence_version": "1", "candles": derivation["candle_evidence"]}
            )
        )
        expected = _derive_outcome(bundle=bundle, manual_execution=manual, candles=candles)
    except (TypeError, ValueError, KeyError) as exc:
        raise OutcomeError("OUTCOME_DERIVATION_INVALID") from exc
    if expected != payload:
        raise OutcomeError("OUTCOME_DERIVATION_MISMATCH")


@dataclass(frozen=True)
class OutcomeRecordV1:
    """The hash-bound, offline learning record for one closed manual trade."""

    payload: dict[str, object]

    def __post_init__(self) -> None:
        _validate_outcome(self.payload)

    @property
    def outcome_id(self) -> str:
        return cast(str, self.payload["outcome_id"])

    def canonical_json(self) -> bytes:
        return canonical_json_bytes(self.payload)

    @classmethod
    def from_json(cls, raw: bytes) -> OutcomeRecordV1:
        return cls(_strict_object(raw, "OUTCOME_JSON_INVALID"))


def _derive_outcome(
    *,
    bundle: DecisionBundleV1,
    manual_execution: ManualExecutionImportV1,
    candles: tuple[Candle, ...],
) -> dict[str, object]:
    """Match a closed manual import and calculate only deterministic offline evidence."""
    bundle.__post_init__()
    manual_execution.__post_init__()
    decision = cast(dict[str, object], bundle.payload["decision_record"])
    plan = cast(dict[str, object], bundle.payload["trade_plan"])
    if decision["decision"] != HumanDecision.TAKEN.value:
        raise OutcomeError("MANUAL_IMPORT_DECISION_NOT_TAKEN")
    if manual_execution.decision_hash != bundle.decision_hash:
        raise OutcomeError("MANUAL_IMPORT_DECISION_MISMATCH")
    card_data = cast(dict[str, object], bundle.payload["operator_card"])
    card_payload = cast(dict[str, object], card_data["payload"])
    if manual_execution.payload["side"] != card_payload.get("side"):
        raise OutcomeError("MANUAL_IMPORT_SIDE_MISMATCH")
    entries, exits = (
        _fills(manual_execution.payload, "entry_fills"),
        _fills(manual_execution.payload, "exit_fills"),
    )
    quantity: Decimal = sum((item[2] for item in entries), Decimal(0))
    if quantity != sum((item[2] for item in exits), Decimal(0)):
        raise OutcomeError("MANUAL_IMPORT_RESIDUAL_OPEN_QUANTITY")
    weighted_entry: Decimal = sum((item[1] * item[2] for item in entries), Decimal(0)) / quantity
    weighted_exit: Decimal = sum((item[1] * item[2] for item in exits), Decimal(0)) / quantity
    fees: Decimal = sum((item[3] for item in [*entries, *exits]), Decimal(0))
    side = cast(str, manual_execution.payload["side"])
    gross = (
        (weighted_exit - weighted_entry) * quantity
        if side == "LONG"
        else (weighted_entry - weighted_exit) * quantity
    )
    net = gross - fees
    planned_risk = _decimal(
        bundle.payload["planned_risk"], positive=True, error="BUNDLE_PLANNED_RISK_INVALID"
    )
    window, coverage = _replay_window(candles, entries[0][0], exits[-1][0])
    mfe: Decimal | None
    mae: Decimal | None
    start_open: int | None
    end_open: int | None
    if coverage == "COMPLETE":
        high, low = max(item.high for item in window), min(item.low for item in window)
        mfe = (
            (high - weighted_entry) * quantity
            if side == "LONG"
            else (weighted_entry - low) * quantity
        )
        mae = (
            (low - weighted_entry) * quantity
            if side == "LONG"
            else (weighted_entry - high) * quantity
        )
        start_open, end_open = window[0].open_time_ms, window[-1].open_time_ms
        hashes: list[str] = [item.canonical_hash for item in window]
    else:
        mfe = mae = None
        start_open = end_open = None
        hashes = []
    path = _path(plan, side, window, coverage)
    planned_entry = _decimal(plan["planned_entry"], positive=True, error="BUNDLE_PLAN_INVALID")
    planned_quantity = _decimal(plan["quantity"], positive=True, error="BUNDLE_PLAN_INVALID")
    card = card_data
    shadow = cast(dict[str, object], bundle.payload["shadow_order"])
    evidence: list[dict[str, object]] = []
    for candle in candles:
        issued = _validated_candle(candle)
        evidence.append(
            {
                "raw_text": issued.evidence.raw_text,
                "received_at": issued.evidence.received_at.isoformat(),
                "receive_sequence": issued.evidence.receive_sequence,
                "connection_id": issued.evidence.connection_id,
            }
        )
    payload: dict[str, object] = {
        "outcome_version": OUTCOME_VERSION,
        "outcome_id": "",
        "canonical_hash": "",
        "bundle_id": bundle.bundle_id,
        "bundle_hash": bundle.canonical_hash,
        "decision_hash": bundle.decision_hash,
        "card_id": card["card_id"],
        "card_hash": card["canonical_hash"],
        "shadow_order_id": shadow["shadow_order_id"],
        "shadow_order_hash": shadow["canonical_hash"],
        "setup_id": bundle.payload["setup_id"],
        "setup_hash": bundle.payload["setup_hash"],
        "plan_id": bundle.payload["plan_id"],
        "plan_hash": bundle.payload["plan_hash"],
        "symbol": "ETH",
        "side": side,
        "speed": plan["speed"],
        "planned_quantity": decimal_to_canonical_string(planned_quantity),
        "actual_quantity": decimal_to_canonical_string(quantity),
        "weighted_entry": decimal_to_canonical_string(weighted_entry),
        "weighted_exit": decimal_to_canonical_string(weighted_exit),
        "entry_deviation": decimal_to_canonical_string(weighted_entry - planned_entry),
        "quantity_deviation": decimal_to_canonical_string(quantity - planned_quantity),
        "total_fees": decimal_to_canonical_string(fees),
        "gross_pnl": decimal_to_canonical_string(gross),
        "net_pnl": decimal_to_canonical_string(net),
        "planned_risk": decimal_to_canonical_string(planned_risk),
        "r_multiple": decimal_to_canonical_string(net / planned_risk),
        "mfe": None if mfe is None else decimal_to_canonical_string(mfe),
        "mae": None if mae is None else decimal_to_canonical_string(mae),
        "actual_execution_outcome": "CLOSED_MANUAL_EXECUTION",
        "hypothetical_plan_path": path,
        "replay_coverage": coverage,
        "replay_start_open_time_ms": start_open,
        "replay_end_open_time_ms": end_open,
        "replay_candle_hashes": hashes,
        "learning_findings": _findings(
            planned_entry=planned_entry,
            actual_entry=weighted_entry,
            planned_quantity=planned_quantity,
            actual_quantity=quantity,
            fees=fees,
            path=path,
            coverage=coverage,
        ),
        "manual_execution_id": manual_execution.payload["manual_execution_id"],
        "manual_execution_hash": manual_execution.payload["canonical_hash"],
        "submission_status": "NOT_SUBMITTED",
        "manual_execution_required": True,
        "derivation": {
            "bundle": bundle.payload,
            "manual_execution": manual_execution.payload,
            "candle_evidence": evidence,
        },
    }
    digest = _digest(OUTCOME_HASH_DOMAIN, payload, omit=("outcome_id", "canonical_hash"))
    payload["outcome_id"] = digest
    payload["canonical_hash"] = digest
    return payload


def build_outcome(
    *,
    bundle: DecisionBundleV1,
    manual_execution: ManualExecutionImportV1,
    candles: tuple[Candle, ...],
) -> OutcomeRecordV1:
    """Match a closed manual import and calculate only deterministic offline evidence."""
    return OutcomeRecordV1(
        _derive_outcome(bundle=bundle, manual_execution=manual_execution, candles=candles)
    )


def _outcome_journal_records(raw: bytes) -> tuple[dict[str, object], ...]:
    if not raw:
        return ()
    if not raw.endswith(b"\n"):
        raise OutcomeError("OUTCOME_JOURNAL_TRUNCATED")
    previous = "0" * 64
    decisions: set[str] = set()
    records: list[dict[str, object]] = []
    for sequence, line in enumerate(raw[:-1].split(b"\n"), 1):
        payload = _strict_object(line, "OUTCOME_JOURNAL_JSON_INVALID")
        fields = {
            "journal_version",
            "sequence",
            "previous_record_hash",
            "record_hash",
            "decision_hash",
            "outcome",
        }
        if (
            set(payload) != fields
            or payload["journal_version"] != OUTCOME_JOURNAL_VERSION
            or payload["sequence"] != sequence
            or payload["previous_record_hash"] != previous
            or type(payload.get("outcome")) is not dict
        ):
            raise OutcomeError("OUTCOME_JOURNAL_FIELDS_INVALID")
        _hash(payload.get("record_hash"), "OUTCOME_JOURNAL_HASH_INVALID")
        _hash(payload.get("decision_hash"), "OUTCOME_JOURNAL_HASH_INVALID")
        if payload["record_hash"] != _digest(
            OUTCOME_JOURNAL_HASH_DOMAIN, payload, omit=("record_hash",)
        ):
            raise OutcomeError("OUTCOME_JOURNAL_HASH_INVALID")
        outcome = OutcomeRecordV1(cast(dict[str, object], payload["outcome"]))
        if payload["decision_hash"] != outcome.payload["decision_hash"]:
            raise OutcomeError("OUTCOME_JOURNAL_DECISION_MISMATCH")
        if payload["decision_hash"] in decisions:
            raise OutcomeError("OUTCOME_JOURNAL_DUPLICATE_DECISION")
        decisions.add(cast(str, payload["decision_hash"]))
        previous = cast(str, payload["record_hash"])
        records.append(payload)
    return tuple(records)


def read_outcome_journal(journal: str | Path) -> tuple[OutcomeRecordV1, ...]:
    path = Path(journal)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return ()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise OutcomeError("OUTCOME_JOURNAL_TARGET_INVALID")
    try:
        records = _outcome_journal_records(path.read_bytes())
    except OSError as exc:
        raise OutcomeError("OUTCOME_JOURNAL_READ_FAILED") from exc
    return tuple(OutcomeRecordV1(cast(dict[str, object], record["outcome"])) for record in records)


def append_outcome(journal: str | Path, *, outcome: OutcomeRecordV1) -> OutcomeRecordV1:
    """Atomically append one outcome per decision hash to a local hash-chain."""
    outcome.__post_init__()
    path = Path(journal)
    lock = path.with_name(path.name + ".lock")
    try:
        lock_fd = os.open(
            lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600
        )
    except FileExistsError as exc:
        raise OutcomeError("OUTCOME_JOURNAL_LOCKED") from exc
    except OSError as exc:
        raise OutcomeError("OUTCOME_JOURNAL_LOCK_FAILED") from exc
    try:
        lock_info = os.fstat(lock_fd)
    except OSError as exc:
        os.close(lock_fd)
        raise OutcomeError("OUTCOME_JOURNAL_LOCK_FAILED") from exc
    if not stat.S_ISREG(lock_info.st_mode):
        os.close(lock_fd)
        raise OutcomeError("OUTCOME_JOURNAL_LOCK_INVALID")
    lock_identity = (lock_info.st_dev, lock_info.st_ino)
    try:
        try:
            fd = os.open(
                path, os.O_CREAT | os.O_RDWR | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0), 0o600
            )
        except OSError as exc:
            raise OutcomeError("OUTCOME_JOURNAL_APPEND_FAILED") from exc
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise OutcomeError("OUTCOME_JOURNAL_TARGET_INVALID")
            identity = (info.st_dev, info.st_ino)
            os.lseek(fd, 0, os.SEEK_SET)
            old = b"".join(iter(lambda: os.read(fd, 65_536), b""))
            records = _outcome_journal_records(old)
            if any(
                record["decision_hash"] == outcome.payload["decision_hash"] for record in records
            ):
                raise OutcomeError("OUTCOME_JOURNAL_DUPLICATE_DECISION")
            payload: dict[str, object] = {
                "journal_version": OUTCOME_JOURNAL_VERSION,
                "sequence": len(records) + 1,
                "previous_record_hash": records[-1]["record_hash"] if records else "0" * 64,
                "record_hash": "",
                "decision_hash": outcome.payload["decision_hash"],
                "outcome": outcome.payload,
            }
            payload["record_hash"] = _digest(
                OUTCOME_JOURNAL_HASH_DOMAIN, payload, omit=("record_hash",)
            )
            encoded = canonical_json_bytes(payload) + b"\n"
            current = path.stat(follow_symlinks=False)
            if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != identity:
                raise OutcomeError("OUTCOME_JOURNAL_IDENTITY_CHANGED")
            original_size = len(old)
            try:
                written = os.write(fd, encoded)
                if written != len(encoded):
                    raise OSError("partial write")
                os.fsync(fd)
                os.lseek(fd, 0, os.SEEK_SET)
                _outcome_journal_records(b"".join(iter(lambda: os.read(fd, 65_536), b"")))
                current = path.stat(follow_symlinks=False)
                if (
                    not stat.S_ISREG(current.st_mode)
                    or (current.st_dev, current.st_ino) != identity
                ):
                    raise OutcomeError("OUTCOME_JOURNAL_IDENTITY_CHANGED")
            except (OSError, OutcomeError) as exc:
                try:
                    os.ftruncate(fd, original_size)
                    os.fsync(fd)
                except OSError as rollback_exc:
                    raise OutcomeError("OUTCOME_JOURNAL_ROLLBACK_FAILED") from rollback_exc
                raise OutcomeError("OUTCOME_JOURNAL_APPEND_FAILED") from exc
            return outcome
        finally:
            os.close(fd)
    finally:
        os.close(lock_fd)
        try:
            current = lock.stat(follow_symlinks=False)
        except FileNotFoundError:
            raise OutcomeError("OUTCOME_JOURNAL_LOCK_IDENTITY_CHANGED") from None
        if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != lock_identity:
            raise OutcomeError("OUTCOME_JOURNAL_LOCK_IDENTITY_CHANGED")
        try:
            lock.unlink()
        except FileNotFoundError:
            raise OutcomeError("OUTCOME_JOURNAL_LOCK_IDENTITY_CHANGED") from None


def read_candle_evidence(raw: bytes) -> tuple[Candle, ...]:
    """Recreate parser-issued ETH candles from canonical local raw-evidence records."""
    payload = _strict_object(raw, "CANDLE_EVIDENCE_JSON_INVALID")
    if (
        set(payload) != {"candle_evidence_version", "candles"}
        or payload.get("candle_evidence_version") != "1"
        or type(payload.get("candles")) is not list
    ):
        raise OutcomeError("CANDLE_EVIDENCE_FIELDS_INVALID")
    candles: list[Candle] = []
    for item in cast(list[object], payload["candles"]):
        if type(item) is not dict or set(item) != {
            "raw_text",
            "received_at",
            "receive_sequence",
            "connection_id",
        }:
            raise OutcomeError("CANDLE_EVIDENCE_FIELDS_INVALID")
        evidence = cast(dict[str, object], item)
        received = _timestamp(evidence["received_at"], "CANDLE_EVIDENCE_TIMESTAMP_INVALID")
        if (
            type(evidence["receive_sequence"]) is not int
            or type(evidence["connection_id"]) is not str
            or type(evidence["raw_text"]) is not str
        ):
            raise OutcomeError("CANDLE_EVIDENCE_FIELDS_INVALID")
        try:
            candles.append(
                candle_from_websocket(
                    evidence["raw_text"],
                    evidence_from_raw(
                        evidence["raw_text"],
                        operation="WebSocket",
                        received_at=received,
                        receive_sequence=evidence["receive_sequence"],
                        connection_id=evidence["connection_id"],
                    ),
                )
            )
        except MarketDataError as exc:
            raise OutcomeError("CANDLE_EVIDENCE_INVALID") from exc
    return tuple(candles)


def main() -> int:
    """Run deterministic local matching; this command cannot submit an order."""
    parser = argparse.ArgumentParser(description="Offline manual ETH outcome replay")
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--manual-execution", type=Path, required=True)
    parser.add_argument("--candle-evidence", type=Path, required=True)
    parser.add_argument("--journal", type=Path)
    args = parser.parse_args()
    try:
        bundle = DecisionBundleV1.from_json(args.bundle.read_bytes())
        execution = ManualExecutionImportV1.from_json(args.manual_execution.read_bytes())
        outcome = build_outcome(
            bundle=bundle,
            manual_execution=execution,
            candles=read_candle_evidence(args.candle_evidence.read_bytes()),
        )
        if args.journal is not None:
            append_outcome(args.journal, outcome=outcome)
    except (OSError, OutcomeError) as exc:
        parser.error(str(exc))
    print("OFFLINE ONLY")
    print("MANUAL EXECUTION")
    print("NOT SUBMITTED")
    print("NO ACCOUNT OR EXCHANGE WRITE")
    print(
        "OUTCOME "
        + f"{outcome.outcome_id} NET_PNL {outcome.payload['net_pnl']} "
        + f"R {outcome.payload['r_multiple']} PATH {outcome.payload['hypothetical_plan_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
