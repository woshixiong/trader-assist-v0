# mypy: disable-error-code="import-not-found"
"""Build the canonical First-Launch-20 Registry seed from public metadata.

The generated file is deliberately not a current-pointer mutation.  An
operator validates and stages it, then separately requests application at a
provider-admitted 5m boundary.
"""

from __future__ import annotations

import argparse
import asyncio
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import HyperliquidPublicClient
from trader_assist_v0.multi_asset_shadow.models import RegistryVersion
from trader_assist_v0.multi_asset_shadow.resolution import resolve_first_launch_20
from trader_assist_v0.nautilus_e4.contracts import PitUniverseSnapshot, RunManifest


def build_seed(
    *, version: str, observed_at: datetime, client: HyperliquidPublicClient
) -> RegistryVersion:
    resolutions = resolve_first_launch_20(
        perp_dexes=client.perp_dexes(),
        all_perp_metas=client.all_perp_metas(),
        observed_at=observed_at,
    )
    unresolved = [item.request.display for item in resolutions if item.market is None]
    if unresolved:
        raise ValueError("First-Launch Registry remains unresolved: " + ", ".join(unresolved))
    markets = tuple(item.market for item in resolutions if item.market is not None)
    if len(markets) != 20:
        raise ValueError("First-Launch Registry must contain exactly 20 markets")
    return RegistryVersion.create(version=version, created_at=observed_at, markets=markets)


def build_launch_identity(
    *,
    seed: RegistryVersion,
    instruments: list[Any],
    sha: str,
    tree: str,
    run_id: str,
    observed_at_ns: int,
    metadata_evidence: dict[str, object],
) -> tuple[PitUniverseSnapshot, RunManifest]:
    """Bind canonical resolution to actual rc5 provider instrument objects."""
    from scripts.e4_nautilus_public_data_probe import L0_PROFILE, launch_bars
    from trader_assist_v0.nautilus_e4.contracts import (
        MarketExpression,
        PitUniverseSnapshot,
        RunManifest,
    )

    expressions = []
    for market in seed.markets:
        matches = [
            i for i in instruments if str(getattr(i, "raw_symbol", "")) == market.identity.coin
        ]
        if len(matches) != 1:
            raise ValueError(f"provider mapping unresolved/ambiguous: {market.display}")
        instrument = matches[0]
        expressions.append(
            MarketExpression(
                market_id=market.identity.market_id,
                dex=market.identity.dex,
                provider_coin=market.identity.coin,
                instrument_id=str(instrument.id),
                expression_id=f"l0-{market.identity.market_id[:20]}",
                instrument_metadata_version="L0_OFFICIAL_CURRENT_METADATA_V1",
                instrument_metadata_hash=market.metadata_hash,
            )
        )
    snapshot = PitUniverseSnapshot.create(
        observed_at_ns=observed_at_ns, expressions=tuple(expressions)
    )
    bars = launch_bars(seed, snapshot)
    ids = sorted(e.market_id for e in snapshot.expressions)
    manifest = RunManifest.create(
        run_id=run_id,
        git_sha=sha,
        git_tree=tree,
        snapshot=snapshot,
        process_epoch=f"{run_id}.process",
        continuity_epoch=f"{run_id}.continuity",
        admission_epoch=f"{run_id}.admission",
        trial_ledger_id="l0-first-launch-20",
        capture_configuration={
            "profile": L0_PROFILE,
            "registry_hash": seed.content_hash,
            "bar_types": list(bars),
            "metadata_evidence": metadata_evidence,
            "expressions": [e.model_dump(mode="json") for e in snapshot.expressions],
        },
        subscription_policy={"discovery": ids, "watch": ids, "actionable": []},
    )
    return snapshot, manifest


async def _provider_instruments() -> list[Any]:
    from nautilus_trader.adapters.hyperliquid import (
        HyperliquidHttpClient,
    )

    from trader_assist_v0.nautilus_e4.host import assert_exact_nautilus_version

    assert_exact_nautilus_version()
    client = HyperliquidHttpClient()
    result = client.load_instrument_definitions(
        include_spot=False, include_perps=True, include_perps_hip3=True
    )
    if hasattr(result, "__await__"):
        result = await result
    return list(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--launch-output", type=Path)
    parser.add_argument("--expected-sha")
    parser.add_argument("--expected-tree")
    parser.add_argument("--run-id")
    arguments = parser.parse_args()
    seed = build_seed(
        version=arguments.version,
        observed_at=datetime.now(UTC),
        client=HyperliquidPublicClient(),
    )
    if arguments.launch_output is not None:
        if not all((arguments.expected_sha, arguments.expected_tree, arguments.run_id)):
            parser.error("launch output requires exact SHA/tree/run-id")
        root = arguments.launch_output
        if root.exists():
            raise ValueError("launch artifact root already exists")
        snapshot, manifest = build_launch_identity(
            seed=seed,
            instruments=asyncio.run(_provider_instruments()),
            sha=arguments.expected_sha,
            tree=arguments.expected_tree,
            run_id=arguments.run_id,
            observed_at_ns=time.time_ns(),
            metadata_evidence={
                "registry_metadata_hashes": [m.metadata_hash for m in seed.markets],
                "provider_instrument_cohort_weight": "UNKNOWN_REQUIRES_TARGET_PROOF",
            },
        )
        from scripts.e4_nautilus_public_data_probe import launch_bars
        from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
        from trader_assist_v0.nautilus_e4.storage import EvidenceStore

        EvidenceStore(root / "e4").initialize(manifest, snapshot)
        registry = MarketRegistryManager(
            root / "registry", metadata_validator=lambda m: m in seed.markets
        )
        registry.stage(seed)
        registry.request_apply(seed.version)
        (root / "bar-types.json").write_bytes(
            canonical_json_bytes(list(launch_bars(seed, snapshot)))
        )
        (root / "registry-seed.json").write_bytes(
            canonical_json_bytes(seed.model_dump(mode="json"))
        )
    arguments.output.write_bytes(canonical_json_bytes(seed.model_dump(mode="json")))
    print(seed.content_hash)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
