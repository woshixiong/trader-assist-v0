# mypy: disable-error-code="import-not-found"
"""Source-bound, rebuildable replay payload bridge over accepted E4 evidence."""

from __future__ import annotations

import hmac
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from trader_assist_v0.contracts.common import Sha256Hex, canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow.models import RegistryMarket
from trader_assist_v0.multi_asset_shadow.strategy_kernel.types import (
    DecisionKind,
    Side,
    StrategyDecision,
)
from trader_assist_v0.nautilus_e4.contracts import (
    AdmittedEvent,
    DataKind,
    EvidenceState,
    LifecycleKind,
    LifecycleRecord,
    LifecycleStatus,
    MarketExpression,
)
from trader_assist_v0.vnext_g4.contracts import (
    CausalLineage,
    DerivationStatus,
    DerivedReplayCacheIdentity,
    EvidenceArtifactHash,
    G4RunManifest,
    HypotheticalOrderIntent,
    PositionSide,
    RestartReferenceEvidence,
    TechnicalOrderQuantity,
    ValidationReference,
)
from trader_assist_v0.vnext_g4.evaluator import EvaluationInputs

TRANSFORM_VERSION = "E4_ADMITTED_TO_G4_REPLAY_V1"
NATIVE_REPLAY_TRANSFORM_VERSION: Literal[
    "E4_ADMITTED_TO_NAUTILUS_RC5_NATIVE_REPLAY_V1"
] = "E4_ADMITTED_TO_NAUTILUS_RC5_NATIVE_REPLAY_V1"
_SUPPLEMENT_DOMAIN = b"trader-assist-v0/vnext-g4/evaluator-supplement/v2r2\0"
_NATIVE_EVENT_DOMAIN = b"trader-assist-v0/nautilus-g4/native-replay-event/v1\0"
_NATIVE_CONTENT_DOMAIN = b"trader-assist-v0/nautilus-g4/native-replay-content/v1\0"
_NATIVE_PROJECTION_DOMAIN = b"trader-assist-v0/nautilus-g4/native-replay-projection/v1\0"

_TERMINAL_THESIS_FAMILIES = frozenset(
    {
        "STRUCTURAL_THESIS_INVALIDATION",
        "FULFILLED_AT_CONCRETE_STRUCTURAL_TARGET",
        "SUPERSEDED_BY_NEWER_FORMAL_SETUP_FOR_SAME_MARKET",
    }
)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DerivedBoolean(_FrozenModel):
    """A causal boolean with explicit current evaluability and frozen history."""

    status: DerivationStatus
    value: bool | None
    last_causally_defensible_value: bool | None
    reason_codes: tuple[str, ...]


class RestartSequenceDerivation(_FrozenModel):
    status: DerivationStatus
    restart_reference_crossed: bool | None
    retest_seen: bool | None
    current_executable_price: Decimal | None
    break_ordinal: int | None = None
    return_ordinal: int | None = None
    reaccel_ordinal: int | None = None
    reason_codes: tuple[str, ...]


class EconomicsDerivation(_FrozenModel):
    status: DerivationStatus
    economics_can_improve: bool | None
    a_now_empty: bool | None
    current_executable_price: Decimal | None
    current_remaining_room_bps: Decimal | None
    best_admissible_price: Decimal | None
    best_room_to_cost: Decimal | None
    reason_codes: tuple[str, ...]


class EvaluatorSupplementEvidence(_FrozenModel):
    """Exact source-bound values still owned by the frozen evaluator contract."""

    causal_lineage_hash: Sha256Hex
    source_artifact_hash: Sha256Hex
    microstructure_warmup_seconds: int = Field(ge=0)
    side_adjusted_aggressor_imbalance_15s: Decimal
    flow_price_response_15s_bps: Decimal
    supplement_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"supplement_hash"})

    @model_validator(mode="after")
    def verify_identity(self) -> Self:
        expected = sha256_hex(
            _SUPPLEMENT_DOMAIN + canonical_json_bytes(self.identity_payload())
        )
        if not hmac.compare_digest(self.supplement_hash, expected):
            raise ValueError("supplement_hash does not bind exact evaluator evidence")
        return self

    @classmethod
    def create(cls, **values: object) -> Self:
        digest = sha256_hex(_SUPPLEMENT_DOMAIN + canonical_json_bytes(values))
        return cls.model_validate({**values, "supplement_hash": digest})


class EvaluationAdmission(_FrozenModel):
    status: DerivationStatus
    inputs: EvaluationInputs | None
    thesis_valid: DerivedBoolean
    restart_sequence: RestartSequenceDerivation
    economics: EconomicsDerivation
    reason_codes: tuple[str, ...]


class OrderIntentAdmission(_FrozenModel):
    status: DerivationStatus
    intent: HypotheticalOrderIntent | None
    reason_codes: tuple[str, ...]


def _native_content_hash(event_hashes: tuple[Sha256Hex, ...]) -> Sha256Hex:
    return sha256_hex(
        _NATIVE_CONTENT_DOMAIN
        + canonical_json_bytes({"ordered_native_event_hashes": event_hashes})
    )


