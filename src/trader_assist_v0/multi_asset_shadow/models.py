"""Small, asset-neutral contracts for the multi-asset public data route."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trader_assist_v0.contracts.common import (
    NonNegativeFiniteDecimal,
    PositiveFiniteDecimal,
    Sha256Hex,
    canonical_json_bytes,
    sha256_hex,
)


class RegistryTier(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class AssetClass(StrEnum):
    CRYPTO = "CRYPTO"
    EQUITY = "EQUITY"
    INDEX = "INDEX"
    COMMODITY = "COMMODITY"
    OTHER = "OTHER"


class MarketLifecycle(StrEnum):
    WARMING = "WARMING"
    HISTORY_READY = "HISTORY_READY"
    SNAPSHOT_READY = "SNAPSHOT_READY"
    ACTIVE = "ACTIVE"
    DRAINING = "DRAINING"
    OUTCOMES_COMPLETE = "OUTCOMES_COMPLETE"
    DISABLED = "DISABLED"


class SessionState(StrEnum):
    OPEN_EXTERNAL_REFERENCE_SESSION = "OPEN_EXTERNAL_REFERENCE_SESSION"
    INTERNAL_OR_OFF_REFERENCE_SESSION = "INTERNAL_OR_OFF_REFERENCE_SESSION"
    CLOSED_OR_MAINTENANCE = "CLOSED_OR_MAINTENANCE"
    SESSION_WARNING = "SESSION_WARNING"


class MarketIdentity(BaseModel):
    """Official venue identity, never a presentation alias."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    venue: str = "HYPERLIQUID"
    dex: str = Field(min_length=1, max_length=80)
    coin: str = Field(min_length=1, max_length=80)
    market_id: Sha256Hex

    @staticmethod
    def canonical_market_id(*, dex: str, coin: str) -> str:
        return sha256_hex(f"HYPERLIQUID|{dex}|{coin}".encode())

    @classmethod
    def create(cls, *, dex: str, coin: str) -> MarketIdentity:
        return cls(dex=dex, coin=coin, market_id=cls.canonical_market_id(dex=dex, coin=coin))

    @property
    def provider_dex(self) -> str:
        """Translate the frozen internal native DEX identity at the API edge."""
        return "" if self.dex == "MAIN" else self.dex

    @model_validator(mode="after")
    def validate_identity(self) -> MarketIdentity:
        if (
            self.venue != "HYPERLIQUID"
            or self.dex.strip() != self.dex
            or self.coin.strip() != self.coin
        ):
            raise ValueError("market identity must use exact official venue, DEX, and coin")
        if self.market_id != self.canonical_market_id(dex=self.dex, coin=self.coin):
            raise ValueError("market_id does not bind canonical venue/DEX/coin identity")
        return self


