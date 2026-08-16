"""Deterministic Manual-40 catalog and First-Launch-20 resolver over official metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import cast

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

from .models import AssetClass, MarketIdentity, RegistryMarket, RegistryTier


@dataclass(frozen=True)
class UniverseRequest:
    display: str
    tier: RegistryTier
    asset_class: AssetClass
    dex: str
    coin: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Resolution:
    request: UniverseRequest
    status: str
    market: RegistryMarket | None
    reason: str | None = None


def _requests() -> tuple[UniverseRequest, ...]:
    native = (
        ("BTC", "P0"),
        ("ETH", "P0"),
        ("SOL", "P0"),
        ("HYPE", "P0"),
        ("XRP", "P0"),
        ("DOGE", "P2"),
        ("BNB", "P2"),
        ("AAVE", "P2"),
        ("SUI", "P2"),
    )
    requests = [
        UniverseRequest(display, RegistryTier(tier), AssetClass.CRYPTO, "MAIN", coin)
        for coin, tier in native
        for display in (coin,)
    ]
    requests.extend(
        [
            UniverseRequest(
                "SKHX", RegistryTier.P0, AssetClass.EQUITY, "xyz", "xyz:SKHX", ("SKHYNIX",)
            ),
            UniverseRequest("MU", RegistryTier.P0, AssetClass.EQUITY, "xyz", "xyz:MU"),
            UniverseRequest("SNDK", RegistryTier.P0, AssetClass.EQUITY, "xyz", "xyz:SNDK"),
            UniverseRequest("SPCX", RegistryTier.P0, AssetClass.EQUITY, "xyz", "xyz:SPCX"),
            UniverseRequest("XYZ100", RegistryTier.P0, AssetClass.INDEX, "xyz", "xyz:XYZ100"),
            UniverseRequest("SP500", RegistryTier.P0, AssetClass.INDEX, "xyz", "xyz:SP500"),
            # User-facing WTIOIL is the live builder contract CL.  Do not
            # resolve this from prose alone: the resolver still requires the
            # exact official xyz:CL metadata record.
            UniverseRequest(
                "WTIOIL", RegistryTier.P1, AssetClass.COMMODITY, "xyz", "xyz:CL", ("CL",)
            ),
        ]
    )
    p1 = "SILVER NVDA DRAM BRENTOIL INTC PLTR SMSN GOOGL TSLA AMD MSTR COIN EWY".split()
    p2 = "AAPL MSFT META AMZN CRCL MRVL RKLB HOOD CRWV NATGAS GOLD".split()
    requests.extend(
        UniverseRequest(item, RegistryTier.P1, _asset_class(item), "xyz", f"xyz:{item}")
        for item in p1
    )
    requests.extend(
        UniverseRequest(item, RegistryTier.P2, _asset_class(item), "xyz", f"xyz:{item}")
        for item in p2
    )
    return tuple(requests)


def _asset_class(display: str) -> AssetClass:
    if display in {"SILVER", "BRENTOIL", "WTIOIL", "NATGAS", "GOLD"}:
        return AssetClass.COMMODITY
    return AssetClass.EQUITY


INITIAL_40 = _requests()

# Strategy/Product-approved First Launch order.  Selection reuses the already
# verified Manual-40 request objects so provider identities, aliases, tiers,
# and asset classes are inherited rather than re-declared.
FIRST_LAUNCH_20_DISPLAYS = (
    "BTC",
    "ETH",
    "HYPE",
    "SOL",
    "SKHX",
    "MU",
    "SNDK",
    "XYZ100",
    "SP500",
    "WTIOIL",
    "DRAM",
    "SPCX",
    "SILVER",
    "NVDA",
    "SMSN",
    "EWY",
    "GOLD",
    "XRP",
    "TSLA",
    "GOOGL",
)


def _select_requests(displays: tuple[str, ...]) -> tuple[UniverseRequest, ...]:
    catalog = {request.display: request for request in INITIAL_40}
    if len(displays) != len(set(displays)):
        raise ValueError("First-Launch market selection contains duplicates")
    missing = [display for display in displays if display not in catalog]
    if missing:
        raise ValueError("First-Launch market selection is outside Manual-40: " + ", ".join(missing))
    return tuple(catalog[display] for display in displays)


FIRST_LAUNCH_20 = _select_requests(FIRST_LAUNCH_20_DISPLAYS)


def _resolve_requests(
    requests: tuple[UniverseRequest, ...],
    *,
    perp_dexes: object,
    all_perp_metas: object,
    observed_at: datetime,
) -> tuple[Resolution, ...]:
    """Resolve every intended display exactly; never silently choose a DEX."""
    if not isinstance(perp_dexes, list) or not isinstance(all_perp_metas, list):
        raise ValueError("official metadata payloads are invalid")
    if len(perp_dexes) != len(all_perp_metas):
        raise ValueError("official metadata DEX index mismatch")
    records: dict[tuple[str, str], dict[str, object]] = {}
    for index, meta in enumerate(all_perp_metas):
        dex = (
            "MAIN"
            if index == 0
            else (perp_dexes[index].get("name") if isinstance(perp_dexes[index], dict) else None)
        )
        if not isinstance(dex, str) or not isinstance(meta, dict):
            raise ValueError("official metadata DEX identity is invalid")
        universe = meta.get("universe")
        if not isinstance(universe, list):
            raise ValueError("official metadata universe is invalid")
        for raw in universe:
            if isinstance(raw, dict) and isinstance(raw.get("name"), str):
                records[(dex, cast(str, raw["name"]))] = raw
    resolutions: list[Resolution] = []
    for request in requests:
        raw = records.get((request.dex, request.coin))
        if raw is None:
            resolutions.append(Resolution(request, "REGISTRY_IDENTITY_UNRESOLVED", None))
            continue
        if raw.get("isDelisted") is True:
            resolutions.append(
                Resolution(request, "REGISTRY_IDENTITY_UNRESOLVED", None, "DELISTED")
            )
            continue
        try:
            size_decimals = int(cast(int | str, raw["szDecimals"]))
            raw_max_leverage = raw.get("maxLeverage")
            max_leverage = None if raw_max_leverage is None else Decimal(str(raw_max_leverage))
            market = RegistryMarket(
                display=request.display,
                aliases=request.aliases,
                tier=request.tier,
                identity=MarketIdentity.create(dex=request.dex, coin=request.coin),
                asset_class=request.asset_class,
                size_decimals=size_decimals,
                price_max_decimals=6 - size_decimals,
                max_leverage=max_leverage,
                is_hip3=request.dex != "MAIN",
                market_status="ACTIVE",
                metadata_observed_at=observed_at,
                metadata_hash=sha256_hex(canonical_json_bytes(raw)),
            )
        except (KeyError, TypeError, ValueError):
            resolutions.append(
                Resolution(request, "REGISTRY_METADATA_VALIDATION_UNAVAILABLE", None)
            )
            continue
        resolutions.append(Resolution(request, "RESOLVED", market))
    return tuple(resolutions)


def resolve_initial_40(
    *, perp_dexes: object, all_perp_metas: object, observed_at: datetime
) -> tuple[Resolution, ...]:
    """Resolve the retained Manual-40 catalog against official metadata."""
    return _resolve_requests(
        INITIAL_40,
        perp_dexes=perp_dexes,
        all_perp_metas=all_perp_metas,
        observed_at=observed_at,
    )


def resolve_first_launch_20(
    *, perp_dexes: object, all_perp_metas: object, observed_at: datetime
) -> tuple[Resolution, ...]:
    """Resolve the Strategy/Product-approved First-Launch-20 selection."""
    return _resolve_requests(
        FIRST_LAUNCH_20,
        perp_dexes=perp_dexes,
        all_perp_metas=all_perp_metas,
        observed_at=observed_at,
    )
