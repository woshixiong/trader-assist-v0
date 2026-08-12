"""Operator-only Registry commands. No network, account, or exchange-write surface."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from trader_assist_v0.multi_asset_shadow.models import RegistryVersion
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager


def _manager(root: Path) -> MarketRegistryManager:
    # Validation binds the candidate's identity/hash.  Production wiring supplies
    # a fresh official metadata validator before stage/apply.
    return MarketRegistryManager(root, metadata_validator=lambda _: True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("command", choices=("validate", "stage", "status", "apply", "rollback"))
    parser.add_argument("--file", type=Path)
    parser.add_argument("--version")
    arguments = parser.parse_args()
    manager = _manager(arguments.root)
    if arguments.command == "status":
        active = manager.active()
        print("NONE" if active is None else active.model_dump_json())
        return 0
    if arguments.command in {"validate", "stage"}:
        if arguments.file is None:
            parser.error("--file is required")
        candidate = RegistryVersion.model_validate_json(arguments.file.read_text(encoding="utf-8"))
        if arguments.command == "validate":
            manager.validate(candidate)
        else:
            manager.stage(candidate)
        return 0
    if arguments.version is None:
        parser.error("--version is required")
    manager.apply(arguments.version, now=datetime.now(UTC).replace(second=0, microsecond=0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