class NativeReplayProjectionIdentity(_FrozenModel):
    """Immutable source and exact native-content identity for one projection."""

    schema_version: Literal["NATIVE_REPLAY_PROJECTION_V1"] = "NATIVE_REPLAY_PROJECTION_V1"
    transform_version: Literal["E4_ADMITTED_TO_NAUTILUS_RC5_NATIVE_REPLAY_V1"] = (
        NATIVE_REPLAY_TRANSFORM_VERSION
    )
    market_id: Sha256Hex
    expression_id: str
    instrument_id: str
    ordered_source_admission_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)
    ordered_native_event_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)
    native_content_hash: Sha256Hex
    event_count: int = Field(ge=1)
    quote_tick_count: int = Field(ge=0)
    trade_tick_count: int = Field(ge=0)
    bar_count: int = Field(ge=0)
    projection_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"projection_hash"})

    @model_validator(mode="after")
    def verify_identity(self) -> Self:
        if len(self.ordered_source_admission_hashes) != self.event_count:
            raise ValueError("source admission hash count does not match projected event count")
        if len(self.ordered_native_event_hashes) != self.event_count:
            raise ValueError("native event hash count does not match projected event count")
        if self.quote_tick_count + self.trade_tick_count + self.bar_count != self.event_count:
            raise ValueError("native replay type counts do not match projected event count")
        expected_content = _native_content_hash(self.ordered_native_event_hashes)
        if not hmac.compare_digest(self.native_content_hash, expected_content):
            raise ValueError("native_content_hash does not bind ordered native events")
        expected_projection = sha256_hex(
            _NATIVE_PROJECTION_DOMAIN + canonical_json_bytes(self.identity_payload())
        )
        if not hmac.compare_digest(self.projection_hash, expected_projection):
            raise ValueError("projection_hash does not bind source and native replay identity")
        return self

    @classmethod
    def create(cls, **values: object) -> Self:
        digest = sha256_hex(
            _NATIVE_PROJECTION_DOMAIN + canonical_json_bytes(values)
        )
        return cls.model_validate({**values, "projection_hash": digest})


@dataclass(frozen=True, slots=True)
class NativeReplayProjection:
    """Nautilus-native replay events with their deterministic source binding."""

    identity: NativeReplayProjectionIdentity
    events: tuple[object, ...]

    def __post_init__(self) -> None:
        if len(self.events) != self.identity.event_count:
            raise ValueError("native replay events do not match projection identity count")


def _required_payload_text(event: AdmittedEvent, field_name: str) -> str:
    value = event.source.payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{event.source.data_kind.value} payload field {field_name!r} must be non-empty text"
        )
    return value


def _decimal_payload_value(
    event: AdmittedEvent,
    field_name: str,
    *,
    allow_zero: bool,
) -> Decimal:
    raw = _required_payload_text(event, field_name)
    try:
        value = Decimal(raw)
    except Exception as exc:
        raise ValueError(
            f"{event.source.data_kind.value} payload field {field_name!r} is not decimal"
        ) from exc
    if not value.is_finite() or value < 0 or (not allow_zero and value == 0):
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(
            f"{event.source.data_kind.value} payload field {field_name!r} must be {qualifier}"
        )
    return value


def _validate_replayable_payload(event: AdmittedEvent) -> None:
    source = event.source
    if source.data_kind is DataKind.BBO:
        bid = _decimal_payload_value(event, "bid_price", allow_zero=False)
        ask = _decimal_payload_value(event, "ask_price", allow_zero=False)
        _decimal_payload_value(event, "bid_size", allow_zero=True)
        _decimal_payload_value(event, "ask_size", allow_zero=True)
        if bid > ask:
            raise ValueError("BBO payload is crossed")
        return
    if source.data_kind is DataKind.TRADE:
        _decimal_payload_value(event, "price", allow_zero=False)
        _decimal_payload_value(event, "size", allow_zero=False)
        if not source.native_trade_id:
            raise ValueError("TRADE source requires a non-empty native_trade_id")
        if source.provider_aggressor_side not in {"BUYER", "SELLER"}:
            raise ValueError("TRADE provider aggressor side is unknown or ambiguous")
        return
    if source.data_kind is DataKind.BAR:
        values = {
            name: _decimal_payload_value(
                event,
                name,
                allow_zero=name == "volume",
            )
            for name in ("open", "high", "low", "close", "volume")
        }
        if source.payload.get("finalized") is not True:
            raise ValueError("BAR source must truthfully state finalized=true")
        if values["high"] < max(values["open"], values["low"], values["close"]):
            raise ValueError("BAR high does not contain open/low/close")
        if values["low"] > min(values["open"], values["high"], values["close"]):
            raise ValueError("BAR low does not contain open/high/close")
        return
    raise ValueError(f"unsupported native replay data kind: {source.data_kind.value}")


def _validate_projection_sources(
    events: Sequence[AdmittedEvent],
    *,
    market_id: str,
    expression_id: str,
    instrument_id: str,
) -> tuple[AdmittedEvent, ...]:
    ordered = tuple(events)
    if not ordered:
        raise ValueError("native replay projection requires at least one accepted admission")
    ordinals = tuple(event.admission_ordinal for event in ordered)
    if ordinals != tuple(sorted(ordinals)):
        raise ValueError("native replay input is not in accepted causal admission order")
    if len(ordinals) != len(set(ordinals)):
        raise ValueError("native replay input contains duplicate admission ordinals")
    admission_hashes = tuple(event.admission_hash for event in ordered)
    if len(admission_hashes) != len(set(admission_hashes)):
        raise ValueError("native replay input contains duplicate admissions")

    expected_identity = (market_id, expression_id, instrument_id)
    for event in ordered:
        source = event.source
        if event.out_of_order:
            raise ValueError("native replay input contains an out_of_order admission")
        if event.continuity_state is not EvidenceState.COMPLETE:
            raise ValueError("native replay input requires COMPLETE continuity")
        actual_identity = (source.market_id, source.expression_id, source.instrument_id)
        if actual_identity != expected_identity:
            raise ValueError("native replay input contains mixed or unselected market identity")
        _validate_replayable_payload(event)
    return ordered


