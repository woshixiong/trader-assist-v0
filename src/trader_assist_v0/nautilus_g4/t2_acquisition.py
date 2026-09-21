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
from typing import Protocol, cast, runtime_checkable

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
from trader_assist_v0.nautilus_g4.t2_shadow import (
    RoleBoundSourceArtifact,
    SourceReference,
    T2SourceRole,
    T2SourceRootSnapshot,
)
from trader_assist_v0.nautilus_pilot.contracts import StrategyInputEvent
from trader_assist_v0.nautilus_pilot.strategy_package import (
    PilotStrategyEvaluator,
    StrategyPackageManifest,
)
from trader_assist_v0.vnext_g4.contracts import (
    CandidateConfig,
    CandidateManifest,
    CausalLineage,
    EvidenceArtifactHash,
    ExecutionModelConfig,
    G4RunManifest,
    LatencyEvidenceRole,
    PositionSide,
    ProspectiveEconomicCandidateIdentity,
    RestartReferenceEvidence,
    RestartReferenceKind,
    ValidationReference,
)
from trader_assist_v0.vnext_g4.evaluator import exit_triggered, winner_confirmed

REAL_T2_TASK_ID = "PILOT_TASK5D_PHASE0E_R_REAL_T2_INTEGRATION_R1"
REAL_T2_ACQUISITION_SECONDS = 14_400
REAL_T2_ACQUISITION_NS = REAL_T2_ACQUISITION_SECONDS * 1_000_000_000
FIVE_MINUTES_MS = 300_000
ONE_MINUTE_NS = 60_000_000_000
PHASE0C_STRATEGY_RELEASE_SHA = "830f0e6ab3bfb711cf29b83f41a7c86ed7fae0c2"
PHASE0C_STRATEGY_PACKAGE_HASH = "e9fc9b43de439bfd62748007974c07540a83c7a5f7cbc0017e993b42eea417f0"
PHASE0C_MARKET_SET_HASH = "9044fb1fa5f25d29cea9c42ee5e3f5aa73448db08d26a988f5d0e8df10dd24ca"
PHASE0C_PROSPECTIVE_CANDIDATE_HASH = (
    "5176739d9ac0b2384675dd077781be187d25458bb3ea00bdc25b5366419ef1e2"
)


VALIDATION_SOURCE_PROFILE_ID = (
    "TASK5D_REAL_T2_NONPROD_TECH_VALIDATION_V1_2026_09_21"
)
VALIDATION_REFERENCE_ID = "TASK5D_REAL_T2_VALIDATION_REF_V1"
FEE_PROFILE_ID = "TASK5D_HL_MAIN_PUBLIC_BASE_TAKER_CONTROL_V1_2026_09_21"
FEE_PROFILE_SOURCE_HASH = (
    "401fd7af740b713c488600840a51ff3f7fb86a59e1e1ef2b76929c23dc8d5d42"
)
FRICTION_POLICY_SOURCE_HASH = (
    "710c757098f45a3104e344f5b44340dd03fd8f335fd12e91d7dc0cc42bb102f8"
)
ALL_IN_FRICTION_STATE_ID = "TASK5D_SINGLE_ATTEMPT_ROUNDTRIP_9BPS_CONTROL_V1"
EXECUTION_MODEL_ID = "VNEXT_G4_EXPLICIT_NAUTILUS_RC5_V1"
EXECUTION_MODEL_SOURCE_HASH = (
    "0d7fa719eca868531823bab2c30adc810aa48b05e9b196a75f1ec647ca7bd606"
)
TECHNICAL_QUANTITY_RULE_ID = (
    "TASK5D_ONE_PROVIDER_SIZE_INCREMENT_CAUSAL_L1_V1"
)
LATENCY_CONTROL_ID = "TASK5D_ZERO_MS_CONTROL_ONLY_V1"
LATENCY_CONTROL_SOURCE_HASH = (
    "f85a647cb68cb4e29897f3760bef2e3b914cec8acc69a7fba520b48a911f321b"
)

FEE_CONTROL_RECORD: dict[str, object] = {
    "account_private_source_used": False,
    "actual_user_fee_rate_claim": False,
    "hip3_rule": (
        "NOT_APPLICABLE_FOR_FROZEN_MAIN_NON_HIP3; "
        "OTHERWISE_NOT_EVALUABLE_WITHOUT_EXACT_PUBLIC_MODIFIERS"
    ),
    "liquidity_role": "TAKER",
    "market_scope": "FIRST_PERP_DEX_MAIN_NON_HIP3_ONLY",
    "one_way_taker_bps": "4.5",
    "one_way_taker_rate_decimal": "0.00045",
    "production_account_fee_authority": False,
    "public_reference_tier": "BASE_RATE_TIER_0",
    "schema_version": "TASK5D_FEE_SOURCE_CONTROL_V1",
    "source_observed_utc_date": "2026-09-21",
    "source_owner": "Hyperliquid",
    "source_url": "https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees",
}
FRICTION_POLICY_RECORD: dict[str, object] = {
    "all_in_friction_bps": "9.0",
    "claim_scope": "TECHNICAL_CONTROL_ONLY_NOT_PRODUCTION_REALISM",
    "entry_fee_bps": "4.5",
    "exit_fee_bps": "4.5",
    "fee_profile_source_hash": FEE_PROFILE_SOURCE_HASH,
    "funding_outcome_rule": (
        "REQUIRE_PUBLIC_FUNDING_HISTORY; ANY_EVENT_IN_HOLD_INTERVAL=>"
        "NOT_EVALUABLE_V1; NO_EVENT=>NOT_APPLICABLE"
    ),
    "funding_predecision": "NOT_APPLICABLE_TO_ZERO_HOLD_TECHNICAL_REFERENCE_ONLY",
    "impact_extra_model_bps": "0",
    "impact_zero_condition": (
        "QTY_ONE_VALID_INCREMENT_AND_QTY_LE_CAUSAL_OPPOSITE_L1"
    ),
    "implementation_shortfall": (
        "OUTCOME_ONLY_NOT_INCLUDED_IN_PREDECISION_ALL_IN"
    ),
    "missing_source_rule": "NOT_EVALUABLE",
    "schema_version": "TASK5D_ALL_IN_FRICTION_CONTROL_V1",
    "scope": "PRE_DECISION_TECHNICAL_CONTROL_PER_ATTEMPT",
    "slippage_extra_model_bps": "0",
    "slippage_zero_scope": "CONTROL_ONLY",
    "spread_double_count": "PROHIBITED",
    "spread_separate_debit": "NOT_APPLICABLE_EXECUTABLE_BBO_EMBEDS_CROSSING",
    "state_id": ALL_IN_FRICTION_STATE_ID,
}
EXECUTION_CONTROL_RECORD: dict[str, object] = {
    "book_type": "L1_MBP",
    "claim_scope": "TECHNICAL_CONTROL_ONLY",
    "execution_model_limited": True,
    "fill_limit_at_price": False,
    "fill_stop_at_price": False,
    "l1_size_feasibility_required": True,
    "liquidity_consumption": True,
    "nautilus_release_commit_sha": "1b0a49d2792a9432a3aca3fcb617ce7a630d905e",
    "nautilus_release_tag": "v2.0.0rc5",
    "nautilus_tag_object_sha": "34de0d6f886a9fe8359f9d6590f43f53c86b1d32",
    "order_primitive": "MARKETABLE",
    "passive_touch_equals_fill": False,
    "prob_fill_on_limit": "0",
    "prob_slippage": "0",
    "project_execution_model_id": EXECUTION_MODEL_ID,
    "queue_position": False,
    "random_seed": None,
    "schema_version": "TASK5D_EXECUTION_CONTROL_SOURCE_V1",
    "trade_execution": True,
    "trigger_price_equals_fill": False,
}
LATENCY_CONTROL_RECORD: dict[str, object] = {
    "latency_control_id": LATENCY_CONTROL_ID,
    "latency_evidence_role": "CONTROL_ONLY",
    "latency_ms": "0",
    "nonzero_latency_calibration_claim": False,
    "production_realism_claim": False,
    "schema_version": "TASK5D_LATENCY_CONTROL_SOURCE_V1",
}


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
    def validate_identity(self) -> StructuralSourceEvidence:
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
    ) -> StructuralSourceEvidence:
        frozen = FROZEN_BY_MARKET.get(decision.market_id)
        if frozen is None or decision.decision is not DecisionKind.FORMAL_SETUP_CONFIRMED:
            raise RealT2IntegrationError(
                "only frozen Formal Setup may materialize structural source"
            )
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
        return TypeAdapter(StrategyDecision).validate_python(self.decision)


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
        market_id: str, expression_id: str, created_ts: int, active_valid_ts: int
    ) -> EvidenceState: ...


