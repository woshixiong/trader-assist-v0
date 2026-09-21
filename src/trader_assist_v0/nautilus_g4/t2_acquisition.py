# mypy: disable-error-code="import-not-found"
"""Bounded Task #5D Real-T2 acquisition composition.

This module owns no transport, Strategy economics, Validation economics, or
execution semantics. It only binds frozen identities to existing owners.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from trader_assist_v0.contracts.common import Sha256Hex, canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    ClosedBar,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
)
from trader_assist_v0.multi_asset_shadow.strategy_kernel.types import (
    DecisionKind,
    StrategyDecision,
)
from trader_assist_v0.nautilus_e4.contracts import (
    AdmittedEvent,
    DataKind,
    EvidenceState,
    MarketExpression,
)
from trader_assist_v0.nautilus_g4.catalog_bridge import EvaluatorSupplementEvidence
from trader_assist_v0.nautilus_pilot.contracts import StrategyInputEvent
from trader_assist_v0.nautilus_pilot.strategy_package import (
    PilotStrategyEvaluator,
    StrategyPackageManifest,
)
from trader_assist_v0.vnext_g4.contracts import (
    CausalLineage,
    PositionSide,
    RestartReferenceEvidence,
    RestartReferenceKind,
)

REAL_T2_TASK_ID = "PILOT_TASK5D_PHASE0E_R_REAL_T2_INTEGRATION_R1"
REAL_T2_ACQUISITION_SECONDS = 14_400
REAL_T2_ACQUISITION_NS = REAL_T2_ACQUISITION_SECONDS * 1_000_000_000
FIVE_MINUTES_MS = 300_000
ONE_MINUTE_NS = 60_000_000_000
PHASE0C_STRATEGY_RELEASE_SHA = "830f0e6ab3bfb711cf29b83f41a7c86ed7fae0c2"
PHASE0C_STRATEGY_PACKAGE_HASH = "e9fc9b43de439bfd62748007974c07540a83c7a5f7cbc0017e993b42eea417f0"
PHASE0C_MARKET_SET_HASH = "9044fb1fa5f25d29cea9c42ee5e3f5aa73448db08d26a988f5d0e8df10dd24ca"
PHASE0C_PROSPECTIVE_CANDIDATE_HASH = "5176739d9ac0b2384675dd077781be187d25458bb3ea00bdc25b5366419ef1e2"


class RealT2IntegrationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class FrozenMarketIdentity:
    ordinal: int
    provider_coin: str
    instrument_id: str
    market_id: str


_FIXED_COINS = (
    "BTC", "ETH", "ZEC", "HYPE", "NEAR", "SOL", "ENA", "XRP", "AVAX", "UNI",
    "SUI", "LIT", "PUMP", "VVV", "ARB", "CASHCAT", "TAO", "XMR", "kPEPE", "ONDO",
)
FROZEN_MARKETS = tuple(
    FrozenMarketIdentity(
        ordinal=i,
        provider_coin=coin,
        instrument_id=f"{coin}-USD-PERP.HYPERLIQUID",
        market_id=MarketIdentity.canonical_market_id(dex="MAIN", coin=coin),
    )
    for i, coin in enumerate(_FIXED_COINS, 1)
)
FROZEN_BY_MARKET = {item.market_id: item for item in FROZEN_MARKETS}


def expected_external_bar_type(instrument_id: str, minutes: int) -> str:
    if minutes not in {1, 5}:
        raise RealT2IntegrationError("only provider-native 1m/5m EXTERNAL bars are permitted")
    return f"{instrument_id}-{minutes}-MINUTE-LAST-EXTERNAL"


def _decimal(payload: Mapping[str, object], key: str) -> Decimal:
    try:
        value = Decimal(str(payload[key]))
    except (KeyError, InvalidOperation, ValueError) as exc:
        raise RealT2IntegrationError(f"{key} is not exact decimal evidence") from exc
    if not value.is_finite():
        raise RealT2IntegrationError(f"{key} is not finite")
    return value


def validate_external_bar_admission(event: AdmittedEvent, *, minutes: int) -> None:
    source = event.source
    duration_ns = minutes * ONE_MINUTE_NS
    if source.data_kind is not DataKind.BAR:
        raise RealT2IntegrationError("Strategy projection requires BAR evidence")
    if source.provider_id != "NAUTILUS_HYPERLIQUID":
        raise RealT2IntegrationError("wrong provider")
    if source.event_context != expected_external_bar_type(source.instrument_id, minutes):
        raise RealT2IntegrationError("bar is not exact LAST EXTERNAL route")
    if source.payload.get("finalized") is not True:
        raise RealT2IntegrationError("bar is not finalized")
    if event.out_of_order or event.continuity_state is not EvidenceState.COMPLETE:
        raise RealT2IntegrationError("out-of-order/gapped bar is not admissible")
    if source.ts_event % duration_ns:
        raise RealT2IntegrationError("bar opening timestamp is not aligned")
    close_ns = source.ts_event + duration_ns
    if source.ts_init < close_ns or event.admission_ts < source.ts_init:
        raise RealT2IntegrationError("early/lookahead bar timing is prohibited")
    frozen = FROZEN_BY_MARKET.get(source.market_id)
    if frozen is None or source.instrument_id != frozen.instrument_id:
        raise RealT2IntegrationError("bar lies outside frozen 20-market identity")
    for key in ("open", "high", "low", "close", "volume"):
        _decimal(source.payload, key)


def admitted_external_5m_to_strategy_input(
    event: AdmittedEvent, *, strategy_package_hash: str
) -> StrategyInputEvent:
    validate_external_bar_admission(event, minutes=5)
    source = event.source
    open_ms = source.ts_event // 1_000_000
    bar = ClosedBar.create(
        market_id=source.market_id,
        interval="5m",
        open_time_ms=open_ms,
        close_time_ms=open_ms + FIVE_MINUTES_MS,
        open=_decimal(source.payload, "open"),
        high=_decimal(source.payload, "high"),
        low=_decimal(source.payload, "low"),
        close=_decimal(source.payload, "close"),
        volume=_decimal(source.payload, "volume"),
        source_id=f"e4-admission:{event.admission_hash}",
        provenance_hash=event.admission_hash,
        received_at=datetime.fromtimestamp(event.admission_ts / 1_000_000_000, UTC),
    )
    return StrategyInputEvent.create(
        strategy_package_hash=strategy_package_hash,
        closed_bar=bar,
    )


class StructuralSourceEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "TASK5D_STRUCTURAL_SOURCE_V1"
    strategy_package_hash: Sha256Hex
    market_id: Sha256Hex
    exact_market_set_ordinal: int = Field(ge=1, le=20)
    formal_setup_admission_ordinal: int = Field(ge=1)
    formal_setup_admission_ts: int = Field(ge=1)
    formal_setup_id: str = Field(min_length=1)
    triggering_admission_hash: Sha256Hex
    decision: dict[str, object]
    decision_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_identity(self) -> "StructuralSourceEvidence":
        frozen = FROZEN_MARKETS[self.exact_market_set_ordinal - 1]
        if self.market_id != frozen.market_id:
            raise ValueError("structural ordinal conflicts with frozen market")
        if sha256_hex(canonical_json_bytes(self.decision)) != self.decision_hash:
            raise ValueError("decision hash mismatch")
        parsed = TypeAdapter(StrategyDecision).validate_python(self.decision)
        if (
            parsed.decision is not DecisionKind.FORMAL_SETUP_CONFIRMED
            or parsed.market_id != self.market_id
            or parsed.market_event_id != self.formal_setup_id
        ):
            raise ValueError("structural decision conflicts with Formal Setup identity")
        return self

    @classmethod
    def create(
        cls, *, strategy_package_hash: str, admission: AdmittedEvent, decision: StrategyDecision
    ) -> "StructuralSourceEvidence":
        frozen = FROZEN_BY_MARKET.get(decision.market_id)
        if frozen is None or decision.decision is not DecisionKind.FORMAL_SETUP_CONFIRMED:
            raise RealT2IntegrationError("only frozen Formal Setup may materialize structural source")
        payload = cast(
            dict[str, object],
            json.loads(TypeAdapter(StrategyDecision).dump_json(decision)),
        )
        return cls(
            strategy_package_hash=strategy_package_hash,
            market_id=decision.market_id,
            exact_market_set_ordinal=frozen.ordinal,
            formal_setup_admission_ordinal=admission.admission_ordinal,
            formal_setup_admission_ts=admission.admission_ts,
            formal_setup_id=decision.market_event_id,
            triggering_admission_hash=admission.admission_hash,
            decision=payload,
            decision_hash=sha256_hex(canonical_json_bytes(payload)),
        )

    def strategy_decision(self) -> StrategyDecision:
        return cast(StrategyDecision, TypeAdapter(StrategyDecision).validate_python(self.decision))


@dataclass(frozen=True, slots=True)
class FormalSetupObservation:
    structural: StructuralSourceEvidence
    package_id: str
    opportunity_id: str
    thesis_id: str
    continuity_epoch: str
    admission_epoch: str

    @property
    def focal_key(self) -> tuple[int, int, int, str]:
        s = self.structural
        return (
            s.formal_setup_admission_ts,
            s.exact_market_set_ordinal,
            s.formal_setup_admission_ordinal,
            s.formal_setup_id,
        )


def select_focal_formal_setup(
    observations: Sequence[FormalSetupObservation],
) -> FormalSetupObservation | None:
    if not observations:
        return None
    ids = [x.structural.formal_setup_id for x in observations]
    if len(ids) != len(set(ids)):
        raise RealT2IntegrationError("duplicate/conflicting Formal Setup identity")
    return min(observations, key=lambda x: x.focal_key)


class StructuralPackageOpener(Protocol):
    def __call__(
        self, *, package_id: str, opportunity_id: str, thesis_id: str,
        market_id: str, expression_id: str, state_ts: int
    ) -> EvidenceState: ...


def _strategy_package() -> StrategyPackageManifest:
    manifest = StrategyPackageManifest.create(trade_os_release_sha=PHASE0C_STRATEGY_RELEASE_SHA)
    if manifest.manifest_hash != PHASE0C_STRATEGY_PACKAGE_HASH:
        raise RealT2IntegrationError("current Strategy package differs from frozen Phase 0C")
    return manifest


def _provider_tick(provider_instrument: object) -> Decimal:
    try:
        tick = Decimal(str(getattr(provider_instrument, "price_increment")))
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise RealT2IntegrationError("provider-native minimum tick is unavailable") from exc
    if not tick.is_finite() or tick <= 0:
        raise RealT2IntegrationError("provider-native minimum tick is invalid")
    return tick


class RealT2StrategyCoordinator:
    def __init__(
        self, *, registry_markets: Mapping[str, RegistryMarket],
        open_structural_package: StructuralPackageOpener,
        clock_ns: Callable[[], int] = time.time_ns,
    ) -> None:
        if set(registry_markets) != set(FROZEN_BY_MARKET):
            raise RealT2IntegrationError("all exact frozen markets are required")
        self.registry_markets = dict(registry_markets)
        self.open_structural_package = open_structural_package
        self.clock_ns = clock_ns
        self.package_manifest = _strategy_package()
        self.evaluators: dict[str, PilotStrategyEvaluator] = {}
        self.minimum_ticks: dict[str, Decimal] = {}
        self.observations: list[FormalSetupObservation] = []
        self.provider_instruments: dict[str, dict[str, object]] = {}
        self.admissions: list[AdmittedEvent] = []

    def observe_admitted_event(
        self, event: AdmittedEvent, provider_instrument: object | None = None
    ) -> None:
        self.admissions.append(event)
        if provider_instrument is not None:
            to_dict = getattr(provider_instrument, "to_dict", None)
            if not callable(to_dict):
                raise RealT2IntegrationError("provider instrument lacks normalized serializer")
            normalized = to_dict()
            if not isinstance(normalized, dict):
                raise RealT2IntegrationError("provider instrument normalization is invalid")
            if str(getattr(provider_instrument, "id", "")) != event.source.instrument_id:
                raise RealT2IntegrationError("provider instrument conflicts with admitted source")
            prior = self.provider_instruments.setdefault(event.source.market_id, normalized)
            if canonical_json_bytes(prior) != canonical_json_bytes(normalized):
                raise RealT2IntegrationError("provider instrument changed within attempt")
        if event.source.data_kind is not DataKind.BAR:
            return
        if event.source.event_context.endswith("-1-MINUTE-LAST-EXTERNAL"):
            validate_external_bar_admission(event, minutes=1)
            return
        strategy_input = admitted_external_5m_to_strategy_input(
            event, strategy_package_hash=self.package_manifest.manifest_hash
        )
        if provider_instrument is None:
            raise RealT2IntegrationError("5m Strategy input lacks provider-native instrument")
        tick = _provider_tick(provider_instrument)
        evaluator = self.evaluators.get(event.source.market_id)
        if evaluator is None:
            evaluator = PilotStrategyEvaluator(
                manifest=self.package_manifest, market_id=event.source.market_id, minimum_tick=tick
            )
            self.evaluators[event.source.market_id] = evaluator
            self.minimum_ticks[event.source.market_id] = tick
        elif self.minimum_ticks[event.source.market_id] != tick:
            raise RealT2IntegrationError("provider-native minimum tick changed within attempt")
        envelope = evaluator.evaluate(strategy_input)
        if envelope is None:
            return
        for decision in envelope.kernel_result.decisions:
            if decision.decision is DecisionKind.FORMAL_SETUP_CONFIRMED:
                self._open_formal_setup(event, decision)

    def _open_formal_setup(self, admission: AdmittedEvent, decision: StrategyDecision) -> None:
        structural = StructuralSourceEvidence.create(
            strategy_package_hash=self.package_manifest.manifest_hash,
            admission=admission,
            decision=decision,
        )
        if any(x.structural.formal_setup_id == structural.formal_setup_id for x in self.observations):
            raise RealT2IntegrationError("same Formal Setup emitted more than once")
        seed = sha256_hex(canonical_json_bytes({
            "admission": admission.admission_hash,
            "formal_setup": structural.formal_setup_id,
            "decision": structural.decision_hash,
        }))
        state_ts = self.clock_ns()
        if state_ts <= admission.admission_ts:
            raise RealT2IntegrationError("structural lifecycle time must follow admission")
        package_id, opportunity_id, thesis_id = (
            f"task5d-{seed[:32]}", f"opportunity-{seed[:32]}", f"thesis-{seed[:32]}"
        )
        self.open_structural_package(
            package_id=package_id,
            opportunity_id=opportunity_id,
            thesis_id=thesis_id,
            market_id=admission.source.market_id,
            expression_id=admission.source.expression_id,
            state_ts=state_ts,
        )
        self.observations.append(FormalSetupObservation(
            structural=structural,
            package_id=package_id,
            opportunity_id=opportunity_id,
            thesis_id=thesis_id,
            continuity_epoch=admission.continuity_epoch,
            admission_epoch=admission.admission_epoch,
        ))

    @property
    def focal(self) -> FormalSetupObservation | None:
        return select_focal_formal_setup(self.observations)


@dataclass(frozen=True, slots=True)
class FixedMarketMaterialization:
    identity: FrozenMarketIdentity
    expression: MarketExpression
    registry_market: RegistryMarket
    provider_entry: dict[str, object]
    provider_context: dict[str, object]
    raw_response_sha256: str


def raw_response_sha256(raw: bytes) -> str:
    return sha256_hex(raw)


def materialize_fixed_markets_from_public_metadata(
    *, raw_response: bytes, parsed_response: object, observed_at_ns: int
) -> tuple[FixedMarketMaterialization, ...]:
    if observed_at_ns <= 0 or json.loads(raw_response) != parsed_response:
        raise RealT2IntegrationError("parsed metadata must bind exact raw response bytes")
    if not isinstance(parsed_response, list) or len(parsed_response) != 2:
        raise RealT2IntegrationError("metaAndAssetCtxs response shape is invalid")
    meta, contexts = parsed_response
    if not isinstance(meta, dict) or not isinstance(contexts, list):
        raise RealT2IntegrationError("metaAndAssetCtxs response shape is invalid")
    universe = meta.get("universe")
    if not isinstance(universe, list) or len(universe) != len(contexts):
        raise RealT2IntegrationError("provider universe/context binding is invalid")
    positions: dict[str, tuple[int, dict[str, object], dict[str, object]]] = {}
    for i, (asset, ctx) in enumerate(zip(universe, contexts, strict=True)):
        if not isinstance(asset, dict) or not isinstance(ctx, dict):
            raise RealT2IntegrationError("provider metadata entry is invalid")
        name = asset.get("name")
        if isinstance(name, str):
            if name in positions:
                raise RealT2IntegrationError("duplicate provider market identity")
            positions[name] = (i, asset, ctx)
    observed = datetime.fromtimestamp(observed_at_ns / 1_000_000_000, UTC)
    raw_hash = raw_response_sha256(raw_response)
    result: list[FixedMarketMaterialization] = []
    for frozen in FROZEN_MARKETS:
        if frozen.provider_coin not in positions:
            raise RealT2IntegrationError("frozen market unavailable; substitution prohibited")
        index, asset, ctx = positions[frozen.provider_coin]
        if asset.get("isDelisted") is True:
            raise RealT2IntegrationError("frozen market is delisted")
        sz = asset.get("szDecimals")
        if isinstance(sz, bool) or not isinstance(sz, int) or not 0 <= sz <= 6:
            raise RealT2IntegrationError("provider szDecimals is invalid")
        try:
            leverage = Decimal(str(asset["maxLeverage"]))
        except (KeyError, InvalidOperation, ValueError) as exc:
            raise RealT2IntegrationError("provider maxLeverage is invalid") from exc
        if not leverage.is_finite() or leverage <= 0:
            raise RealT2IntegrationError("provider maxLeverage is invalid")
        metadata_hash = sha256_hex(canonical_json_bytes({
            "raw_response_sha256": raw_hash,
            "source_universe_index": index,
            "asset": asset,
            "context": ctx,
            "instrument_id": frozen.instrument_id,
            "market_id": frozen.market_id,
        }))
        expression = MarketExpression(
            market_id=frozen.market_id,
            dex="MAIN",
            provider_coin=frozen.provider_coin,
            instrument_id=frozen.instrument_id,
            expression_id=f"task5d-{frozen.ordinal:02d}-{frozen.market_id[:16]}",
            listing_state="ACTIVE_STANDARD_MAIN_PERPETUAL",
            instrument_metadata_version="TASK5D_HYPERLIQUID_PUBLIC_META_CTX_RC5_V1",
            instrument_metadata_hash=metadata_hash,
        )
        registry = RegistryMarket(
            display=frozen.provider_coin,
            aliases=(),
            tier=RegistryTier.P0,
            identity=MarketIdentity.create(dex="MAIN", coin=frozen.provider_coin),
            asset_class=AssetClass.CRYPTO,
            size_decimals=sz,
            price_max_significant_figures=5,
            price_max_decimals=6 - sz,
            max_leverage=leverage,
            is_hip3=False,
            market_status="ACTIVE",
            timeframe_profile="FAST_5M",
            lifecycle=MarketLifecycle.ACTIVE,
            growth_mode=None,
            metadata_observed_at=observed,
            metadata_hash=metadata_hash,
        )
        result.append(FixedMarketMaterialization(
            identity=frozen,
            expression=expression,
            registry_market=registry,
            provider_entry=dict(asset),
            provider_context=dict(ctx),
            raw_response_sha256=raw_hash,
        ))
    if tuple(x.identity for x in result) != FROZEN_MARKETS:
        raise RealT2IntegrationError("frozen market order changed")
    return tuple(result)
