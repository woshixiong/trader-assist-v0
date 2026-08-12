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
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

INFO_URL = "https://api.hyperliquid.xyz/info"
_ALLOWED_TYPES = frozenset({"perpDexs", "meta", "metaAndAssetCtxs", "candleSnapshot", "l2Book"})


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
        return self.request({"type": "meta", "dex": dex})

    def metadata_and_context(self, dex: str) -> object:
        return self.request({"type": "metaAndAssetCtxs", "dex": dex})

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