def _assert_native_text_round_trip(*, field_name: str, source: str, native: object) -> None:
    if str(native) != source:
        raise ValueError(f"native {field_name} conversion is not lossless")


def project_native_replay(
    *,
    events: Sequence[AdmittedEvent],
    market_id: str,
    expression_id: str,
    instrument_id: str,
) -> NativeReplayProjection:
    """Translate one explicitly selected accepted E4 sequence to rc5 native events."""
    ordered = _validate_projection_sources(
        events,
        market_id=market_id,
        expression_id=expression_id,
        instrument_id=instrument_id,
    )

    from nautilus_trader.model import (
        AggressorSide,
        Bar,
        BarType,
        InstrumentId,
        Price,
        Quantity,
        QuoteTick,
        TradeId,
        TradeTick,
    )

    native_instrument_id = InstrumentId.from_str(instrument_id)
    _assert_native_text_round_trip(
        field_name="instrument_id",
        source=instrument_id,
        native=native_instrument_id,
    )
    native_events: list[object] = []
    native_event_hashes: list[Sha256Hex] = []
    counts = {DataKind.BBO: 0, DataKind.TRADE: 0, DataKind.BAR: 0}

    for event in ordered:
        source = event.source
        if source.data_kind is DataKind.BBO:
            bid_price_raw = _required_payload_text(event, "bid_price")
            ask_price_raw = _required_payload_text(event, "ask_price")
            bid_size_raw = _required_payload_text(event, "bid_size")
            ask_size_raw = _required_payload_text(event, "ask_size")
            bid_price = Price.from_str(bid_price_raw)
            ask_price = Price.from_str(ask_price_raw)
            bid_size = Quantity.from_str(bid_size_raw)
            ask_size = Quantity.from_str(ask_size_raw)
            for field_name, raw, native in (
                ("bid_price", bid_price_raw, bid_price),
                ("ask_price", ask_price_raw, ask_price),
                ("bid_size", bid_size_raw, bid_size),
                ("ask_size", ask_size_raw, ask_size),
            ):
                _assert_native_text_round_trip(
                    field_name=field_name,
                    source=raw,
                    native=native,
                )
            native_event = QuoteTick(
                instrument_id=native_instrument_id,
                bid_price=bid_price,
                ask_price=ask_price,
                bid_size=bid_size,
                ask_size=ask_size,
                ts_event=source.ts_event,
                ts_init=source.ts_init,
            )
            native_payload: dict[str, object] = {
                "data_kind": DataKind.BBO.value,
                "instrument_id": str(native_event.instrument_id),
                "bid_price": str(native_event.bid_price),
                "ask_price": str(native_event.ask_price),
                "bid_size": str(native_event.bid_size),
                "ask_size": str(native_event.ask_size),
                "ts_event": native_event.ts_event,
                "ts_init": native_event.ts_init,
            }
        elif source.data_kind is DataKind.TRADE:
            price_raw = _required_payload_text(event, "price")
            size_raw = _required_payload_text(event, "size")
            native_trade_id = source.native_trade_id
            if native_trade_id is None:
                raise ValueError("TRADE source requires a native_trade_id")
            price = Price.from_str(price_raw)
            size = Quantity.from_str(size_raw)
            _assert_native_text_round_trip(field_name="price", source=price_raw, native=price)
            _assert_native_text_round_trip(field_name="size", source=size_raw, native=size)
            aggressor_side = (
                AggressorSide.BUY
                if source.provider_aggressor_side == "BUYER"
                else AggressorSide.SELL
            )
            trade_id = TradeId(native_trade_id)
            _assert_native_text_round_trip(
                field_name="native_trade_id",
                source=native_trade_id,
                native=trade_id,
            )
            native_event = TradeTick(
                instrument_id=native_instrument_id,
                price=price,
                size=size,
                aggressor_side=aggressor_side,
                trade_id=trade_id,
                ts_event=source.ts_event,
                ts_init=source.ts_init,
            )
            if str(native_event.aggressor_side) != source.provider_aggressor_side:
                raise ValueError("native aggressor-side conversion is not lossless")
            native_payload = {
                "data_kind": DataKind.TRADE.value,
                "instrument_id": str(native_event.instrument_id),
                "price": str(native_event.price),
                "size": str(native_event.size),
                "native_trade_id": str(native_event.trade_id),
                "provider_aggressor_side": str(native_event.aggressor_side),
                "ts_event": native_event.ts_event,
                "ts_init": native_event.ts_init,
            }
        else:
            bar_type = BarType.from_str(source.event_context)
            _assert_native_text_round_trip(
                field_name="bar_type",
                source=source.event_context,
                native=bar_type,
            )
            if str(bar_type.instrument_id) != instrument_id:
                raise ValueError("BAR type instrument conflicts with selected instrument")
            raw_values = {
                name: _required_payload_text(event, name)
                for name in ("open", "high", "low", "close", "volume")
            }
            open_price = Price.from_str(raw_values["open"])
            high_price = Price.from_str(raw_values["high"])
            low_price = Price.from_str(raw_values["low"])
            close_price = Price.from_str(raw_values["close"])
            volume = Quantity.from_str(raw_values["volume"])
            native_values = {
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
            }
            for field_name, native in native_values.items():
                _assert_native_text_round_trip(
                    field_name=field_name,
                    source=raw_values[field_name],
                    native=native,
                )
            native_event = Bar(
                bar_type=bar_type,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                ts_event=source.ts_event,
                ts_init=source.ts_init,
            )
            native_payload = {
                "data_kind": DataKind.BAR.value,
                "bar_type": str(native_event.bar_type),
                "open": str(native_event.open),
                "high": str(native_event.high),
                "low": str(native_event.low),
                "close": str(native_event.close),
                "volume": str(native_event.volume),
                "ts_event": native_event.ts_event,
                "ts_init": native_event.ts_init,
            }

        native_events.append(native_event)
        native_event_hashes.append(
            sha256_hex(_NATIVE_EVENT_DOMAIN + canonical_json_bytes(native_payload))
        )
        counts[source.data_kind] += 1

    event_hashes = tuple(native_event_hashes)
    identity = NativeReplayProjectionIdentity.create(
        schema_version="NATIVE_REPLAY_PROJECTION_V1",
        transform_version=NATIVE_REPLAY_TRANSFORM_VERSION,
        market_id=market_id,
        expression_id=expression_id,
        instrument_id=instrument_id,
        ordered_source_admission_hashes=tuple(
            event.admission_hash for event in ordered
        ),
        ordered_native_event_hashes=event_hashes,
        native_content_hash=_native_content_hash(event_hashes),
        event_count=len(ordered),
        quote_tick_count=counts[DataKind.BBO],
        trade_tick_count=counts[DataKind.TRADE],
        bar_count=counts[DataKind.BAR],
    )
    return NativeReplayProjection(identity=identity, events=tuple(native_events))


