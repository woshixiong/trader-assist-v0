# mypy: disable-error-code="import-not-found"
"""Thin Nautilus rc5 execution seam for Ordinary VNext G4 development replay."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from trader_assist_v0.contracts.common import Sha256Hex, canonical_json_bytes, sha256_hex
from trader_assist_v0.vnext_g4.contracts import (
    NAUTILUS_VERSION,
    REPRESENTATIVE_MARKET_FLOOR,
    CandidateManifest,
    ExecutionModelConfig,
)

if TYPE_CHECKING:
    from nautilus_trader.backtest import BacktestEngine
    from nautilus_trader.execution import ProbabilisticFillModel


class RepresentativeMarketEvidence(BaseModel):
    """One actual accepted source market; generated labels cannot enter G4E8."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    market_id: Sha256Hex
    instrument_id: str = Field(min_length=3, max_length=160)
    source_kind: Literal["ACCEPTED_E4_CAUSAL"] = "ACCEPTED_E4_CAUSAL"
    source_e4_manifest_hash: Sha256Hex
    source_event_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)
    event_count: int = Field(gt=0)


class ProviderStateProjection(BaseModel):
    """Deterministic observation of provider-owned Cache/Portfolio state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_api: Literal["NAUTILUS_CACHE_PORTFOLIO"] = "NAUTILUS_CACHE_PORTFOLIO"
    cache_type: str
    portfolio_type: str
    order_count: int = Field(ge=0)
    filled_order_count: int = Field(ge=0)
    position_count: int = Field(ge=0)
    account_count: int = Field(ge=0)
    state_hash: Sha256Hex


BACKTEST_NODE_PUBLIC_METHODS = (
    "build",
    "run",
    "dispose",
    "get_engine_cache",
    "get_engine_portfolio",
)


def causal_claim_gate_states(
    *,
    evidence_tier: Literal[
        "T0_SYNTHETIC_CONTROL",
        "T1_SAME_JOB_90S_PUBLIC_E4_PROBE",
        "T2_REAL_CAUSAL_G4_ARTIFACT",
    ],
    synthetic: bool,
    manual_substitution: bool,
    deterministic_replay_proven: bool,
    semantic_derivation_proven: bool,
    validation_materialized: bool,
    canonical_order_intent_proven: bool,
    provider_outcome_cost_provenance_complete: bool,
    restart_equivalence_proven: bool,
) -> dict[str, str]:
    """Map evidence topology to causal gates without promoting controls."""
    if (
        evidence_tier != "T2_REAL_CAUSAL_G4_ARTIFACT"
        or synthetic
        or manual_substitution
    ):
        return {name: "NOT_PROVEN" for name in ("G4E1", "G4E2", "G4E5", "G4E7")}
    g4e1 = "PASS" if deterministic_replay_proven else "NOT_PROVEN"
    g4e2 = (
        "PASS"
        if deterministic_replay_proven
        and semantic_derivation_proven
        and validation_materialized
        and canonical_order_intent_proven
        else "NOT_PROVEN"
    )
    g4e5 = (
        "PASS"
        if g4e2 == "PASS" and provider_outcome_cost_provenance_complete
        else "NOT_PROVEN"
    )
    g4e7 = "PASS" if restart_equivalence_proven else "NOT_PROVEN"
    return {"G4E1": g4e1, "G4E2": g4e2, "G4E5": g4e5, "G4E7": g4e7}


def formal_g4_acceptance(gates: Mapping[str, str]) -> bool:
    """Formal acceptance is total over exactly G4E0..G4E8; no vacuous PASS."""
    required = tuple(f"G4E{index}" for index in range(9))
    return set(gates) == set(required) and all(gates[name] == "PASS" for name in required)


def assert_exact_nautilus_rc5() -> None:
    from importlib.metadata import version

    installed = version("nautilus-trader")
    if installed != NAUTILUS_VERSION:
        raise RuntimeError(f"expected Nautilus {NAUTILUS_VERSION}, installed {installed}")


def build_fill_model(config: ExecutionModelConfig) -> ProbabilisticFillModel:
    """Map explicit project assumptions onto Nautilus' provider-owned fill model."""
    from nautilus_trader.execution import ProbabilisticFillModel

    assert_exact_nautilus_rc5()
    return ProbabilisticFillModel(
        prob_fill_on_limit=float(config.prob_fill_on_limit),
        prob_slippage=float(config.prob_slippage),
        random_seed=config.random_seed,
    )


def new_isolated_backtest_engine(candidate: CandidateManifest) -> BacktestEngine:
    """Create one fresh Nautilus engine per candidate; simulated state is never shared."""
    from nautilus_trader.backtest import BacktestEngine, BacktestEngineConfig
    from nautilus_trader.model import TraderId

    assert_exact_nautilus_rc5()
    config = BacktestEngineConfig(
        trader_id=TraderId(f"VNEXT-G4-{candidate.candidate_hash[:16]}"),
        bypass_logging=True,
    )
    return BacktestEngine(config)


def assert_backtest_node_catalog_surface() -> None:
    """Fail closed unless the exact rc5 high-level catalog replay surface is available."""
    from nautilus_trader.backtest import BacktestNode
    from nautilus_trader.config import (
        BacktestDataConfig,
        BacktestEngineConfig,
        BacktestRunConfig,
        BacktestVenueConfig,
    )
    from nautilus_trader.persistence import ParquetDataCatalog

    assert_exact_nautilus_rc5()
    public_types = (
        BacktestNode,
        BacktestDataConfig,
        BacktestEngineConfig,
        BacktestRunConfig,
        BacktestVenueConfig,
        ParquetDataCatalog,
    )
    if not all(callable(item) for item in public_types):
        raise RuntimeError("exact rc5 high-level catalog replay surface is incomplete")
    missing = tuple(
        name
        for name in BACKTEST_NODE_PUBLIC_METHODS
        if not callable(getattr(BacktestNode, name, None))
    )
    if missing:
        raise RuntimeError(f"exact rc5 BacktestNode is missing public methods: {missing}")


