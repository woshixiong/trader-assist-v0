"""Build a canonical, externally staged Manual-40 Registry seed from public metadata.

The generated file is deliberately not a current-pointer mutation.  An
operator validates and stages it, then separately requests application at a
provider-admitted 5m boundary.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import HyperliquidPublicClient
from trader_assist_v0.multi_asset_shadow.models import RegistryVersion
from trader_assist_v0.multi_asset_shadow.resolution import resolve_initial_40


def build_seed(
    *, version: str, observed_at: datetime, client: HyperliquidPublicClient
) -> RegistryVersion:
    resolutions = resolve_initial_40(
        perp_dexes=client.perp_dexes(),
        all_perp_metas=client.all_perp_metas(),
        observed_at=observed_at,
    )
    unresolved = [item.request.display for item in resolutions if item.market is None]
    if unresolved:
        raise ValueError("initial Registry remains unresolved: " + ", ".join(unresolved))
    markets = tuple(item.market for item in resolutions if item.market is not None)
    if len(markets) != 40:
        raise ValueError("initial Registry must contain exactly 40 markets")
    return RegistryVersion.create(version=version, created_at=observed_at, markets=markets)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    seed = build_seed(
        version=arguments.version,
        observed_at=datetime.now(UTC),
        client=HyperliquidPublicClient(),
    )
    arguments.output.write_bytes(canonical_json_bytes(seed.model_dump(mode="json")))
    print(seed.content_hash)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
