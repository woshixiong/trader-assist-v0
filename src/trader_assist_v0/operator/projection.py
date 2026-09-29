"""Read-only projection from retained Three Setup source evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow.l1_approval import (
    ApprovalMode,
    AuthorityMode,
    StrategyOrderPackage,
)
from trader_assist_v0.multi_asset_shadow.shadow_records.records import ImmutableRecord, RecordError
from trader_assist_v0.multi_asset_shadow.shadow_records.store import ReadOnlyEvidenceSnapshot

from .contracts import OperatorConfig


class ProjectionBlocked(ValueError):
    """Source evidence cannot authorize an exact reviewable package."""


@dataclass(frozen=True)
class SourceProjection:
    package: StrategyOrderPackage
    source_refs: dict[str, str]
    snapshot_digest: str
    activation_id: str
    observed_ms: int


def _decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ProjectionBlocked("source numeric field is invalid") from exc
    if not result.is_finite() or result <= 0:
        raise ProjectionBlocked("source numeric field is not positive finite")
    return result


def _timestamp_ms(value: object) -> int:
    if not isinstance(value, str):
        raise ProjectionBlocked("source timestamp is unavailable")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone is required")
        return int(parsed.astimezone(UTC).timestamp() * 1000)
    except ValueError as exc:
        raise ProjectionBlocked("source timestamp is invalid") from exc


def _linked(
    source: ReadOnlyEvidenceSnapshot, shadow: ImmutableRecord
) -> tuple[ImmutableRecord, ImmutableRecord, ImmutableRecord, ImmutableRecord]:
    payload = shadow.payload
    signal = source.exact(str(payload["signal_id"]), "formal_signal")
    plan = source.exact(str(payload["plan_id"]), "plan_record")
    event = source.exact(str(payload["market_event_id"]), "market_event")
    provenance = source.exact(str(payload["provenance_id"]), "provenance")
    if (
        signal.payload.get("market_event_id") != event.record_id
        or signal.payload.get("provenance_id") != provenance.record_id
        or plan.payload.get("signal_id") != signal.record_id
        or plan.payload.get("provenance_id") != provenance.record_id
        or payload.get("signal_id") != signal.record_id
        or payload.get("market_id") != signal.payload.get("market_id")
        or payload.get("market_id") != event.payload.get("market_id")
        or payload.get("side") != signal.payload.get("side")
        or payload.get("setup_family") != signal.payload.get("setup_family")
    ):
        raise ProjectionBlocked("retained source linkage conflicts")
    for field in ("planned_entry", "stop", "tp1", "tp2", "risk_reference_sizing"):
        if payload.get(field) != plan.payload.get(field):
            raise ProjectionBlocked("retained plan differs from Shadow")
    for field in (
        "strategy_version",
        "parameter_version",
        "registry_version",
        "registry_hash",
        "cost_model_version",
    ):
        if payload.get(field) != provenance.payload.get(field):
            raise ProjectionBlocked("source version identity conflicts")
    return signal, plan, event, provenance


def project_post_activation(
    source: ReadOnlyEvidenceSnapshot,
    config: OperatorConfig,
    *,
    shadow_id: str | None = None,
    observed_ms: int,
) -> SourceProjection:
    try:
        shadow = (
            source.latest_shadow() if shadow_id is None else source.exact(shadow_id, "shadow_order")
        )
        if shadow is None:
            raise ProjectionBlocked("no retained ShadowOrder")
        latest_shadow = source.latest_shadow()
        if latest_shadow is None or latest_shadow.record_id != shadow.record_id:
            raise ProjectionBlocked("Shadow package is stale or superseded")
        signal, plan, event, provenance = _linked(source, shadow)
        payload = shadow.payload
        if payload.get("submission_status") != "NOT_SUBMITTED":
            raise ProjectionBlocked("source is not zero-write Shadow evidence")
        reference = payload.get("risk_reference_sizing")
        if not isinstance(reference, dict) or config.reference_scenario is None:
            raise ProjectionBlocked("REFERENCE_SCENARIO_UNRESOLVED")
        suffix = "1pct" if config.reference_scenario == "1pct" else "2pct"
        pct_key = "risk_pct_1" if suffix == "1pct" else "risk_pct_2"
        quantity = _decimal(reference.get("reference_qty_" + suffix))
        notional = _decimal(reference.get("reference_notional_" + suffix))
        entry = _decimal(payload["planned_entry"])
        if quantity * entry != notional:
            raise ProjectionBlocked("reference notional does not match retained quantity")
        equity = _decimal(reference.get("reference_equity_usd"))
        risk_budget = equity * _decimal(reference.get(pct_key)) / Decimal(100)
        if reference.get("not_account_authoritative") != "YES":
            raise ProjectionBlocked("reference scenario claims account authority")
        evaluation_id = signal.payload.get("strategy_evaluation_id")
        evaluations = (
            source.matching("strategy_evaluation", "evaluation_id", str(evaluation_id))
            if evaluation_id is not None
            else ()
        )
        if len(evaluations) != 1:
            raise ProjectionBlocked("exact Strategy evaluation is unavailable")
        evaluation = evaluations[0]
        if evaluation.payload.get("market_id") != payload.get("market_id"):
            raise ProjectionBlocked("Strategy evaluation market conflicts")
        latest_evaluation = source.latest_strategy(str(payload["market_id"]))
        if latest_evaluation is None or latest_evaluation.record_id != evaluation.record_id:
            raise ProjectionBlocked("Shadow Strategy evidence is stale or superseded")
        created_ms = _timestamp_ms(payload["created_at"])
        source_hashes = {
            "shadow": shadow.canonical_hash,
            "signal": signal.canonical_hash,
            "plan": plan.canonical_hash,
            "market_event": event.canonical_hash,
            "provenance": provenance.canonical_hash,
            "strategy_evaluation": evaluation.canonical_hash,
        }
        source_ids = {
            "shadow": shadow.record_id,
            "signal": signal.record_id,
            "plan": plan.record_id,
            "market_event": event.record_id,
            "provenance": provenance.record_id,
            "strategy_evaluation": evaluation.record_id,
        }
        refs = {
            key: value
            for name in source_ids
            for key, value in (
                (name + ".id", source_ids[name]),
                (name + ".hash", source_hashes[name]),
            )
        }
        details: dict[str, object] = {
            "approval_mode": ApprovalMode.POST_ACTIVATION.value,
            "source_ids": source_ids,
            "source_hashes": source_hashes,
            "market_id": str(payload["market_id"]),
            "instrument_id": payload.get("instrument_id"),
            "side": str(payload["side"]),
            "setup_family": str(payload["setup_family"]),
            "setup_mode": payload.get("setup_mode"),
            "registry_version": str(payload["registry_version"]),
            "registry_hash": str(payload["registry_hash"]),
            "cost_model_version": str(payload["cost_model_version"]),
            "policy_version": payload.get("policy_version"),
            "max_approved_entry": payload.get("max_approved_entry"),
            "planned_entry": str(payload["planned_entry"]),
            "stop": str(payload["stop"]),
            "tp1": str(payload["tp1"]),
            "tp2": payload.get("tp2"),
            "reference_scenario": config.reference_scenario,
            "reference_quantity": str(quantity),
            "reference_notional": str(notional),
            "reference_risk_budget_usd": str(risk_budget),
            "reference_only": True,
            "activation_id": event.record_id,
            "activation_trigger_id": str(event.payload.get("kernel_market_event_id", "")),
            "submission_status": "NOT_SUBMITTED",
            "execution_eligible": False,
        }
        if not details["activation_trigger_id"]:
            raise ProjectionBlocked("exact Activation trigger is unavailable")
        package = StrategyOrderPackage.create(
            parent_strategy_order_id=shadow.record_id,
            strategy_version=str(payload["strategy_version"]),
            parameter_version=str(payload["parameter_version"]),
            created_server_ms=created_ms,
            expires_server_ms=created_ms + config.approval_ttl_ms,
            activation_opportunity_id=event.record_id,
            authority_mode=AuthorityMode.ZERO_WRITE,
            legs=(),
            ts8_details=details,
        )
        return SourceProjection(
            package=package,
            source_refs=refs,
            snapshot_digest=sha256_hex(
                canonical_json_bytes(
                    {
                        "refs": refs,
                        "observed_ms": observed_ms,
                        "strategy_boundary_ms": evaluation.payload["evaluation_boundary_ms"],
                        "current_market_health": "UNAVAILABLE_FAIL_CLOSED",
                    }
                )
            ),
            activation_id=event.record_id,
            observed_ms=observed_ms,
        )
    except (RecordError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, ProjectionBlocked):
            raise
        raise ProjectionBlocked("authoritative projection is unavailable") from exc


def project_preauthorized_armed(
    _source: ReadOnlyEvidenceSnapshot, _config: OperatorConfig, *, _observed_ms: int
) -> SourceProjection:
    """Existing evidence lacks exact pre-Activation sizing/trigger terms.

    Preserve the mode contract but never guess a reviewable package from an
    active MarketEvent or E4 ARMED label alone.
    """
    raise ProjectionBlocked("PREAUTHORIZED_ARMED_EXACT_FIELDS_UNPROVEN")


def prove_later_activation(
    source: ReadOnlyEvidenceSnapshot,
    config: OperatorConfig,
    package: StrategyOrderPackage,
    *,
    observed_ms: int,
    approved_ms: int,
) -> SourceProjection | None:
    """Match one later retained Activation to a previously approved condition."""
    details = package.ts8_details
    if details is None or details.get("approval_mode") != ApprovalMode.PREAUTHORIZED_ARMED.value:
        raise ProjectionBlocked("package is not preauthorized")
    trigger = details.get("activation_trigger_id")
    if not isinstance(trigger, str) or not trigger:
        raise ProjectionBlocked("approved trigger is missing")
    source_ids = details.get("source_ids")
    source_hashes = details.get("source_hashes")
    if not isinstance(source_ids, dict) or not isinstance(source_hashes, dict):
        raise ProjectionBlocked("approved source identity is incomplete")
    for name, record_id in source_ids.items():
        if not isinstance(name, str) or not isinstance(record_id, str):
            raise ProjectionBlocked("approved source identity is invalid")
        record = source.get(record_id)
        if record is None or record.canonical_hash != source_hashes.get(name):
            raise ProjectionBlocked("approved ARMED source changed or disappeared")
    events = source.matching("market_event", "kernel_market_event_id", trigger)
    if not events:
        return None
    if len(events) != 1:
        raise ProjectionBlocked("Activation identity is ambiguous")
    event = events[0]
    if (
        event.payload.get("market_id") != details.get("market_id")
        or event.payload.get("side") != details.get("side")
        or event.payload.get("setup_family") != details.get("setup_family")
    ):
        raise ProjectionBlocked("Activation differs from approved condition")
    shadows = source.matching("shadow_order", "market_event_id", event.record_id)
    if len(shadows) != 1:
        raise ProjectionBlocked("Activation has no unique retained Shadow package")
    current = project_post_activation(
        source, config, shadow_id=shadows[0].record_id, observed_ms=observed_ms
    )
    current_details = current.package.ts8_details
    if current_details is None:
        raise ProjectionBlocked("activated package details are missing")
    for field in (
        "market_id",
        "side",
        "setup_family",
        "setup_mode",
        "planned_entry",
        "stop",
        "tp1",
        "tp2",
        "reference_scenario",
        "reference_quantity",
        "reference_notional",
        "reference_risk_budget_usd",
        "registry_version",
        "registry_hash",
        "cost_model_version",
    ):
        if details.get(field) != current_details.get(field):
            raise ProjectionBlocked("Activation changes approved conditional package")
    if package.strategy_version != current.package.strategy_version or (
        package.parameter_version != current.package.parameter_version
    ):
        raise ProjectionBlocked("Activation changes approved versions")
    if package.activation_opportunity_id != trigger:
        raise ProjectionBlocked("approved Opportunity differs from trigger")
    activation_ms = _timestamp_ms(event.payload.get("event_time"))
    armed_ms = details.get("armed_ts_ms")
    if (
        not isinstance(armed_ms, int)
        or not armed_ms < approved_ms < activation_ms
        or observed_ms < activation_ms
    ):
        raise ProjectionBlocked("ARMED-to-Activation chronology is unproven")
    return current
