"""Operator Registry control plane; public metadata only and no clock activation."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from trader_assist_v0.multi_asset_shadow.hyperliquid_public import (
    HyperliquidPublicClient,
    OfficialMetadataValidator,
)
from trader_assist_v0.multi_asset_shadow.models import (
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager


def _manager(root: Path) -> MarketRegistryManager:
    # Staging performs a bounded all-perp-metadata identity check.  Atomic
    # activation later relies on the immutable validation evidence, not a
    # fragile network call at the 5m boundary.
    return MarketRegistryManager(
        root,
        metadata_validator=OfficialMetadataValidator(HyperliquidPublicClient()),
    )


def _candidate(path: Path) -> RegistryVersion:
    return RegistryVersion.model_validate_json(path.read_text(encoding="utf-8"))


def _market(path: Path) -> RegistryMarket:
    return RegistryMarket.model_validate_json(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument(
        "command",
        choices=(
            "validate",
            "stage",
            "status",
            "apply",
            "rollback",
            "add",
            "remove",
            "enable",
            "disable",
            "tier",
        ),
    )
    parser.add_argument("--file", type=Path)
    parser.add_argument("--version")
    parser.add_argument("--market-id")
    parser.add_argument("--tier", choices=tuple(item.value for item in RegistryTier))
    arguments = parser.parse_args()
    manager = _manager(arguments.root)
    if arguments.command == "status":
        active = manager.active()
        pending = manager.pending_version()
        print(
            json.dumps(
                {
                    "active": None
                    if active is None
                    else {"version": active.version, "hash": active.content_hash},
                    "pending": None
                    if pending is None
                    else {"version": pending.version, "hash": pending.content_hash},
                    "markets": []
                    if active is None
                    else [
                        {
                            "display": item.display,
                            "tier": item.tier.value,
                            "lifecycle": item.lifecycle.value,
                        }
                        for item in active.markets
                    ],
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    if arguments.command in {"validate", "stage"}:
        if arguments.file is None:
            parser.error("--file is required")
        candidate = _candidate(arguments.file)
        if arguments.command == "validate":
            manager.validate(candidate)
        else:
            manager.stage(candidate)
        return 0
    if arguments.command == "add":
        if arguments.file is None or arguments.version is None:
            parser.error("--file (one RegistryMarket) and --version are required")
        candidate = manager.add_new(
            version=arguments.version, now=datetime.now(UTC), market=_market(arguments.file)
        )
        print(candidate.model_dump_json())
        return 0
    if arguments.command in {"apply", "rollback"}:
        if arguments.version is None:
            parser.error("--version is required")
        # This records an eligible pending version only.  The data runtime must
        # call apply_at_closed_5m with an admitted provider bar.
        candidate = (
            manager.rollback_request(arguments.version)
            if arguments.command == "rollback"
            else manager.request_apply(arguments.version)
        )
        print(candidate.model_dump_json())
        return 0
    if arguments.version is None or arguments.market_id is None:
        parser.error("--version and --market-id are required")
    active = manager.active()
    if active is None:
        parser.error("an active Registry is required")
    current = next((m for m in active.markets if m.identity.market_id == arguments.market_id), None)
    if current is None:
        parser.error("unknown --market-id")
    if arguments.command == "remove":
        lifecycle = MarketLifecycle.DRAINING
    elif arguments.command == "enable":
        lifecycle = MarketLifecycle.WARMING
    elif arguments.command == "disable":
        lifecycle = (
            MarketLifecycle.DRAINING
            if current.lifecycle is MarketLifecycle.ACTIVE
            else MarketLifecycle.DISABLED
        )
    elif arguments.command == "tier":
        if arguments.tier is None:
            parser.error("--tier is required")
        markets = tuple(
            m.model_copy(update={"tier": RegistryTier(arguments.tier)}) if m == current else m
            for m in active.markets
        )
        candidate = RegistryVersion.create(
            version=arguments.version, created_at=datetime.now(UTC), markets=markets
        )
        manager.stage(candidate)
        print(candidate.model_dump_json())
        return 0
    else:
        parser.error("add requires --file")
    candidate = manager.lifecycle_update(
        arguments.version,
        arguments.market_id,
        lifecycle,
        now=datetime.now(UTC),
    )
    print(candidate.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
