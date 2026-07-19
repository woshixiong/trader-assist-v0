"""Strict, offline risk-configuration authority for First Launch plans."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, cast

from trader_assist_v0.contracts.common import canonical_json_bytes

CONFIGURATION_HASH_DOMAIN = "trader-assist-v0/first-launch/risk-configuration/v1"
_KEYS = {
    "CONFIGURATION_VERSION",
    "ACCOUNT_EQUITY_USD",
    "RISK_PER_TRADE_PCT",
    "MAX_NOTIONAL_USD",
}
_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_NUMBER = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")


class ConfigurationError(ValueError):
    """Configuration is not an external, exact, usable risk authority."""


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ConfigurationError("CONFIGURATION_DUPLICATE_KEY")
        result[key] = value
    return result


def _constant(_value: str) -> None:
    raise ConfigurationError("CONFIGURATION_NON_FINITE")


def _decimal(value: object, name: str, places: int) -> Decimal:
    if type(value) is not str or _NUMBER.fullmatch(value) is None:
        raise ConfigurationError(f"{name}_MUST_BE_PLAIN_DECIMAL_STRING")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ConfigurationError(f"{name}_INVALID") from exc
    exponent = result.as_tuple().exponent
    if not result.is_finite() or not isinstance(exponent, int) or -exponent > places:
        raise ConfigurationError(f"{name}_PRECISION_INVALID")
    return result


@dataclass(frozen=True)
class RiskConfiguration:
    configuration_version: str
    account_equity_usd: Decimal
    risk_per_trade_pct: Decimal
    max_notional_usd: Decimal | None
    configuration_hash: str

    def __post_init__(self) -> None:
        if (
            type(self.configuration_version) is not str
            or _VERSION.fullmatch(self.configuration_version) is None
        ):
            raise ConfigurationError("CONFIGURATION_VERSION_INVALID")
        equity = _decimal(str(self.account_equity_usd), "ACCOUNT_EQUITY_USD", 2)
        pct = _decimal(str(self.risk_per_trade_pct), "RISK_PER_TRADE_PCT", 4)
        maximum = (
            None
            if self.max_notional_usd is None
            else _decimal(str(self.max_notional_usd), "MAX_NOTIONAL_USD", 2)
        )
        if not Decimal("10.00") <= equity <= Decimal("10000000.00"):
            raise ConfigurationError("ACCOUNT_EQUITY_USD_RANGE_INVALID")
        if not Decimal("0.01") <= pct <= Decimal("2.00"):
            raise ConfigurationError("RISK_PER_TRADE_PCT_RANGE_INVALID")
        if maximum is not None and not Decimal("10.00") <= maximum <= equity * Decimal("25"):
            raise ConfigurationError("MAX_NOTIONAL_USD_RANGE_INVALID")
        expected = self.digest(self.configuration_version, equity, pct, maximum)
        if self.configuration_hash != expected:
            raise ConfigurationError("CONFIGURATION_HASH_INVALID")

    @staticmethod
    def digest(version: str, equity: Decimal, pct: Decimal, maximum: Decimal | None) -> str:
        return hashlib.sha256(
            CONFIGURATION_HASH_DOMAIN.encode()
            + b"\0"
            + canonical_json_bytes(
                {
                    "CONFIGURATION_VERSION": version,
                    "ACCOUNT_EQUITY_USD": str(equity),
                    "RISK_PER_TRADE_PCT": str(pct),
                    "MAX_NOTIONAL_USD": None if maximum is None else str(maximum),
                }
            )
        ).hexdigest()

    @property
    def system_hard_notional_cap(self) -> Decimal:
        return self.account_equity_usd * Decimal("25")

    @property
    def effective_max_notional(self) -> Decimal:
        return (
            self.system_hard_notional_cap
            if self.max_notional_usd is None
            else min(self.max_notional_usd, self.system_hard_notional_cap)
        )

    @classmethod
    def from_json(cls, raw_text: str) -> RiskConfiguration:
        if type(raw_text) is not str:
            raise ConfigurationError("CONFIGURATION_TEXT_INVALID")
        try:
            raw = json.loads(raw_text, object_pairs_hook=_pairs, parse_constant=_constant)
        except (json.JSONDecodeError, ConfigurationError) as exc:
            raise ConfigurationError("CONFIGURATION_JSON_INVALID") from exc
        if type(raw) is not dict or set(raw) != _KEYS:
            raise ConfigurationError("CONFIGURATION_KEYS_INVALID")
        values = cast(dict[str, object], raw)
        version = values["CONFIGURATION_VERSION"]
        if type(version) is not str or _VERSION.fullmatch(version) is None:
            raise ConfigurationError("CONFIGURATION_VERSION_INVALID")
        equity = _decimal(values["ACCOUNT_EQUITY_USD"], "ACCOUNT_EQUITY_USD", 2)
        pct = _decimal(values["RISK_PER_TRADE_PCT"], "RISK_PER_TRADE_PCT", 4)
        configured = values["MAX_NOTIONAL_USD"]
        maximum = None if configured is None else _decimal(configured, "MAX_NOTIONAL_USD", 2)
        return cls(
            str(version), equity, pct, maximum, cls.digest(str(version), equity, pct, maximum)
        )


def load_risk_configuration(raw_text: str) -> RiskConfiguration:
    """Load one exact configuration; callers must not retain authority after failure."""
    return RiskConfiguration.from_json(raw_text)