def _as_collection(value: object, *, name: str) -> Collection[object]:
    if isinstance(value, dict):
        return tuple(value.values())
    if isinstance(value, Collection) and not isinstance(value, str | bytes):
        return value
    raise RuntimeError(f"Nautilus Cache {name} did not return a public collection")


def _identity_rows(values: Collection[object], fields: tuple[str, ...]) -> list[dict[str, str]]:
    rows = [
        {field: str(getattr(value, field, None)) for field in fields}
        for value in values
    ]
    return sorted(rows, key=lambda row: tuple(row.values()))


def _provider_account(
    cache: object,
    portfolio: object,
    *,
    venue: object | None,
    account_id: object | None,
) -> object:
    """Resolve one known run account through rc5 public lookup methods only."""
    lookup_available = False
    account = None
    if account_id is not None:
        lookup = getattr(cache, "account", None)
        if callable(lookup):
            lookup_available = True
            account = lookup(account_id)
    if account is None and venue is not None:
        for owner, name in (
            (cache, "account_for_venue"),
            (portfolio, "account"),
        ):
            lookup = getattr(owner, name, None)
            if callable(lookup):
                lookup_available = True
                account = lookup(venue)
                if account is not None:
                    break
    if not lookup_available:
        raise RuntimeError("Nautilus Cache/Portfolio lacks a public account lookup method")
    if account is None:
        raise RuntimeError("known run account was not found in provider-owned state")
    return account


def project_provider_native_state(
    cache: object,
    portfolio: object,
    *,
    venue: object | None = None,
    account_id: object | None = None,
) -> ProviderStateProjection:
    """Project public Cache/Portfolio state without raw-engine or report access."""
    if venue is None and account_id is None:
        raise ValueError("known run venue or account identity is required")
    orders_method = getattr(cache, "orders", None)
    positions_method = getattr(cache, "positions", None)
    methods = {"orders": orders_method, "positions": positions_method}
    missing = tuple(name for name, method in methods.items() if not callable(method))
    if missing:
        raise RuntimeError(f"Nautilus Cache is missing public state methods: {missing}")
    assert callable(orders_method)
    assert callable(positions_method)
    orders = _as_collection(orders_method(), name="orders")
    positions = _as_collection(positions_method(), name="positions")
    account = _provider_account(
        cache,
        portfolio,
        venue=venue,
        account_id=account_id,
    )
    accounts = (account,)
    cache_type = f"{type(cache).__module__}.{type(cache).__qualname__}"
    portfolio_type = f"{type(portfolio).__module__}.{type(portfolio).__qualname__}"
    filled_orders = tuple(
        item for item in orders if str(getattr(item, "filled_qty", "0")) not in {"0", "0.0"}
    )
    payload = {
        "source_api": "NAUTILUS_CACHE_PORTFOLIO",
        "cache_type": cache_type,
        "portfolio_type": portfolio_type,
        "orders": _identity_rows(
            orders,
            ("client_order_id", "status", "filled_qty", "avg_px"),
        ),
        "positions": _identity_rows(
            positions,
            ("id", "instrument_id", "side", "quantity"),
        ),
        "accounts": _identity_rows(
            accounts,
            ("id", "account_type", "base_currency"),
        ),
    }
    return ProviderStateProjection(
        cache_type=cache_type,
        portfolio_type=portfolio_type,
        order_count=len(orders),
        filled_order_count=len(filled_orders),
        position_count=len(positions),
        account_count=len(accounts),
        state_hash=sha256_hex(canonical_json_bytes(payload)),
    )


def assert_representative_scale(market_ids: tuple[str, ...]) -> None:
    unique = set(market_ids)
    if len(unique) != len(market_ids):
        raise ValueError("representative-scale market identities must be unique")
    if len(unique) < REPRESENTATIVE_MARKET_FLOOR:
        raise ValueError(
            f"formal G4 scale requires at least {REPRESENTATIVE_MARKET_FLOOR} markets"
        )


def assert_actual_representative_scale(
    evidence: tuple[RepresentativeMarketEvidence, ...],
) -> tuple[str, ...]:
    """Accept G4E8 only for source-bound markets with actual retained events."""
    if not evidence:
        raise ValueError("actual representative scale requires retained market evidence")
    markets = tuple(sorted(item.market_id for item in evidence))
    if len(markets) != len(set(markets)):
        raise ValueError("representative-scale market identities must be unique")
    if len({item.source_e4_manifest_hash for item in evidence}) != 1:
        raise ValueError("representative markets must bind one accepted E4 source manifest")
    all_event_hashes = tuple(
        event_hash for item in evidence for event_hash in item.source_event_hashes
    )
    if len(all_event_hashes) != len(set(all_event_hashes)):
        raise ValueError("representative causal event identities must be unique")
    assert_representative_scale(markets)
    return markets


def candidate_state_isolation_plan(
    candidates: tuple[CandidateManifest, ...],
) -> tuple[str, ...]:
    """Return exact candidate hashes requiring independent engine/context state."""
    hashes = tuple(candidate.candidate_hash for candidate in candidates)
    if len(hashes) != len(set(hashes)):
        raise ValueError("duplicate candidate identity would violate comparison isolation")
    return hashes
