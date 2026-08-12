"""Thin, public-read-only Hyperliquid `/info` adapter.

The adapter deliberately exposes only the provider's public information and
market-data requests needed by the multi-asset Shadow route.  It has no user,
wallet, signing, exchange, order, or mutation operation.
"""

from __future__ import annotations

import json
import ssl
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

from .models import RegistryMarket

INFO_URL = "https://api.hyperliquid.xyz/info"
_ALLOWED_TYPES = frozenset(
    {"perpDexs", "allPerpMetas", "meta", "metaAndAssetCtxs", "candleSnapshot", "l2Book"}
)


class PublicDataError(RuntimeError):
    pass


class HttpPost(Protocol):
    def __call__(self, url: str, body: bytes, timeout_seconds: float) -> bytes: ...


def _default_post(url: str, body: bytes, timeout_seconds: float) -> bytes:
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(
            request, timeout=timeout_seconds, context=ssl.create_default_context()
        ) as response:
            return cast(bytes, response.read())
    except (HTTPError, URLError, TimeoutError, ssl.SSLError) as exc:
        raise PublicDataError("official public API request failed") from exc


@dataclass(frozen=True)
class HyperliquidPublicClient:
    """Provider-native public transport with a narrow allowlist of request shapes."""

    post: HttpPost = _default_post
    timeout_seconds: float = 15.0

    def request(self, payload: Mapping[str, object]) -> object:
        request_type = payload.get("type")
        if request_type not in _ALLOWED_TYPES or not self._is_supported_shape(payload):
            raise PublicDataError("public request is outside the approved market-data surface")
        raw = self.post(
            INFO_URL,
            json.dumps(dict(payload), separators=(",", ":")).encode(),
            self.timeout_seconds,
        )
        try:
            return json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PublicDataError("official public API returned invalid JSON") from exc

    @staticmethod
    def _is_supported_shape(payload: Mapping[str, object]) -> bool:
        request_type = payload.get("type")
        if request_type == "perpDexs":
            return set(payload) == {"type"}
        if request_type == "allPerpMetas":
            return set(payload) == {"type"}
        if request_type in {"meta", "metaAndAssetCtxs"}:
            return set(payload) <= {"type", "dex"} and isinstance(payload.get("dex", ""), str)
        if request_type == "candleSnapshot":
            request = payload.get("req")
            return (
                set(payload) == {"type", "req"}
                and isinstance(request, Mapping)
                and set(request) == {"coin", "interval", "startTime", "endTime"}
                and isinstance(request["coin"], str)
                and request["interval"] in {"1m", "5m"}
                and isinstance(request["startTime"], int)
                and isinstance(request["endTime"], int)
            )
        if request_type == "l2Book":
            return set(payload) <= {"type", "coin", "nSigFigs", "mantissa"} and isinstance(
                payload.get("coin"), str
            )
        return False

    def perp_dexes(self) -> object:
        return self.request({"type": "perpDexs"})

    def metadata(self, dex: str) -> object:
        # The official API represents the first/native perp DEX as omitted or
        # empty.  Internal MAIN is deliberately never emitted on the wire.
        payload: dict[str, object] = {"type": "meta"}
        if dex != "":
            payload["dex"] = dex
        return self.request(payload)

    def metadata_and_context(self, dex: str) -> object:
        payload: dict[str, object] = {"type": "metaAndAssetCtxs"}
        if dex != "":
            payload["dex"] = dex
        return self.request(payload)

    def all_perp_metas(self) -> object:
        return self.request({"type": "allPerpMetas"})

    def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
        return self.request(
            {
                "type": "candleSnapshot",
                "req": {
                    "coin": coin,
                    "interval": interval,
                    "startTime": start_ms,
                    "endTime": end_ms,
                },
            }
        )

    def l2_book(self, *, coin: str) -> object:
        return self.request({"type": "l2Book", "coin": coin})


class OfficialMetadataValidator:
    """One bounded official metadata snapshot for Registry identity validation."""

    def __init__(self, client: HyperliquidPublicClient) -> None:
        self._client = client
        self._records: dict[tuple[str, str], dict[str, object]] | None = None

    def _load(self) -> dict[tuple[str, str], dict[str, object]]:
        if self._records is not None:
            return self._records
        try:
            dexes = self._client.perp_dexes()
            metas = self._client.all_perp_metas()
        except PublicDataError:
            raise
        if not isinstance(dexes, list) or not isinstance(metas, list) or len(dexes) != len(metas):
            raise PublicDataError("official metadata response has incompatible DEX indexes")
        records: dict[tuple[str, str], dict[str, object]] = {}
        for index, meta in enumerate(metas):
            dex = (
                "MAIN"
                if index == 0
                else (dexes[index].get("name") if isinstance(dexes[index], dict) else None)
            )
            if not isinstance(dex, str) or not isinstance(meta, dict):
                raise PublicDataError("official metadata response has invalid DEX identity")
            universe = meta.get("universe")
            if not isinstance(universe, list):
                raise PublicDataError("official metadata response has invalid universe")
            for raw in universe:
                if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
                    raise PublicDataError("official metadata response has invalid market")
                records[(dex, raw["name"])] = raw
        self._records = records
        return records

    def __call__(self, market: RegistryMarket) -> bool:
        raw = self._load().get((market.identity.dex, market.identity.coin))
        if raw is None:
            return False
        try:
            return (
                market.metadata_hash == sha256_hex(canonical_json_bytes(raw))
                and raw.get("szDecimals") == market.size_decimals
                and Decimal(str(raw.get("maxLeverage"))) == market.max_leverage
                and market.price_max_decimals == 6 - market.size_decimals
            )
        except (ArithmeticError, TypeError, ValueError):
            return False