def _strategy_package() -> StrategyPackageManifest:
    manifest = StrategyPackageManifest.create(trade_os_release_sha=PHASE0C_STRATEGY_RELEASE_SHA)
    if manifest.manifest_hash != PHASE0C_STRATEGY_PACKAGE_HASH:
        raise RealT2IntegrationError("current Strategy package differs from frozen Phase 0C")
    return manifest


@runtime_checkable
class ProviderInstrumentView(Protocol):
    id: object
    price_increment: object
    size_precision: int
    size_increment: object

    def to_dict(self) -> dict[str, object]: ...


def _provider_instrument_view(provider_instrument: object) -> ProviderInstrumentView:
    if not isinstance(provider_instrument, ProviderInstrumentView):
        raise RealT2IntegrationError(
            "provider instrument lacks required normalized metadata surface"
        )
    return provider_instrument


def _provider_tick(provider_instrument: ProviderInstrumentView) -> Decimal:
    try:
        tick = Decimal(str(provider_instrument.price_increment))
    except (InvalidOperation, ValueError) as exc:
        raise RealT2IntegrationError(
            "provider-native minimum tick is unavailable"
        ) from exc
    if not tick.is_finite() or tick <= 0:
        raise RealT2IntegrationError("provider-native minimum tick is invalid")
    return tick