def build_replay_payload(events: Sequence[AdmittedEvent]) -> bytes:
    """Serialize immutable admitted evidence in its accepted causal order."""
    ordinals = [event.admission_ordinal for event in events]
    if ordinals != sorted(ordinals):
        raise ValueError("G4 replay input is not in accepted causal admission order")
    if len(ordinals) != len(set(ordinals)):
        raise ValueError("G4 replay input contains duplicate admission ordinals")
    payload = {
        "schema_version": "VNEXT_G4_REPLAY_INPUT_V1",
        "transform_version": TRANSFORM_VERSION,
        "events": [event.model_dump(mode="json") for event in events],
    }
    return canonical_json_bytes(payload)


def bind_rebuildable_cache(
    *,
    manifest: G4RunManifest,
    payload: bytes,
) -> DerivedReplayCacheIdentity:
    """Bind a derived cache to immutable E4/G4 source hashes; it is never market truth."""
    artifacts = tuple(
        EvidenceArtifactHash(name=item.name, sha256=item.sha256)
        for item in manifest.source_evidence_artifact_hashes
    )
    return DerivedReplayCacheIdentity.create(
        source_g4_manifest_hash=manifest.manifest_hash,
        source_artifact_hashes=artifacts,
        transform_version=TRANSFORM_VERSION,
        derived_payload_hash=sha256_hex(payload),
    )


def _not_evaluable_bool(
    reason: str,
    *,
    last_value: bool | None = None,
) -> DerivedBoolean:
    return DerivedBoolean(
        status=DerivationStatus.NOT_EVALUABLE,
        value=None,
        last_causally_defensible_value=last_value,
        reason_codes=(reason,),
    )


def derive_thesis_valid(
    *,
    formal_setup_confirmed: bool,
    lineage: CausalLineage,
    records: Sequence[LifecycleRecord],
) -> DerivedBoolean:
    """Derive FORMAL_SETUP_CONFIRMED -> THESIS_CREATED -> ACTIVE_VALID.

    Attempt failure is deliberately ignored as a Thesis terminal family. Any
    incomplete source freezes the last defensible state and makes the current
    evaluation unavailable.
    """
    if not formal_setup_confirmed:
        return _not_evaluable_bool("FORMAL_SETUP_NOT_CONFIRMED")
    ordered = tuple(records)
    order_keys = tuple((item.state_ts, item.last_admission_ordinal) for item in ordered)
    if order_keys != tuple(sorted(order_keys)):
        return _not_evaluable_bool("THESIS_LIFECYCLE_NOT_CAUSALLY_ORDERED")

    created = False
    active_valid = False
    last_value: bool | None = None
    for record in ordered:
        if record.market_id != lineage.market_id:
            return _not_evaluable_bool(
                "THESIS_LIFECYCLE_MARKET_CONFLICT",
                last_value=last_value,
            )
        if record.evidence_state is not EvidenceState.COMPLETE:
            return _not_evaluable_bool(
                f"THESIS_SOURCE_{record.evidence_state.value}",
                last_value=last_value,
            )
        reasons = frozenset(record.reason_codes)
        if record.kind is LifecycleKind.ATTEMPT and "ATTEMPT_FAILURE" in reasons:
            continue
        if record.kind is not LifecycleKind.THESIS or record.object_id != lineage.thesis_id:
            continue
        if last_value is False:
            return _not_evaluable_bool(
                "TERMINAL_THESIS_HISTORY_REWRITE_ATTEMPT",
                last_value=last_value,
            )
        if "THESIS_CREATED" in reasons:
            if record.status is not LifecycleStatus.ACTIVE:
                return _not_evaluable_bool("THESIS_CREATED_NOT_ACTIVE", last_value=last_value)
            if (
                record.state_ts < lineage.formal_setup_admission_ts
                or record.last_admission_ordinal < lineage.formal_setup_admission_ordinal
                or (
                    record.state_ts == lineage.formal_setup_admission_ts
                    and record.last_admission_ordinal
                    == lineage.formal_setup_admission_ordinal
                )
            ):
                return _not_evaluable_bool(
                    "THESIS_CREATED_BEFORE_FORMAL_SETUP",
                    last_value=last_value,
                )
            created = True
            continue
        if "ACTIVE_VALID" in reasons:
            if not created or record.status is not LifecycleStatus.ACTIVE:
                return _not_evaluable_bool(
                    "ACTIVE_VALID_WITHOUT_CREATED_THESIS",
                    last_value=last_value,
                )
            active_valid = True
            last_value = True
            continue
        terminal = reasons & _TERMINAL_THESIS_FAMILIES
        if terminal:
            if not active_valid or record.status not in {
                LifecycleStatus.TERMINAL,
                LifecycleStatus.SUPERSEDED,
            }:
                return _not_evaluable_bool(
                    "THESIS_TERMINAL_SEQUENCE_INVALID",
                    last_value=last_value,
                )
            last_value = False
            continue
        if record.status is not LifecycleStatus.ACTIVE:
            return _not_evaluable_bool(
                "UNRECOGNIZED_THESIS_TERMINAL_FAMILY",
                last_value=last_value,
            )

    if not created or not active_valid:
        return _not_evaluable_bool("THESIS_LIFECYCLE_INCOMPLETE", last_value=last_value)
    assert last_value is not None
    return DerivedBoolean(
        status=DerivationStatus.EVALUABLE,
        value=last_value,
        last_causally_defensible_value=last_value,
        reason_codes=("THESIS_CAUSALLY_DERIVED",),
    )


