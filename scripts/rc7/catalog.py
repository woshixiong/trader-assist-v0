"""Explicit native recovery or deterministic quote replay of a stopped run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trader_assist_v0.nautilus_e4.native_catalog import recover_and_promote, replay_catalog_quotes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("recover", "replay"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--backtest-input", action="store_true")
    args = parser.parse_args()
    operation = recover_and_promote if args.action == "recover" else replay_catalog_quotes
    print(
        json.dumps(operation(args.root, args.instance_id, live=not args.backtest_input), indent=2)
    )


if __name__ == "__main__":
    main()
