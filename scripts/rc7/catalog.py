"""Explicit native recovery or deterministic quote replay of a stopped run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trader_assist_v0.nautilus_e4.native_catalog import (
    read_staged_run,
    recover_and_promote,
    replay_catalog_quotes,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("stage", "recover", "replay"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--backtest-input", action="store_true")
    args = parser.parse_args()
    if args.action == "stage":
        if args.backtest_input:
            parser.error("stage reads a native live run")
        print(json.dumps(read_staged_run(args.root, args.instance_id), indent=2))
        return
    operation = recover_and_promote if args.action == "recover" else replay_catalog_quotes
    print(
        json.dumps(operation(args.root, args.instance_id, live=not args.backtest_input), indent=2)
    )


if __name__ == "__main__":
    main()