def _event_health_reason(event: AdmittedEvent, lineage: CausalLineage) -> str | None:
    if (
        event.source.market_id != lineage.market_id
        or event.source.instrument_id != lineage.instrument_id
    ):
        return "SOURCE_MARKET_OR_INSTRUMENT_CONFLICT"
    if event.admission_epoch != lineage.admission_epoch:
        return "SOURCE_ADMISSION_EPOCH_CONFLICT"
    if event.continuity_epoch != lineage.continuity_epoch:
        return "SOURCE_CONTINUITY_EPOCH_CONFLICT"
    if event.out_of_order:
        return "SOURCE_EVENT_OUT_OF_ORDER"
    if event.continuity_state is not EvidenceState.COMPLETE:
        return f"SOURCE_{event.continuity_state.value}"
    return None


def _bbo_values(event: AdmittedEvent) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    if event.source.data_kind is not DataKind.BBO:
        raise ValueError("causal executable-price derivation requires BBO evidence")
    try:
        bid = Decimal(str(event.source.payload["bid_price"]))
        ask = Decimal(str(event.source.payload["ask_price"]))
        bid_size = Decimal(str(event.source.payload["bid_size"]))
        ask_size = Decimal(str(event.source.payload["ask_size"]))
    except (KeyError, ValueError) as exc:
        raise ValueError("BBO evidence does not materialize exact price/size") from exc
    if any(not item.is_finite() or item <= 0 for item in (bid, ask, bid_size, ask_size)):
        raise ValueError("BBO evidence contains non-positive or non-finite state")
    if bid >= ask:
        raise ValueError("BBO evidence is crossed or locked")
    return bid, ask, bid_size, ask_size