class RealT2StrategyCoordinator:
    def __init__(
        self, *, registry_markets: Mapping[str, RegistryMarket],
        open_structural_package: StructuralPackageOpener,
        clock_start_ns: int,
        cutoff_ns: int,
        clock_ns: Callable[[], int] = time.time_ns,
    ) -> None:
        if set(registry_markets) != set(FROZEN_BY_MARKET):
            raise RealT2IntegrationError("all exact frozen markets are required")
        self.registry_markets = dict(registry_markets)
        if cutoff_ns - clock_start_ns != REAL_T2_ACQUISITION_NS:
            raise RealT2IntegrationError("Real-T2 cutoff must remain exactly 14400 seconds")
        self.open_structural_package = open_structural_package
        self.clock_start_ns = clock_start_ns
        self.cutoff_ns = cutoff_ns
        self.clock_ns = clock_ns
        self.package_manifest = _strategy_package()
        self.evaluators: dict[str, PilotStrategyEvaluator] = {}
        self.minimum_ticks: dict[str, Decimal] = {}
        self.observations: list[FormalSetupObservation] = []
        self.provider_instruments: dict[str, dict[str, object]] = {}
        self.admissions: list[AdmittedEvent] = []
        self.last_5m_ts_event: dict[str, int] = {}
        self.first_source_bound_bbo: dict[str, CausalBboBinding] = {}

    def observe_admitted_event(
        self, event: AdmittedEvent, provider_instrument: object | None = None
    ) -> None:
        if event.admission_ts < self.clock_start_ns or event.admission_ts >= self.cutoff_ns:
            return
        self.admissions.append(event)
        if provider_instrument is not None:
            provider_view = _provider_instrument_view(provider_instrument)
            normalized = provider_view.to_dict()
            if str(provider_view.id) != event.source.instrument_id:
                raise RealT2IntegrationError(
                    "provider instrument conflicts with admitted source"
                )
            prior = self.provider_instruments.setdefault(
                event.source.market_id, normalized
            )
            if canonical_json_bytes(prior) != canonical_json_bytes(normalized):
                raise RealT2IntegrationError("provider instrument changed within attempt")
        if event.source.data_kind is DataKind.BBO:
            # This runs synchronously at admission.  A later BBO cannot replace a
            # bound evaluation BBO, even if the global focal is selected at cutoff.
            for observation in self.observations:
                setup_id = observation.structural.formal_setup_id
                if setup_id in self.first_source_bound_bbo:
                    continue
                binding = select_focal_causal_bbo(
                    admissions=tuple(self.admissions),
                    focal=observation,
                    side=position_side_for_focal(observation),
                    evaluation_admission_hash=event.admission_hash,
                )
                if binding is not None:
                    self.first_source_bound_bbo[setup_id] = binding
        if event.source.data_kind is not DataKind.BAR:
            return
        if event.source.event_context.endswith("-1-MINUTE-LAST-EXTERNAL"):
            validate_external_bar_admission(event, minutes=1)
            return
        strategy_input = admitted_external_5m_to_strategy_input(
            event, strategy_package_hash=self.package_manifest.manifest_hash
        )
        previous = self.last_5m_ts_event.get(event.source.market_id)
        if previous is not None and event.source.ts_event != previous + 5 * ONE_MINUTE_NS:
            raise RealT2IntegrationError(
                "missing/conflicting 5m sequence cannot be synthetically repaired"
            )
        self.last_5m_ts_event[event.source.market_id] = event.source.ts_event
        if provider_instrument is None:
            raise RealT2IntegrationError("5m Strategy input lacks provider-native instrument")
        tick = _provider_tick(_provider_instrument_view(provider_instrument))
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
        if any(
            x.structural.formal_setup_id == structural.formal_setup_id
            for x in self.observations
        ):
            raise RealT2IntegrationError("same Formal Setup emitted more than once")
        seed = sha256_hex(canonical_json_bytes({
            "admission": admission.admission_hash,
            "formal_setup": structural.formal_setup_id,
            "decision": structural.decision_hash,
        }))
        created_ts = self.clock_ns()
        active_valid_ts = self.clock_ns()
        if created_ts <= admission.admission_ts or active_valid_ts <= created_ts:
            raise RealT2IntegrationError(
                "structural lifecycle observed times must strictly follow admission"
            )
        package_id, opportunity_id, thesis_id = (
            f"task5d-{seed[:32]}", f"opportunity-{seed[:32]}", f"thesis-{seed[:32]}"
        )
        self.open_structural_package(
            package_id=package_id,
            opportunity_id=opportunity_id,
            thesis_id=thesis_id,
            market_id=admission.source.market_id,
            expression_id=admission.source.expression_id,
            created_ts=created_ts,
            active_valid_ts=active_valid_ts,
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

    def source_bound_bbo_for(
        self, focal: FormalSetupObservation
    ) -> CausalBboBinding | None:
        """Return the immutable causal BBO frozen at admission time."""
        return self.first_source_bound_bbo.get(focal.structural.formal_setup_id)


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


@dataclass(frozen=True, slots=True)
class RestartPivotSource:
    restart_reference_id: str
    side: PositionSide
    kind: RestartReferenceKind
    price: Decimal
    reset_admission_ordinal: int
    confirmed_admission_ordinal: int
    confirmed_admission_ts: int
    source_bytes: bytes


def derive_restart_pivot_source(
    *, admissions: Sequence[AdmittedEvent], focal: FormalSetupObservation, side: PositionSide
) -> RestartPivotSource | None:
    eligible = [
        e for e in admissions
        if e.source.market_id == focal.structural.market_id
        and e.source.data_kind is DataKind.BAR
        and e.admission_ordinal > focal.structural.formal_setup_admission_ordinal
        and e.source.event_context.endswith("-1-MINUTE-LAST-EXTERNAL")
    ]
    for event in eligible:
        validate_external_bar_admission(event, minutes=1)
        if (
            event.continuity_epoch != focal.continuity_epoch
            or event.admission_epoch != focal.admission_epoch
        ):
            return None
    eligible.sort(key=lambda e: e.admission_ordinal)
    if len(eligible) < 3:
        return None
    candidates: list[
        tuple[
            AdmittedEvent,
            AdmittedEvent,
            AdmittedEvent,
            Decimal,
            RestartReferenceKind,
        ]
    ] = []
    for left, pivot, right in zip(eligible, eligible[1:], eligible[2:], strict=False):
        if not (
            left.source.ts_event + ONE_MINUTE_NS == pivot.source.ts_event
            and pivot.source.ts_event + ONE_MINUTE_NS == right.source.ts_event
        ):
            return None
        if side is PositionSide.LONG:
            value = _decimal(pivot.source.payload, "high")
            if value > _decimal(left.source.payload, "high") and value >= _decimal(
                right.source.payload, "high"
            ):
                candidates.append((left, pivot, right, value, RestartReferenceKind.PIVOT_HIGH))
        else:
            value = _decimal(pivot.source.payload, "low")
            if value < _decimal(left.source.payload, "low") and value <= _decimal(
                right.source.payload, "low"
            ):
                candidates.append((left, pivot, right, value, RestartReferenceKind.PIVOT_LOW))
    if not candidates:
        return None
    left, pivot, right, price, kind = candidates[-1]
    source_bytes = canonical_json_bytes({
        "left": left.model_dump(mode="json"),
        "pivot": pivot.model_dump(mode="json"),
        "right": right.model_dump(mode="json"),
        "knowable_at_admission_ordinal": right.admission_ordinal,
    })
    rid = sha256_hex(source_bytes)
    return RestartPivotSource(
        restart_reference_id=rid,
        side=side,
        kind=kind,
        price=price,
        reset_admission_ordinal=focal.structural.formal_setup_admission_ordinal,
        confirmed_admission_ordinal=right.admission_ordinal,
        confirmed_admission_ts=right.admission_ts,
        source_bytes=source_bytes,
    )


def materialize_restart_reference(
    *, source: RestartPivotSource, lineage: CausalLineage, source_artifact_hash: str
) -> RestartReferenceEvidence:
    return RestartReferenceEvidence.create(
        restart_reference_id=source.restart_reference_id,
        lineage_hash=lineage.lineage_hash,
        side=source.side,
        kind=source.kind,
        price=source.price,
        reset_admission_ordinal=source.reset_admission_ordinal,
        confirmed_admission_ordinal=source.confirmed_admission_ordinal,
        confirmed_admission_ts=source.confirmed_admission_ts,
        source_artifact_hash=source_artifact_hash,
    )


@dataclass(frozen=True, slots=True)
class SupplementSource:
    source_bytes: bytes
    microstructure_warmup_seconds: int
    side_adjusted_aggressor_imbalance_15s: Decimal
    flow_price_response_15s_bps: Decimal


def derive_evaluator_supplement_source(
    *, admissions: Sequence[AdmittedEvent], lineage: CausalLineage, side: PositionSide
) -> SupplementSource | None:
    bbo = [
        e for e in admissions
        if e.source.market_id == lineage.market_id
        and e.source.instrument_id == lineage.instrument_id
        and e.source.data_kind is DataKind.BBO
        and e.continuity_epoch == lineage.continuity_epoch
        and e.admission_epoch == lineage.admission_epoch
        and e.continuity_state is EvidenceState.COMPLETE
        and not e.out_of_order
        and e.admission_ts >= lineage.formal_setup_admission_ts
    ]
    if not bbo:
        return None
    bbo.sort(key=lambda e: e.admission_ordinal)
    end = bbo[-1]
    start_cutoff = end.admission_ts - 15_000_000_000
    start = next((e for e in bbo if e.admission_ts >= start_cutoff), None)
    if start is None or start.admission_ts > start_cutoff:
        return None
    trades = [
        e for e in admissions
        if e.source.market_id == lineage.market_id
        and e.source.instrument_id == lineage.instrument_id
        and e.source.data_kind is DataKind.TRADE
        and start_cutoff <= e.admission_ts <= end.admission_ts
        and e.continuity_epoch == lineage.continuity_epoch
        and e.admission_epoch == lineage.admission_epoch
        and e.continuity_state is EvidenceState.COMPLETE
        and not e.out_of_order
    ]
    buy = Decimal("0")
    sell = Decimal("0")
    for trade in trades:
        notional = _decimal(trade.source.payload, "price") * _decimal(trade.source.payload, "size")
        aggressor = (trade.source.provider_aggressor_side or "").upper()
        if "BUY" in aggressor:
            buy += notional
        elif "SELL" in aggressor:
            sell += notional
        else:
            return None
    total = buy + sell
    sign = Decimal("1") if side is PositionSide.LONG else Decimal("-1")
    imbalance = Decimal("0") if total == 0 else sign * (buy - sell) / total

    def executable(event: AdmittedEvent) -> Decimal:
        key = "ask_price" if side is PositionSide.LONG else "bid_price"
        return _decimal(event.source.payload, key)

    first = executable(start)
    last = executable(end)
    response = sign * (last - first) / first * Decimal("10000")
    source_bytes = canonical_json_bytes({
        "start_bbo": start.admission_hash,
        "end_bbo": end.admission_hash,
        "trades": [e.admission_hash for e in trades],
        "window_ns": 15_000_000_000,
        "side": side.value,
    })
    warmup = max(0, (end.admission_ts - lineage.formal_setup_admission_ts) // 1_000_000_000)
    return SupplementSource(source_bytes, int(warmup), imbalance, response)


def materialize_evaluator_supplement(
    *, source: SupplementSource, lineage: CausalLineage, source_artifact_hash: str
) -> EvaluatorSupplementEvidence:
    return EvaluatorSupplementEvidence.create(
        causal_lineage_hash=lineage.lineage_hash,
        source_artifact_hash=source_artifact_hash,
        microstructure_warmup_seconds=source.microstructure_warmup_seconds,
        side_adjusted_aggressor_imbalance_15s=source.side_adjusted_aggressor_imbalance_15s,
        flow_price_response_15s_bps=source.flow_price_response_15s_bps,
    )


def replay_frozen_structural_source(
    *, admissions: Sequence[AdmittedEvent], registry_markets: Mapping[str, RegistryMarket],
    provider_minimum_ticks: Mapping[str, Decimal],
) -> StructuralSourceEvidence:
    if (
        set(registry_markets) != set(FROZEN_BY_MARKET)
        or set(provider_minimum_ticks) != set(FROZEN_BY_MARKET)
    ):
        raise RealT2IntegrationError("global replay requires exact 20-market source boundary")
    package = _strategy_package()
    evaluators: dict[str, PilotStrategyEvaluator] = {}
    observed: list[StructuralSourceEvidence] = []
    last_5m_ts_event: dict[str, int] = {}
    ordered = tuple(sorted(admissions, key=lambda e: e.admission_ordinal))
    ordinals = [e.admission_ordinal for e in ordered]
    if ordinals != sorted(set(ordinals)):
        raise RealT2IntegrationError("rooted admissions have duplicate/conflicting causal order")
    for event in ordered:
        if (
            event.source.data_kind is not DataKind.BAR
            or not event.source.event_context.endswith("-5-MINUTE-LAST-EXTERNAL")
        ):
            continue
        strategy_input = admitted_external_5m_to_strategy_input(
            event, strategy_package_hash=package.manifest_hash
        )
        previous = last_5m_ts_event.get(event.source.market_id)
        if previous is not None and event.source.ts_event != previous + 5 * ONE_MINUTE_NS:
            raise RealT2IntegrationError(
                "rooted 5m sequence has a gap/conflict; synthetic repair is prohibited"
            )
        last_5m_ts_event[event.source.market_id] = event.source.ts_event
        tick = provider_minimum_ticks[event.source.market_id]
        if not tick.is_finite() or tick <= 0:
            raise RealT2IntegrationError("rooted provider-native minimum tick is invalid")
        evaluator = evaluators.get(event.source.market_id)
        if evaluator is None:
            evaluator = PilotStrategyEvaluator(
                manifest=package, market_id=event.source.market_id, minimum_tick=tick
            )
            evaluators[event.source.market_id] = evaluator
        envelope = evaluator.evaluate(strategy_input)
        if envelope is None:
            continue
        for decision in envelope.kernel_result.decisions:
            if decision.decision is DecisionKind.FORMAL_SETUP_CONFIRMED:
                observed.append(StructuralSourceEvidence.create(
                    strategy_package_hash=package.manifest_hash,
                    admission=event,
                    decision=decision,
                ))
    if not observed:
        raise RealT2IntegrationError("rooted source contains no Formal Setup")
    return min(observed, key=lambda s: (
        s.formal_setup_admission_ts,
        s.exact_market_set_ordinal,
        s.formal_setup_admission_ordinal,
        s.formal_setup_id,
    ))


def provider_instrument_metadata_document(
    *,
    raw_provider_response: bytes,
    materialization: FixedMarketMaterialization,
    provider_instrument: ProviderInstrumentView,
) -> bytes:
    normalized = provider_instrument.to_dict()
    if str(provider_instrument.id) != materialization.identity.instrument_id:
        raise RealT2IntegrationError(
            "provider instrument id conflicts with frozen identity"
        )
    if (
        provider_instrument.size_precision
        != materialization.registry_market.size_decimals
    ):
        raise RealT2IntegrationError(
            "provider size precision conflicts with raw metadata"
        )
    tick = _provider_tick(provider_instrument)
    quantity = Decimal(str(provider_instrument.size_increment))
    if not quantity.is_finite() or quantity <= 0:
        raise RealT2IntegrationError("provider-native size increment is invalid")
    return canonical_json_bytes({
        "schema_version": "TASK5D_PROVIDER_INSTRUMENT_METADATA_V1",
        "market_id": materialization.identity.market_id,
        "instrument_id": materialization.identity.instrument_id,
        "raw_provider_response_sha256": raw_response_sha256(raw_provider_response),
        "registry_metadata_hash": materialization.registry_market.metadata_hash,
        "provider_minimum_tick": str(tick),
        "provider_size_increment": str(quantity),
        "provider_instrument": normalized,
    })


@dataclass(frozen=True, slots=True)
class CausalBboBinding:
    admission: AdmittedEvent
    executable_price: Decimal
    opposite_l1_size: Decimal


@dataclass(frozen=True, slots=True)
class ExitTriggerBinding:
    """First source-bound causal exit event; absent is truthfully not evaluable."""

    admission: AdmittedEvent
    executable_price: Decimal
    reason: str
    semantic_hash: str


@dataclass(frozen=True, slots=True)
class FundingHistoryAssessment:
    state: str
    source_hash: str | None
    event_count: int
    reason: str


@dataclass(frozen=True, slots=True)
class Task5DValidationMaterialization:
    validation_source_artifact: RoleBoundSourceArtifact
    validation_reference: ValidationReference
    validation_reference_artifact: RoleBoundSourceArtifact
    quantity_source_hash: str
    friction_source_hash: str


def _assert_frozen_validation_source_hashes() -> None:
    checks = (
        (FEE_CONTROL_RECORD, FEE_PROFILE_SOURCE_HASH),
        (FRICTION_POLICY_RECORD, FRICTION_POLICY_SOURCE_HASH),
        (EXECUTION_CONTROL_RECORD, EXECUTION_MODEL_SOURCE_HASH),
        (LATENCY_CONTROL_RECORD, LATENCY_CONTROL_SOURCE_HASH),
    )
    for record, expected in checks:
        if sha256_hex(canonical_json_bytes(record)) != expected:
            raise RealT2IntegrationError("frozen Validation source hash drifted")


def frozen_task5d_prospective_candidate() -> ProspectiveEconomicCandidateIdentity:
    config = CandidateConfig.model_validate(
        {
            "entry_activation": "EA0",
            "ea3_base": None,
            "attempt_stop": "AP0",
            "room_to_cost_k": "3",
            "fixed_stop_bps": None,
            "rv_multiplier": None,
            "time_stop_seconds": None,
            "reentry_policy": "NO_REENTRY_REFERENCE",
            "winner_confirmation": "WC0",
            "winner_progress_bps": "10",
            "persistence_seconds": None,
            "winner_add": "A0_NO_ADD",
            "exit_policy": "X0",
            "giveback_ratio": None,
            "comparison_role": "REFERENCE",
        }
    )
    prospective = ProspectiveEconomicCandidateIdentity.create(
        candidate_id="TASK5D_PHASE0C_TECHNICAL_REFERENCE_V1",
        config=config,
    )
    if (
        prospective.prospective_candidate_hash
        != PHASE0C_PROSPECTIVE_CANDIDATE_HASH
    ):
        raise RealT2IntegrationError(
            "Phase 0C prospective candidate identity drifted"
        )
    return prospective


def task5d_execution_model_config() -> ExecutionModelConfig:
    return ExecutionModelConfig.model_validate(
        {
            "book_type": "L1_MBP",
            "order_primitive": "MARKETABLE",
            "prob_fill_on_limit": "0",
            "prob_slippage": "0",
            "trade_execution": True,
            "queue_position": False,
            "liquidity_consumption": True,
            "fill_limit_at_price": False,
            "fill_stop_at_price": False,
            "random_seed": None,
            "l1_size_feasibility_required": True,
            "passive_touch_equals_fill": False,
            "trigger_price_equals_fill": False,
            "execution_model_limited": True,
        }
    )


def materialize_task5d_g4_manifest(
    *,
    exact_source_git_head: str,
    exact_source_git_tree: str,
    e4_manifest_hash: str,
    pit_snapshot_hash: str,
    structural_artifact: RoleBoundSourceArtifact,
    candidate: CandidateManifest,
    e4_admission_artifacts: Sequence[RoleBoundSourceArtifact],
) -> G4RunManifest:
    if structural_artifact.role is not T2SourceRole.STRUCTURAL_SOURCE:
        raise RealT2IntegrationError(
            "G4 manifest requires exact structural source artifact"
        )
    evidence = tuple(
        EvidenceArtifactHash(name=item.name, sha256=item.artifact_hash)
        for item in sorted(e4_admission_artifacts, key=lambda item: item.name)
    )
    if not evidence:
        raise RealT2IntegrationError(
            "G4 manifest requires exact E4 admission evidence"
        )
    return G4RunManifest.create(
        run_id=f"task5d-g4-{structural_artifact.artifact_hash[:24]}",
        git_sha=exact_source_git_head,
        git_tree=exact_source_git_tree,
        source_e4_manifest_hash=e4_manifest_hash,
        source_pit_snapshot_hash=pit_snapshot_hash,
        source_evidence_artifact_hashes=evidence,
        structural_component_manifest_hash=structural_artifact.artifact_hash,
        execution_model=task5d_execution_model_config(),
        candidates=(candidate,),
        trial_adaptivity_id="task5d-single-prospective-v1",
        cutoff_id="task5d-14400s-single-attempt-v1",
    )


def position_side_for_focal(focal: FormalSetupObservation) -> PositionSide:
    side = focal.structural.strategy_decision().side.value
    if side == "LONG":
        return PositionSide.LONG
    if side == "SHORT":
        return PositionSide.SHORT
    raise RealT2IntegrationError("focal Strategy side is unsupported")


def select_focal_causal_bbo(
    *,
    admissions: Sequence[AdmittedEvent],
    focal: FormalSetupObservation,
    side: PositionSide,
    evaluation_admission_hash: str,
) -> CausalBboBinding | None:
    """Bind the exact current evaluation BBO; never select at cutoff hindsight."""
    frozen = FROZEN_BY_MARKET[focal.structural.market_id]
    eligible = tuple(
        event
        for event in admissions
        if event.source.data_kind is DataKind.BBO
        and event.source.market_id == focal.structural.market_id
        and event.source.instrument_id == frozen.instrument_id
        and event.continuity_epoch == focal.continuity_epoch
        and event.admission_epoch == focal.admission_epoch
        and event.continuity_state is EvidenceState.COMPLETE
        and not event.out_of_order
        and (
            event.admission_ordinal
            > focal.structural.formal_setup_admission_ordinal
        )
        and event.admission_ts >= focal.structural.formal_setup_admission_ts
        and event.admission_hash == evaluation_admission_hash
    )
    if len(eligible) > 1:
        raise RealT2IntegrationError("evaluation BBO identity is ambiguous")
    if not eligible:
        return None
    admission = eligible[0]
    bid = _decimal(admission.source.payload, "bid_price")
    ask = _decimal(admission.source.payload, "ask_price")
    bid_size = _decimal(admission.source.payload, "bid_size")
    ask_size = _decimal(admission.source.payload, "ask_size")
    if bid <= 0 or ask <= bid or bid_size <= 0 or ask_size <= 0:
        raise RealT2IntegrationError("causal BBO is invalid")
    if side is PositionSide.LONG:
        return CausalBboBinding(admission, ask, ask_size)
    return CausalBboBinding(admission, bid, bid_size)


def select_first_exit_trigger(
    *,
    admissions: Sequence[AdmittedEvent],
    focal: FormalSetupObservation,
    side: PositionSide,
    entry_binding: CausalBboBinding,
    entry_executable_price: Decimal,
    candidate: CandidateConfig,
) -> ExitTriggerBinding | None:
    """Use frozen AP0/WC0/X0 semantics over only post-entry causal BBOs."""
    decision = focal.structural.strategy_decision()
    stop = decision.structural_stop
    target = decision.target_reference
    if stop is None or target is None or target.price <= 0:
        return None
    if candidate.exit_policy.value != "X0":
        raise RealT2IntegrationError("Task5D exit selector only accepts frozen X0")
    winner = False
    ordered = sorted(
        admissions,
        key=lambda item: (
            item.admission_ordinal,
            item.admission_ts,
            item.admission_hash,
        ),
    )
    for event in ordered:
        if event.admission_ordinal <= entry_binding.admission.admission_ordinal:
            continue
        if (
            event.source.data_kind is not DataKind.BBO
            or event.source.market_id != focal.structural.market_id
            or event.source.instrument_id != entry_binding.admission.source.instrument_id
            or event.continuity_epoch != focal.continuity_epoch
            or event.admission_epoch != focal.admission_epoch
            or event.continuity_state is not EvidenceState.COMPLETE
            or event.out_of_order
        ):
            continue
        bid = _decimal(event.source.payload, "bid_price")
        ask = _decimal(event.source.payload, "ask_price")
        executable = bid if side is PositionSide.LONG else ask
        if executable <= 0:
            raise RealT2IntegrationError("exit trigger BBO is invalid")
        progress = (
            (executable - entry_executable_price) / entry_executable_price
            if side is PositionSide.LONG
            else (entry_executable_price - executable) / entry_executable_price
        ) * Decimal("10000")
        winner = winner or winner_confirmed(
            candidate=candidate,
            favorable_progress_bps=progress,
            persistence_seconds=0,
            fresh_favorable_structure=False,
            favorable_flow_price_response=False,
        )
        protective = executable <= stop if side is PositionSide.LONG else executable >= stop
        target_hit = (
            winner
            and (
                executable >= target.price
                if side is PositionSide.LONG
                else executable <= target.price
            )
        )
        if exit_triggered(
            candidate=candidate,
            fixed_r_reference_hit=target_hit,
            structural_deterioration=False,
            giveback_ratio=Decimal("0"),
            protective_stop_hit=protective,
            thesis_invalid=False,
        ):
            reason = "AP0_PROTECTIVE_STOP" if protective else "X0_TARGET_AFTER_WC0"
            semantic_hash = sha256_hex(canonical_json_bytes({
                "entry_bbo_admission_hash": entry_binding.admission.admission_hash,
                "exit_bbo_admission_hash": event.admission_hash,
                "structural_decision_hash": focal.structural.decision_hash,
                "candidate_config": candidate.model_dump(mode="json"),
                "reason": reason,
                "executable_price": str(executable),
            }))
            return ExitTriggerBinding(event, executable, reason, semantic_hash)
    return None


def assess_public_funding_history(
    *,
    raw_response: bytes | None,
    parsed_response: object | None,
    coin: str,
    start_time_ms: int,
    end_time_ms: int,
) -> FundingHistoryAssessment:
    if (
        raw_response is None
        or parsed_response is None
        or start_time_ms < 0
        or end_time_ms < start_time_ms
    ):
        return FundingHistoryAssessment(
            "NOT_EVALUABLE",
            None,
            0,
            "MISSING_OR_INVALID_PUBLIC_FUNDING_SOURCE",
        )
    try:
        reparsed = json.loads(raw_response)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return FundingHistoryAssessment(
            "NOT_EVALUABLE", None, 0, "INVALID_PUBLIC_FUNDING_SOURCE"
        )
    if reparsed != parsed_response or not isinstance(parsed_response, list):
        return FundingHistoryAssessment(
            "NOT_EVALUABLE", None, 0, "INVALID_PUBLIC_FUNDING_SOURCE"
        )
    for item in parsed_response:
        if not isinstance(item, dict):
            return FundingHistoryAssessment(
                "NOT_EVALUABLE", None, 0, "INVALID_PUBLIC_FUNDING_EVENT"
            )
        event_coin = item.get("coin")
        event_time = item.get("time")
        if (
            event_coin != coin
            or isinstance(event_time, bool)
            or not isinstance(event_time, int)
            or not start_time_ms <= event_time <= end_time_ms
        ):
            return FundingHistoryAssessment(
                "NOT_EVALUABLE", None, 0, "INVALID_PUBLIC_FUNDING_EVENT"
            )
    source_hash = sha256_hex(raw_response)
    if parsed_response:
        return FundingHistoryAssessment(
            "NOT_EVALUABLE",
            source_hash,
            len(parsed_response),
            "FUNDING_EVENT_PRESENT_V1",
        )
    return FundingHistoryAssessment(
        "NOT_APPLICABLE",
        source_hash,
        0,
        "NO_FUNDING_EVENT_IN_EXACT_HOLD_INTERVAL",
    )


def _source_reference(
    artifact: RoleBoundSourceArtifact,
) -> SourceReference:
    return SourceReference(
        role=artifact.role,
        name=artifact.name,
        artifact_hash=artifact.artifact_hash,
    )


def _validated_execution_model(manifest: G4RunManifest) -> None:
    expected = task5d_execution_model_config()
    if manifest.execution_model != expected:
        raise RealT2IntegrationError(
            "G4 execution model differs from frozen Validation source"
        )


def materialize_task5d_validation_source(
    *,
    clock_start_ns: int,
    exact_source_git_head: str,
    exact_source_git_tree: str,
    focal: FormalSetupObservation,
    side: PositionSide,
    causal_bbo: CausalBboBinding,
    provider_instrument: ProviderInstrumentView,
    registry_market: RegistryMarket,
    instrument_metadata_version: str,
    instrument_metadata_artifact: RoleBoundSourceArtifact,
    e4_admission_artifact: RoleBoundSourceArtifact,
    prospective_candidate_artifact: RoleBoundSourceArtifact,
    prospective_candidate: ProspectiveEconomicCandidateIdentity,
    g4_run_manifest_artifact: RoleBoundSourceArtifact,
    g4_run_manifest: G4RunManifest,
) -> Task5DValidationMaterialization:
    _assert_frozen_validation_source_hashes()
    if clock_start_ns <= 0:
        raise RealT2IntegrationError("Validation CLOCK_START_NS is invalid")
    if registry_market.identity.dex != "MAIN" or registry_market.is_hip3:
        raise RealT2IntegrationError(
            "Validation V1 is MAIN non-HIP3 only"
        )
    if (
        prospective_candidate.prospective_candidate_hash
        != PHASE0C_PROSPECTIVE_CANDIDATE_HASH
    ):
        raise RealT2IntegrationError(
            "Validation candidate is not frozen Phase 0C identity"
        )
    if (
        prospective_candidate_artifact.role
        is not T2SourceRole.PROSPECTIVE_ECONOMIC_CANDIDATE_IDENTITY
        or ProspectiveEconomicCandidateIdentity.model_validate_json(
            prospective_candidate_artifact.exact_bytes()
        )
        != prospective_candidate
    ):
        raise RealT2IntegrationError(
            "prospective candidate artifact is not exact"
        )
    if (
        g4_run_manifest_artifact.role is not T2SourceRole.G4_RUN_MANIFEST
        or G4RunManifest.model_validate_json(
            g4_run_manifest_artifact.exact_bytes()
        )
        != g4_run_manifest
    ):
        raise RealT2IntegrationError("G4 manifest artifact is not exact")
    _validated_execution_model(g4_run_manifest)
    if (
        instrument_metadata_artifact.role
        is not T2SourceRole.INSTRUMENT_METADATA
    ):
        raise RealT2IntegrationError(
            "instrument metadata is rooted under wrong role"
        )
    if e4_admission_artifact.role is not T2SourceRole.E4_ADMISSION:
        raise RealT2IntegrationError("causal BBO is rooted under wrong role")
    rooted_bbo = AdmittedEvent.model_validate_json(
        e4_admission_artifact.exact_bytes()
    )
    if rooted_bbo != causal_bbo.admission:
        raise RealT2IntegrationError(
            "causal BBO artifact does not bind exact admission"
        )
    provider_view = _provider_instrument_view(provider_instrument)
    if str(provider_view.id) != causal_bbo.admission.source.instrument_id:
        raise RealT2IntegrationError(
            "provider instrument conflicts with causal BBO"
        )
    quantity = Decimal(str(provider_view.size_increment))
    if not quantity.is_finite() or quantity <= 0:
        raise RealT2IntegrationError("provider size increment is invalid")
    size_decimals = provider_view.size_precision
    quantum = Decimal(1).scaleb(-size_decimals)
    if quantity != quantity.quantize(quantum):
        raise RealT2IntegrationError(
            "provider size increment is not grid-valid"
        )
    if quantity > causal_bbo.opposite_l1_size:
        raise RealT2IntegrationError(
            "one provider size increment exceeds causal opposite L1"
        )
    metadata = json.loads(instrument_metadata_artifact.exact_bytes())
    if (
        not isinstance(metadata, dict)
        or metadata.get("market_id") != focal.structural.market_id
        or (
            metadata.get("instrument_id")
            != causal_bbo.admission.source.instrument_id
        )
        or Decimal(str(metadata.get("provider_size_increment"))) != quantity
    ):
        raise RealT2IntegrationError(
            "instrument metadata source conflicts with focal quantity"
        )
    quantity_record = {
        "schema_version": "TASK5D_TECHNICAL_QUANTITY_SOURCE_V1",
        "rule_id": TECHNICAL_QUANTITY_RULE_ID,
        "market_id": focal.structural.market_id,
        "instrument_id": causal_bbo.admission.source.instrument_id,
        "side": side.value,
        "instrument_metadata_version": instrument_metadata_version,
        "instrument_metadata_hash": instrument_metadata_artifact.artifact_hash,
        "bbo_admission_hash": causal_bbo.admission.admission_hash,
        "provider_size_increment": str(quantity),
        "size_decimals": size_decimals,
        "opposite_l1_size": str(causal_bbo.opposite_l1_size),
        "quantity": str(quantity),
        "rule_result": "PASS_ONE_INCREMENT_LE_OPPOSITE_L1",
    }
    quantity_hash = sha256_hex(canonical_json_bytes(quantity_record))
    friction_record = {
        "schema_version": "TASK5D_ALL_IN_FRICTION_INSTANCE_V1",
        "policy_source_hash": FRICTION_POLICY_SOURCE_HASH,
        "fee_profile_source_hash": FEE_PROFILE_SOURCE_HASH,
        "execution_model_source_hash": EXECUTION_MODEL_SOURCE_HASH,
        "technical_quantity_rule_source_hash": quantity_hash,
        "instrument_metadata_hash": instrument_metadata_artifact.artifact_hash,
        "focal_bbo_admission_hash": causal_bbo.admission.admission_hash,
        "entry_fee_bps": "4.5",
        "exit_fee_bps": "4.5",
        "spread_state": "NOT_APPLICABLE_AS_SEPARATE_DEBIT",
        "slippage_extra_control_bps": "0",
        "impact_extra_control_bps": "0",
        "funding_predecision_state": (
            "NOT_APPLICABLE_TECHNICAL_REFERENCE"
        ),
        "implementation_shortfall_state": "OUTCOME_ONLY",
        "all_in_friction_bps": "9.0",
    }
    friction_hash = sha256_hex(canonical_json_bytes(friction_record))
    document = {
        "schema_version": "TASK5D_VALIDATION_SOURCE_V1",
        "profile_id": VALIDATION_SOURCE_PROFILE_ID,
        "validation_reference_id": VALIDATION_REFERENCE_ID,
        "authority": (
            "Issue_85_comment_5709098638",
            "Issue_85_comment_5709405967",
            "Issue_85_comment_5741961048",
            "Issue_163_comment_5758381459",
            "Issue_163_comment_5760105677",
        ),
        "fee_control": {
            "record": FEE_CONTROL_RECORD,
            "source_hash": FEE_PROFILE_SOURCE_HASH,
        },
        "friction_control": {
            "policy_record": FRICTION_POLICY_RECORD,
            "policy_source_hash": FRICTION_POLICY_SOURCE_HASH,
            "record": friction_record,
            "source_hash": friction_hash,
        },
        "execution_control": {
            "record": EXECUTION_CONTROL_RECORD,
            "source_hash": EXECUTION_MODEL_SOURCE_HASH,
        },
        "technical_quantity_control": {
            "record": quantity_record,
            "source_hash": quantity_hash,
        },
        "latency_control": {
            "record": LATENCY_CONTROL_RECORD,
            "source_hash": LATENCY_CONTROL_SOURCE_HASH,
        },
        "attempt_binding": {
            "clock_start_ns": clock_start_ns,
            "source_git_head": exact_source_git_head,
            "source_git_tree": exact_source_git_tree,
            "focal_market_id": focal.structural.market_id,
            "focal_instrument_id": (
                causal_bbo.admission.source.instrument_id
            ),
            "focal_bbo_admission_hash": (
                causal_bbo.admission.admission_hash
            ),
            "instrument_metadata_version": instrument_metadata_version,
            "instrument_metadata_hash": (
                instrument_metadata_artifact.artifact_hash
            ),
            "prospective_candidate_hash": (
                prospective_candidate.prospective_candidate_hash
            ),
        },
    }
    references = tuple(
        _source_reference(item)
        for item in (
            instrument_metadata_artifact,
            e4_admission_artifact,
            prospective_candidate_artifact,
            g4_run_manifest_artifact,
        )
    )
    validation_source = RoleBoundSourceArtifact.create(
        role=T2SourceRole.VALIDATION_SOURCE,
        name="task5d-validation-source-v1",
        exact_bytes=canonical_json_bytes(document),
        references=references,
    )
    validation = ValidationReference.create(
        validation_reference_id=VALIDATION_REFERENCE_ID,
        source_artifact_hash=validation_source.artifact_hash,
        fee_profile_id=FEE_PROFILE_ID,
        fee_profile_source_hash=FEE_PROFILE_SOURCE_HASH,
        fee_effective_at_ns=clock_start_ns,
        fee_bps=Decimal("4.5"),
        all_in_friction_state_id=ALL_IN_FRICTION_STATE_ID,
        all_in_friction_source_hash=friction_hash,
        all_in_friction_bps=Decimal("9.0"),
        execution_model_id=EXECUTION_MODEL_ID,
        execution_model_source_hash=EXECUTION_MODEL_SOURCE_HASH,
        technical_quantity_rule_id=TECHNICAL_QUANTITY_RULE_ID,
        technical_quantity_rule_source_hash=quantity_hash,
        latency_control_id=LATENCY_CONTROL_ID,
        latency_control_source_hash=LATENCY_CONTROL_SOURCE_HASH,
        latency_ms=Decimal("0"),
        latency_evidence_role=LatencyEvidenceRole.CONTROL_ONLY,
    )
    if not validation.fully_materialized:
        raise RealT2IntegrationError(
            "ValidationReference is not fully materialized"
        )
    validation_reference_artifact = RoleBoundSourceArtifact.create(
        role=T2SourceRole.VALIDATION_REFERENCE,
        name="task5d-validation-reference-v1",
        exact_bytes=canonical_json_bytes(
            validation.model_dump(mode="json")
        ),
        references=(_source_reference(validation_source),),
    )
    return Task5DValidationMaterialization(
        validation_source_artifact=validation_source,
        validation_reference=validation,
        validation_reference_artifact=validation_reference_artifact,
        quantity_source_hash=quantity_hash,
        friction_source_hash=friction_hash,
    )


def validate_task5d_validation_artifacts(
    *,
    validation_source_artifact: RoleBoundSourceArtifact,
    validation_reference_artifact: RoleBoundSourceArtifact,
    validation: ValidationReference,
    exact_source_git_head: str,
    exact_source_git_tree: str,
    focal_market_id: str,
    focal_instrument_id: str,
    focal_bbo_admission_hash: str,
    instrument_metadata_version: str,
    instrument_metadata_artifact: RoleBoundSourceArtifact,
    e4_admission_artifact: RoleBoundSourceArtifact,
    prospective_candidate_artifact: RoleBoundSourceArtifact,
    g4_run_manifest_artifact: RoleBoundSourceArtifact,
) -> None:
    _assert_frozen_validation_source_hashes()
    if not validation.fully_materialized:
        raise RealT2IntegrationError(
            "Task5D ValidationReference is incomplete"
        )
    if (
        validation.validation_reference_id != VALIDATION_REFERENCE_ID
        or (
            validation.source_artifact_hash
            != validation_source_artifact.artifact_hash
        )
        or validation.production_account_fee_authority
        or validation.actual_user_fee_rate_claim
        or validation.fee_profile_id != FEE_PROFILE_ID
        or validation.fee_profile_source_hash != FEE_PROFILE_SOURCE_HASH
        or validation.fee_bps != Decimal("4.5")
        or (
            validation.all_in_friction_state_id
            != ALL_IN_FRICTION_STATE_ID
        )
        or validation.all_in_friction_bps != Decimal("9.0")
        or validation.execution_model_id != EXECUTION_MODEL_ID
        or (
            validation.execution_model_source_hash
            != EXECUTION_MODEL_SOURCE_HASH
        )
        or (
            validation.technical_quantity_rule_id
            != TECHNICAL_QUANTITY_RULE_ID
        )
        or validation.latency_control_id != LATENCY_CONTROL_ID
        or (
            validation.latency_control_source_hash
            != LATENCY_CONTROL_SOURCE_HASH
        )
        or validation.latency_ms != Decimal("0")
        or (
            validation.latency_evidence_role
            is not LatencyEvidenceRole.CONTROL_ONLY
        )
    ):
        raise RealT2IntegrationError(
            "Task5D ValidationReference conflicts with frozen profile"
        )
    parsed_reference = ValidationReference.model_validate_json(
        validation_reference_artifact.exact_bytes()
    )
    if (
        validation_reference_artifact.role
        is not T2SourceRole.VALIDATION_REFERENCE
        or parsed_reference != validation
        or (
            _source_reference(validation_source_artifact)
            not in validation_reference_artifact.references
        )
    ):
        raise RealT2IntegrationError(
            "ValidationReference artifact is not source-bound"
        )
    if validation_source_artifact.role is not T2SourceRole.VALIDATION_SOURCE:
        raise RealT2IntegrationError(
            "Validation source is rooted under wrong role"
        )
    document = json.loads(validation_source_artifact.exact_bytes())
    if not isinstance(document, dict):
        raise RealT2IntegrationError(
            "Validation source document is invalid"
        )
    fee = document.get("fee_control")
    friction = document.get("friction_control")
    execution = document.get("execution_control")
    quantity = document.get("technical_quantity_control")
    latency = document.get("latency_control")
    binding = document.get("attempt_binding")
    if not all(
        isinstance(item, dict)
        for item in (
            fee,
            friction,
            execution,
            quantity,
            latency,
            binding,
        )
    ):
        raise RealT2IntegrationError(
            "Validation source groups are incomplete"
        )
    assert isinstance(fee, dict)
    assert isinstance(friction, dict)
    assert isinstance(execution, dict)
    assert isinstance(quantity, dict)
    assert isinstance(latency, dict)
    assert isinstance(binding, dict)
    quantity_record = quantity.get("record")
    friction_record = friction.get("record")
    if (
        not isinstance(quantity_record, dict)
        or not isinstance(friction_record, dict)
    ):
        raise RealT2IntegrationError(
            "Validation dynamic source records are invalid"
        )
    quantity_hash = sha256_hex(canonical_json_bytes(quantity_record))
    friction_hash = sha256_hex(canonical_json_bytes(friction_record))
    if (
        document.get("schema_version") != "TASK5D_VALIDATION_SOURCE_V1"
        or document.get("profile_id") != VALIDATION_SOURCE_PROFILE_ID
        or (
            document.get("validation_reference_id")
            != VALIDATION_REFERENCE_ID
        )
        or fee
        != {
            "record": FEE_CONTROL_RECORD,
            "source_hash": FEE_PROFILE_SOURCE_HASH,
        }
        or execution
        != {
            "record": EXECUTION_CONTROL_RECORD,
            "source_hash": EXECUTION_MODEL_SOURCE_HASH,
        }
        or latency
        != {
            "record": LATENCY_CONTROL_RECORD,
            "source_hash": LATENCY_CONTROL_SOURCE_HASH,
        }
        or friction.get("policy_record") != FRICTION_POLICY_RECORD
        or (
            friction.get("policy_source_hash")
            != FRICTION_POLICY_SOURCE_HASH
        )
        or friction.get("source_hash") != friction_hash
        or quantity.get("source_hash") != quantity_hash
        or validation.all_in_friction_source_hash != friction_hash
        or (
            validation.technical_quantity_rule_source_hash
            != quantity_hash
        )
        or binding.get("source_git_head") != exact_source_git_head
        or binding.get("source_git_tree") != exact_source_git_tree
        or binding.get("focal_market_id") != focal_market_id
        or binding.get("focal_instrument_id") != focal_instrument_id
        or (
            binding.get("focal_bbo_admission_hash")
            != focal_bbo_admission_hash
        )
        or (
            binding.get("instrument_metadata_version")
            != instrument_metadata_version
        )
        or (
            binding.get("instrument_metadata_hash")
            != instrument_metadata_artifact.artifact_hash
        )
        or (
            binding.get("prospective_candidate_hash")
            != PHASE0C_PROSPECTIVE_CANDIDATE_HASH
        )
    ):
        raise RealT2IntegrationError(
            "Validation source document cross-binding failed"
        )
    expected_references = (
        _source_reference(instrument_metadata_artifact),
        _source_reference(e4_admission_artifact),
        _source_reference(prospective_candidate_artifact),
        _source_reference(g4_run_manifest_artifact),
    )
    if any(
        item not in validation_source_artifact.references
        for item in expected_references
    ):
        raise RealT2IntegrationError(
            "Validation source lacks exact source-reference closure"
        )


def assemble_real_t2_root(
    *,
    artifacts: Sequence[RoleBoundSourceArtifact],
    governance_epoch: str,
    acquisition_plan_hash: str,
    exact_source_git_head: str,
    exact_source_git_tree: str,
    strategy_package_identity: str,
) -> T2SourceRootSnapshot:
    typed = tuple(artifacts)
    if not typed or any(type(x) is not RoleBoundSourceArtifact for x in typed):
        raise RealT2IntegrationError("root requires exact materialized role artifacts")
    by_role: dict[T2SourceRole, list[RoleBoundSourceArtifact]] = {}
    for item in typed:
        by_role.setdefault(item.role, []).append(item)
    singleton = (
        T2SourceRole.E4_RUN_MANIFEST,
        T2SourceRole.E4_PIT_SNAPSHOT,
        T2SourceRole.G4_RUN_MANIFEST,
        T2SourceRole.SELECTED_CANDIDATE,
        T2SourceRole.PROSPECTIVE_ECONOMIC_CANDIDATE_IDENTITY,
        T2SourceRole.STRUCTURAL_SOURCE,
        T2SourceRole.CAUSAL_LINEAGE,
        T2SourceRole.VALIDATION_REFERENCE,
        T2SourceRole.VALIDATION_SOURCE,
        T2SourceRole.PROVIDER_INSTRUMENT_WIRE,
        T2SourceRole.THESIS_OUTCOME,
    )
    for role in singleton:
        if len(by_role.get(role, [])) != 1:
            raise RealT2IntegrationError(f"root requires exactly one {role.value}")
    required_nonempty = (
        T2SourceRole.E4_ADMISSION,
        T2SourceRole.E4_LIFECYCLE,
        T2SourceRole.E4_CONTINUITY,
        T2SourceRole.RESTART_REFERENCE_SOURCE,
        T2SourceRole.RESTART_REFERENCE,
        T2SourceRole.EVALUATOR_SUPPLEMENT_SOURCE,
        T2SourceRole.EVALUATOR_SUPPLEMENT,
        T2SourceRole.COST_SOURCE,
    )
    for role in required_nonempty:
        if not by_role.get(role):
            raise RealT2IntegrationError(f"root requires source role {role.value}")
    for role in (
        T2SourceRole.MARKET_EXPRESSION,
        T2SourceRole.REGISTRY_MARKET,
        T2SourceRole.INSTRUMENT_METADATA,
    ):
        if len(by_role.get(role, [])) != 20:
            raise RealT2IntegrationError(f"root requires 20 {role.value} artifacts")
    def one(role: T2SourceRole) -> RoleBoundSourceArtifact:
        return by_role[role][0]
    return T2SourceRootSnapshot.create(
        task_id=REAL_T2_TASK_ID,
        governance_epoch=governance_epoch,
        acquisition_plan_hash=acquisition_plan_hash,
        exact_source_git_head=exact_source_git_head,
        exact_source_git_tree=exact_source_git_tree,
        e4_run_manifest_hash=one(T2SourceRole.E4_RUN_MANIFEST).artifact_hash,
        e4_pit_snapshot_hash=one(T2SourceRole.E4_PIT_SNAPSHOT).artifact_hash,
        g4_run_manifest_hash=one(T2SourceRole.G4_RUN_MANIFEST).artifact_hash,
        selected_candidate_hash=one(T2SourceRole.SELECTED_CANDIDATE).artifact_hash,
        strategy_package_identity=strategy_package_identity,
        validation_reference_hash=one(T2SourceRole.VALIDATION_REFERENCE).artifact_hash,
        artifacts=typed,
    )
