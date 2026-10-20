"""Small admission contracts over native metadata and already-closed native bars.

Transport, subscription recovery, aggregation and persistence remain Nautilus's.
Only the existing approved registry may supply provider coins; IDs and precision
come from actual native instruments, never symbol concatenation.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.resolution import FIRST_LAUNCH_20

from .contracts import MarketExpression, PitUniverseSnapshot

STREAM_AGES = {"quote": 30, "trade": 60, "book": 30, "1m": 120, "5m": 360}


def validate_coins(coins: tuple[str, ...]) -> None:
    allowed = {item.coin for item in FIRST_LAUNCH_20}
    if len(set(coins)) != len(coins) or not set(coins) <= allowed:
        raise ValueError("provider coins must be unique members of the approved registry")
    if "ETH" not in coins or not any(":" in coin for coin in coins):
        raise ValueError("approved universe requires ETH and an existing HIP-3 RWA")


class NativeUniverse:
    def __init__(self, coins: tuple[str, ...], snapshot: PitUniverseSnapshot | None) -> None:
        validate_coins(coins)
        self.coins = coins
        self.snapshot = snapshot
        self.resolved: dict[str, MarketExpression] = {}

    def admit(self, instrument: Any) -> MarketExpression | None:
        coin = str(instrument.raw_symbol)
        if coin not in self.coins:
            return None
        if str(instrument.id.venue) != "HYPERLIQUID":
            raise ValueError("native provider venue mismatch")
        if self.snapshot is not None:
            expected = next(e for e in self.snapshot.expressions if e.provider_coin == coin)
            if str(instrument.id) != expected.instrument_id:
                raise ValueError("native provider metadata identity mismatch")
        dex = coin.split(":", 1)[0] if ":" in coin else "MAIN"
        metadata = json.dumps(instrument.to_dict(), sort_keys=True, separators=(",", ":"))
        expression = MarketExpression(
            market_id=sha256_hex(f"HYPERLIQUID|{dex}|{coin}".encode()),
            dex=dex,
            provider_coin=coin,
            instrument_id=str(instrument.id),
            expression_id=f"rc7-{coin}",
            instrument_metadata_version="NATIVE_RC7_CURRENT",
            instrument_metadata_hash=sha256_hex(metadata.encode()),
        )
        prior = self.resolved.get(coin)
        if prior is not None and prior.instrument_id != expression.instrument_id:
            raise ValueError("ambiguous native provider identity")
        self.resolved[coin] = expression
        return expression

    @property
    def missing(self) -> list[str]:
        return sorted(set(self.coins) - self.resolved.keys())

    def current_snapshot(self, *, now_ns: int) -> PitUniverseSnapshot:
        if self.missing:
            raise ValueError(f"PROVIDER_METADATA_MISSING:{self.missing}")
        return PitUniverseSnapshot.create(
            observed_at_ns=now_ns,
            expressions=tuple(self.resolved[coin] for coin in self.coins),
        )


def closed_bar_window(event: Any, *, now_ns: int) -> tuple[int, int]:
    """Tagged HL parser uses candle open time; handler emits on period change."""
    minutes = event.bar_type.spec.step
    duration = minutes * 60_000_000_000
    if minutes not in (1, 5) or event.ts_event <= 0 or event.ts_event % duration:
        raise ValueError("INVALID_NATIVE_BAR_PERIOD")
    close_ns = event.ts_event + duration
    if event.ts_init < close_ns or now_ns < event.ts_init:
        raise ValueError("NATIVE_BAR_NOT_CLOSED_OR_FUTURE")
    return event.ts_event // 1_000_000, close_ns // 1_000_000 - 1


def native_event_hash(event: Any) -> str:
    return hashlib.sha256(
        json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