def derive_retest_seen(
    *,
    lineage: CausalLineage,
    side: PositionSide,
    events: Sequence[AdmittedEvent],
    references: Sequence[RestartReferenceEvidence],
    attempt_failed_admission_ordinal: int | None = None,
) -> RestartSequenceDerivation:
    """Derive exact BREAK_R -> RETURN_R -> REACCEL_R from causal BBO."""
    ordered_events = tuple(events)
    ordinals = tuple(item.admission_ordinal for item in ordered_events)
    if not ordered_events:
        return RestartSequenceDerivation(
            status=DerivationStatus.NOT_EVALUABLE,
            restart_reference_crossed=None,
            retest_seen=None,
            current_executable_price=None,
            reason_codes=("BBO_EVIDENCE_MISSING",),
        )
    if ordinals != tuple(sorted(ordinals)) or len(ordinals) != len(set(ordinals)):
        return RestartSequenceDerivation(
            status=DerivationStatus.NOT_EVALUABLE,
            restart_reference_crossed=None,
            retest_seen=None,
            current_executable_price=None,
            reason_codes=("BBO_ADMISSION_ORDER_INVALID",),
        )
    ordered_references = tuple(references)
    reference_ordinals = tuple(item.confirmed_admission_ordinal for item in ordered_references)
    if (
        not ordered_references
        or reference_ordinals != tuple(sorted(reference_ordinals))
        or len(reference_ordinals) != len(set(reference_ordinals))
    ):
        return RestartSequenceDerivation(
            status=DerivationStatus.NOT_EVALUABLE,
            restart_reference_crossed=None,
            retest_seen=None,
            current_executable_price=None,
            reason_codes=("RESTART_REFERENCE_MISSING_OR_CONFLICTED",),
        )
    if any(
        item.lineage_hash != lineage.lineage_hash or item.side is not side
        for item in ordered_references
    ):
        return RestartSequenceDerivation(
            status=DerivationStatus.NOT_EVALUABLE,
            restart_reference_crossed=None,
            retest_seen=None,
            current_executable_price=None,
            reason_codes=("RESTART_REFERENCE_LINEAGE_CONFLICT",),
        )
    if ordered_references[-1].restart_reference_id != lineage.restart_reference_id:
        return RestartSequenceDerivation(
            status=DerivationStatus.NOT_EVALUABLE,
            restart_reference_crossed=None,
            retest_seen=None,
            current_executable_price=None,
            reason_codes=("LATEST_RESTART_REFERENCE_ID_CONFLICT",),
        )

    reference_index = -1
    active_reference: RestartReferenceEvidence | None = None
    previous_d: Decimal | None = None
    phase = "SEEK_BREAK"
    break_ordinal: int | None = None
    return_ordinal: int | None = None
    reaccel_ordinal: int | None = None
    current_price: Decimal | None = None
    failed_reset_applied = False
    activation_crossed_now = False

    for event in ordered_events:
        reason = _event_health_reason(event, lineage)
        if reason is not None:
            return RestartSequenceDerivation(
                status=DerivationStatus.NOT_EVALUABLE,
                restart_reference_crossed=None,
                retest_seen=None,
                current_executable_price=current_price,
                break_ordinal=break_ordinal,
                return_ordinal=return_ordinal,
                reaccel_ordinal=reaccel_ordinal,
                reason_codes=(reason,),
            )
        while (
            reference_index + 1 < len(ordered_references)
            and ordered_references[reference_index + 1].confirmed_admission_ordinal
            <= event.admission_ordinal
        ):
            reference_index += 1
            active_reference = ordered_references[reference_index]
            previous_d = None
            phase = "SEEK_BREAK"
            break_ordinal = return_ordinal = reaccel_ordinal = None
        if active_reference is None:
            continue
        if event.admission_ordinal < active_reference.reset_admission_ordinal:
            continue
        if (
            attempt_failed_admission_ordinal is not None
            and not failed_reset_applied
            and event.admission_ordinal >= attempt_failed_admission_ordinal
        ):
            previous_d = None
            phase = "SEEK_BREAK"
            break_ordinal = return_ordinal = reaccel_ordinal = None
            failed_reset_applied = True
        try:
            bid, ask, _, _ = _bbo_values(event)
        except ValueError as exc:
            return RestartSequenceDerivation(
                status=DerivationStatus.NOT_EVALUABLE,
                restart_reference_crossed=None,
                retest_seen=None,
                current_executable_price=current_price,
                reason_codes=(str(exc),),
            )
        current_price = ask if side is PositionSide.LONG else bid
        side_sign = Decimal("1") if side is PositionSide.LONG else Decimal("-1")
        distance = side_sign * (current_price - active_reference.price)
        crossed = previous_d is not None and previous_d <= 0 and distance > 0
        activation_crossed_now = False
        if phase == "SEEK_BREAK" and crossed:
            phase = "SEEK_RETURN"
            break_ordinal = event.admission_ordinal
            activation_crossed_now = True
        elif phase == "SEEK_RETURN" and distance <= 0:
            phase = "SEEK_REACCEL"
            return_ordinal = event.admission_ordinal
        elif phase == "SEEK_REACCEL" and crossed:
            phase = "COMPLETE"
            reaccel_ordinal = event.admission_ordinal
            activation_crossed_now = True
        previous_d = distance

    if current_price is None:
        return RestartSequenceDerivation(
            status=DerivationStatus.NOT_EVALUABLE,
            restart_reference_crossed=None,
            retest_seen=None,
            current_executable_price=None,
            reason_codes=("NO_POST_REFERENCE_EXECUTABLE_BBO",),
        )
    return RestartSequenceDerivation(
        status=DerivationStatus.EVALUABLE,
        restart_reference_crossed=activation_crossed_now,
        retest_seen=phase == "COMPLETE",
        current_executable_price=current_price,
        break_ordinal=break_ordinal,
        return_ordinal=return_ordinal,
        reaccel_ordinal=reaccel_ordinal,
        reason_codes=("RESTART_SEQUENCE_CAUSALLY_DERIVED",),
    )


def _least_legal_price_at_or_above(value: Decimal, market: RegistryMarket) -> Decimal | None:
    rounded = market.tick_round(value)
    if rounded == value:
        return value
    candidate = rounded
    seen_quantums: set[Decimal] = set()
    while True:
        basis = max(value, candidate)
        decimal_quantum = Decimal(1).scaleb(-market.price_max_decimals)
        significant_quantum = Decimal(1).scaleb(
            basis.adjusted() - market.price_max_significant_figures + 1
        )
        quantum = max(decimal_quantum, significant_quantum)
        if quantum in seen_quantums:
            break
        seen_quantums.add(quantum)
        candidate = (value / quantum).to_integral_value(rounding=ROUND_CEILING) * quantum
        if candidate > 0 and market.tick_round(candidate) == candidate and candidate >= value:
            return candidate
    integer_candidate = value.to_integral_value(rounding=ROUND_CEILING)
    if integer_candidate > 0 and market.tick_round(integer_candidate) == integer_candidate:
        return integer_candidate
    return None


def _remaining_room_bps(*, side: PositionSide, entry: Decimal, target: Decimal) -> Decimal:
    side_sign = Decimal("1") if side is PositionSide.LONG else Decimal("-1")
    return side_sign * (target - entry) / entry * Decimal("10000")