class RegistryMarket(BaseModel):
    """A manually approved market, bound to a verified public metadata snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    display: str = Field(min_length=1, max_length=120)
    aliases: tuple[str, ...] = ()
    tier: RegistryTier
    identity: MarketIdentity
    asset_class: AssetClass
    size_decimals: int = Field(ge=0, le=18)
    # Hyperliquid perps do not publish a fixed tick.  These are the provider
    # rules required to reproduce a legal planned price deterministically.
    price_max_significant_figures: int = Field(default=5, ge=1, le=18)
    price_max_decimals: int = Field(ge=0, le=18)
    max_leverage: Decimal | None = Field(default=None, gt=0, le=200)
    is_hip3: bool
    market_status: str = Field(min_length=1, max_length=80)
    timeframe_profile: str = "FAST_5M"
    lifecycle: MarketLifecycle = MarketLifecycle.WARMING
    growth_mode: str | None = None
    metadata_observed_at: datetime
    metadata_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_market(self) -> RegistryMarket:
        if self.timeframe_profile != "FAST_5M":
            raise ValueError("only FAST_5M is authorized")
        if self.metadata_observed_at.tzinfo is None:
            raise ValueError("metadata_observed_at must be timezone-aware")
        if self.identity.dex == "MAIN" and self.is_hip3:
            raise ValueError("MAIN market cannot be marked HIP-3")
        if self.identity.dex != "MAIN" and not self.is_hip3:
            raise ValueError("non-MAIN market must be marked HIP-3")
        if self.display in self.aliases or len(set(self.aliases)) != len(self.aliases):
            raise ValueError("aliases must be unique presentation metadata")
        return self

    def tick_round(self, price: Decimal, *, rounding: str = "ROUND_DOWN") -> Decimal:
        """Return a legal provider price without pretending a static tick exists.

        Per the official perp rule, a price may have five significant figures
        and at most ``6 - szDecimals`` decimal places; an integer is always
        legal.  Rounding down is deterministic and conservative for the
        planner's displayed entry evidence.
        """
        from decimal import ROUND_DOWN

        if not price.is_finite() or price <= 0:
            raise ValueError("price must be positive and finite")
        if rounding != "ROUND_DOWN":
            raise ValueError("only deterministic ROUND_DOWN is supported")
        decimal_cap = Decimal(1).scaleb(-self.price_max_decimals)
        decimal_limited = price.quantize(decimal_cap, rounding=ROUND_DOWN)
        adjusted = decimal_limited.adjusted()
        significant_quantum = Decimal(1).scaleb(adjusted - self.price_max_significant_figures + 1)
        rounded = decimal_limited.quantize(
            max(decimal_cap, significant_quantum), rounding=ROUND_DOWN
        )
        return rounded


class RegistryVersion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1"
    version: str = Field(min_length=1, max_length=80)
    created_at: datetime
    markets: tuple[RegistryMarket, ...]
    content_hash: Sha256Hex

    @staticmethod
    def hash_payload(
        *, version: str, created_at: datetime, markets: tuple[RegistryMarket, ...]
    ) -> str:
        return sha256_hex(
            canonical_json_bytes(
                {
                    "schema_version": "1",
                    "version": version,
                    "created_at": created_at.astimezone(UTC),
                    "markets": [item.model_dump(mode="json") for item in markets],
                }
            )
        )

    @model_validator(mode="after")
    def validate_version(self) -> RegistryVersion:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        market_ids = [item.identity.market_id for item in self.markets]
        displays = [item.display for item in self.markets]
        presentation_ids = [item.display for item in self.markets] + [
            alias for item in self.markets for alias in item.aliases
        ]
        if len(market_ids) != len(set(market_ids)):
            raise ValueError("duplicate canonical market identity")
        if len(displays) != len(set(displays)):
            raise ValueError("duplicate display name")
        if len(presentation_ids) != len(set(presentation_ids)):
            raise ValueError("display identifiers and aliases must be globally unique")
        expected = self.hash_payload(
            version=self.version, created_at=self.created_at, markets=self.markets
        )
        if self.content_hash != expected:
            raise ValueError("registry content_hash does not bind version contents")
        return self

    @classmethod
    def create(
        cls, *, version: str, created_at: datetime, markets: tuple[RegistryMarket, ...]
    ) -> RegistryVersion:
        return cls(
            version=version,
            created_at=created_at,
            markets=markets,
            content_hash=cls.hash_payload(version=version, created_at=created_at, markets=markets),
        )


class ClosedBar(BaseModel):
    """Normalized authoritative closed candle.  No open candle can enter this type."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    market_id: Sha256Hex
    interval: str = "5m"
    open_time_ms: int = Field(ge=0)
    close_time_ms: int = Field(ge=1)
    open: PositiveFiniteDecimal
    high: PositiveFiniteDecimal
    low: PositiveFiniteDecimal
    close: PositiveFiniteDecimal
    volume: NonNegativeFiniteDecimal
    source_id: str = Field(min_length=1, max_length=120)
    provenance_hash: Sha256Hex
    received_at: datetime
    canonical_hash: Sha256Hex

    @staticmethod
    def hash_payload(payload: dict[str, object]) -> str:
        return sha256_hex(canonical_json_bytes(payload))

    @model_validator(mode="after")
    def validate_bar(self) -> ClosedBar:
        if self.interval not in {"1m", "5m", "15m", "1h"}:
            raise ValueError("unsupported interval")
        if self.close_time_ms <= self.open_time_ms:
            raise ValueError("bar close must follow open")
        if self.high < max(self.open, self.close, self.low) or self.low > min(
            self.open, self.close, self.high
        ):
            raise ValueError("invalid OHLC range")
        if self.received_at.tzinfo is None:
            raise ValueError("received_at must be timezone-aware")
        payload = self.model_dump(mode="json", exclude={"canonical_hash"})
        if self.canonical_hash != self.hash_payload(payload):
            raise ValueError("canonical_hash does not bind closed bar")
        return self

    @classmethod
    def create(
        cls,
        *,
        market_id: str,
        interval: str = "5m",
        open_time_ms: int,
        close_time_ms: int,
        open: Decimal,
        high: Decimal,
        low: Decimal,
        close: Decimal,
        volume: Decimal,
        source_id: str,
        provenance_hash: str,
        received_at: datetime,
    ) -> ClosedBar:
        # Hash the exact JSON representation that validation will later bind;
        # Decimal and datetime Python objects otherwise serialize differently.
        provisional = cls.model_construct(
            market_id=market_id,
            interval=interval,
            open_time_ms=open_time_ms,
            close_time_ms=close_time_ms,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            source_id=source_id,
            provenance_hash=provenance_hash,
            received_at=received_at,
            canonical_hash="0" * 64,
        )
        normalized = provisional.model_dump(mode="json", exclude={"canonical_hash"})
        return cls(
            market_id=market_id,
            interval=interval,
            open_time_ms=open_time_ms,
            close_time_ms=close_time_ms,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            source_id=source_id,
            provenance_hash=provenance_hash,
            received_at=received_at,
            canonical_hash=cls.hash_payload(normalized),
        )