def derive_economics_can_improve(
    *,
    lineage: CausalLineage,
    side: PositionSide,
    ideal_entry_low: Decimal | None,
    ideal_entry_high: Decimal | None,
    target_reference: Decimal | None,
    room_to_cost_k: Decimal,
    current_bbo: AdmittedEvent | None,
    market_expression: MarketExpression | None,
    registry_market: RegistryMarket | None,
    validation: ValidationReference | None,
) -> EconomicsDerivation:
    """Evaluate the total A_NOW existential without snapping or widening geometry."""
    required = (
        ideal_entry_low,
        ideal_entry_high,
        target_reference,
        current_bbo,
        market_expression,
        registry_market,
        validation,
    )
    if any(item is None for item in required):
        return EconomicsDerivation(
            status=DerivationStatus.NOT_EVALUABLE,
            economics_can_improve=None,
            a_now_empty=None,
            current_executable_price=None,
            current_remaining_room_bps=None,
            best_admissible_price=None,
            best_room_to_cost=None,
            reason_codes=("S3_REQUIRED_SOURCE_MISSING",),
        )
    assert ideal_entry_low is not None
    assert ideal_entry_high is not None
    assert target_reference is not None
    assert current_bbo is not None
    assert market_expression is not None
    assert registry_market is not None
    assert validation is not None
    reason: str | None
    if not validation.fully_materialized:
        reason = "VALIDATION_REFERENCE_NOT_FULLY_MATERIALIZED"
    elif (
        validation.validation_reference_id != lineage.validation_reference_id
        or validation.reference_hash != lineage.validation_reference_hash
    ):
        reason = "VALIDATION_REFERENCE_LINEAGE_CONFLICT"
    elif ideal_entry_low <= 0 or ideal_entry_high < ideal_entry_low or target_reference <= 0:
        reason = "S3_GEOMETRY_INVALID"
    elif (
        market_expression.market_id != lineage.market_id
        or market_expression.instrument_id != lineage.instrument_id
        or market_expression.instrument_metadata_version != lineage.instrument_metadata_version
        or market_expression.instrument_metadata_hash != lineage.instrument_metadata_hash
        or registry_market.identity.market_id != lineage.market_id
        or registry_market.metadata_hash != lineage.instrument_metadata_hash
    ):
        reason = "INSTRUMENT_PRICE_VALIDITY_LINEAGE_CONFLICT"
    else:
        reason = _event_health_reason(current_bbo, lineage)
    if reason is not None:
        return EconomicsDerivation(
            status=DerivationStatus.NOT_EVALUABLE,
            economics_can_improve=None,
            a_now_empty=None,
            current_executable_price=None,
            current_remaining_room_bps=None,
            best_admissible_price=None,
            best_room_to_cost=None,
            reason_codes=(reason,),
        )
    try:
        bid, ask, _, _ = _bbo_values(current_bbo)
    except ValueError as exc:
        return EconomicsDerivation(
            status=DerivationStatus.NOT_EVALUABLE,
            economics_can_improve=None,
            a_now_empty=None,
            current_executable_price=None,
            current_remaining_room_bps=None,
            best_admissible_price=None,
            best_room_to_cost=None,
            reason_codes=(str(exc),),
        )
    current = ask if side is PositionSide.LONG else bid
    if registry_market.tick_round(current) != current:
        return EconomicsDerivation(
            status=DerivationStatus.NOT_EVALUABLE,
            economics_can_improve=None,
            a_now_empty=None,
            current_executable_price=current,
            current_remaining_room_bps=None,
            best_admissible_price=None,
            best_room_to_cost=None,
            reason_codes=("CURRENT_EXECUTABLE_PRICE_NOT_VENUE_VALID",),
        )

    least = _least_legal_price_at_or_above(ideal_entry_low, registry_market)
    greatest = registry_market.tick_round(ideal_entry_high)
    if (
        least is None
        or least > ideal_entry_high
        or greatest < ideal_entry_low
        or greatest <= 0
    ):
        return EconomicsDerivation(
            status=DerivationStatus.EVALUABLE,
            economics_can_improve=False,
            a_now_empty=True,
            current_executable_price=current,
            current_remaining_room_bps=_remaining_room_bps(
                side=side,
                entry=current,
                target=target_reference,
            ),
            best_admissible_price=None,
            best_room_to_cost=None,
            reason_codes=("A_NOW_EMPTY",),
        )
    best = least if side is PositionSide.LONG else greatest
    assert validation.all_in_friction_bps is not None
    ratio = _remaining_room_bps(side=side, entry=best, target=target_reference) / Decimal(
        validation.all_in_friction_bps
    )
    can_improve = ratio >= room_to_cost_k
    return EconomicsDerivation(
        status=DerivationStatus.EVALUABLE,
        economics_can_improve=can_improve,
        a_now_empty=False,
        current_executable_price=current,
        current_remaining_room_bps=_remaining_room_bps(
            side=side,
            entry=current,
            target=target_reference,
        ),
        best_admissible_price=best,
        best_room_to_cost=ratio,
        reason_codes=(("A_NOW_CAN_MEET_HURDLE" if can_improve else "A_NOW_CANNOT_MEET_HURDLE"),),
    )


def derive_evaluation_admission(
    *,
    candidate_room_to_cost_k: Decimal,
    lineage: CausalLineage,
    formal_decision: StrategyDecision,
    lifecycle_records: Sequence[LifecycleRecord],
    bbo_events: Sequence[AdmittedEvent],
    restart_references: Sequence[RestartReferenceEvidence],
    market_expression: MarketExpression | None,
    registry_market: RegistryMarket | None,
    validation: ValidationReference | None,
    supplement: EvaluatorSupplementEvidence | None,
) -> EvaluationAdmission:
    """Admit only source-derived S1/S2/S3 values to the frozen evaluator."""
    formal = (
        formal_decision.decision is DecisionKind.FORMAL_SETUP_CONFIRMED
        and formal_decision.market_id == lineage.market_id
        and formal_decision.market_event_id == lineage.formal_setup_id
    )
    position_side = PositionSide.LONG if formal_decision.side is Side.LONG else PositionSide.SHORT
    thesis = derive_thesis_valid(
        formal_setup_confirmed=formal,
        lineage=lineage,
        records=lifecycle_records,
    )
    restart = derive_retest_seen(
        lineage=lineage,
        side=position_side,
        events=bbo_events,
        references=restart_references,
        attempt_failed_admission_ordinal=max(
            (
                record.last_admission_ordinal
                for record in lifecycle_records
                if record.kind is LifecycleKind.ATTEMPT
                and record.parent_id == lineage.thesis_id
                and "ATTEMPT_FAILURE" in record.reason_codes
                and record.evidence_state is EvidenceState.COMPLETE
            ),
            default=None,
        ),
    )
    target = (
        formal_decision.target_reference.price
        if formal_decision.target_reference is not None
        else None
    )
    economics = derive_economics_can_improve(
        lineage=lineage,
        side=position_side,
        ideal_entry_low=formal_decision.ideal_entry_low,
        ideal_entry_high=formal_decision.ideal_entry_high,
        target_reference=target,
        room_to_cost_k=candidate_room_to_cost_k,
        current_bbo=bbo_events[-1] if bbo_events else None,
        market_expression=market_expression,
        registry_market=registry_market,
        validation=validation,
    )
    reasons: list[str] = []
    for component in (thesis, restart, economics):
        if component.status is DerivationStatus.NOT_EVALUABLE:
            reasons.extend(component.reason_codes)
    if supplement is None:
        reasons.append("EVALUATOR_SUPPLEMENT_SOURCE_MISSING")
    elif supplement.causal_lineage_hash != lineage.lineage_hash:
        reasons.append("EVALUATOR_SUPPLEMENT_LINEAGE_CONFLICT")
    if (
        economics.current_remaining_room_bps is not None
        and economics.current_remaining_room_bps <= 0
    ):
        reasons.append("CURRENT_STRUCTURAL_ROOM_NOT_POSITIVE_FOR_FROZEN_EVALUATOR")
    if reasons:
        return EvaluationAdmission(
            status=DerivationStatus.NOT_EVALUABLE,
            inputs=None,
            thesis_valid=thesis,
            restart_sequence=restart,
            economics=economics,
            reason_codes=tuple(dict.fromkeys(reasons)),
        )
    assert thesis.value is not None
    assert restart.restart_reference_crossed is not None
    assert restart.retest_seen is not None
    assert economics.current_remaining_room_bps is not None
    assert economics.economics_can_improve is not None
    assert supplement is not None
    assert validation is not None
    assert validation.all_in_friction_bps is not None
    inputs = EvaluationInputs(
        formal_setup_confirmed=True,
        thesis_valid=thesis.value,
        bbo_state_valid=True,
        data_evaluable=True,
        restart_reference_crossed=restart.restart_reference_crossed,
        retest_seen=restart.retest_seen,
        microstructure_warmup_seconds=supplement.microstructure_warmup_seconds,
        side_adjusted_aggressor_imbalance_15s=(
            supplement.side_adjusted_aggressor_imbalance_15s
        ),
        flow_price_response_15s_bps=supplement.flow_price_response_15s_bps,
        remaining_structural_room_bps=economics.current_remaining_room_bps,
        all_in_friction_bps=validation.all_in_friction_bps,
        economics_can_improve=economics.economics_can_improve,
    )
    return EvaluationAdmission(
        status=DerivationStatus.EVALUABLE,
        inputs=inputs,
        thesis_valid=thesis,
        restart_sequence=restart,
        economics=economics,
        reason_codes=("SOURCE_BOUND_EVALUATOR_INPUTS_ADMITTED",),
    )


def admit_hypothetical_order_intent(
    *,
    strategy_decision_id: str,
    candidate_hash: str,
    side: PositionSide,
    lineage: CausalLineage,
    current_bbo: AdmittedEvent,
    technical_quantity: Decimal,
    size_decimals: int,
    activation_reference_hash: str,
    validation: ValidationReference | None,
) -> OrderIntentAdmission:
    """Build a canonical zero-write intent only from a valid causal L1 binding."""
    reason = _event_health_reason(current_bbo, lineage)
    if reason is not None:
        return OrderIntentAdmission(
            status=DerivationStatus.NOT_EVALUABLE,
            intent=None,
            reason_codes=(reason,),
        )
    if validation is None or not validation.fully_materialized:
        return OrderIntentAdmission(
            status=DerivationStatus.NOT_EVALUABLE,
            intent=None,
            reason_codes=("VALIDATION_REFERENCE_NOT_FULLY_MATERIALIZED",),
        )
    try:
        bid, ask, bid_size, ask_size = _bbo_values(current_bbo)
        executable = ask if side is PositionSide.LONG else bid
        displayed_opposite_size = ask_size if side is PositionSide.LONG else bid_size
        quantity = TechnicalOrderQuantity(
            quantity=technical_quantity,
            displayed_opposite_l1_size=displayed_opposite_size,
            size_decimals=size_decimals,
            instrument_metadata_version=lineage.instrument_metadata_version,
            instrument_metadata_hash=lineage.instrument_metadata_hash,
            bbo_admission_hash=current_bbo.admission_hash,
        )
        intent = HypotheticalOrderIntent.create(
            strategy_decision_id=strategy_decision_id,
            candidate_hash=candidate_hash,
            side=side,
            technical_quantity=quantity,
            executable_price=executable,
            activation_reference_hash=activation_reference_hash,
            validation=validation,
            lineage=lineage,
        )
    except (ValueError, ValidationError) as exc:
        return OrderIntentAdmission(
            status=DerivationStatus.NOT_EVALUABLE,
            intent=None,
            reason_codes=(f"EXECUTION_BINDING_NOT_EVALUABLE:{exc}",),
        )
    return OrderIntentAdmission(
        status=DerivationStatus.EVALUABLE,
        intent=intent,
        reason_codes=("CANONICAL_NOT_SUBMITTED_ORDER_INTENT_ADMITTED",),
    )
