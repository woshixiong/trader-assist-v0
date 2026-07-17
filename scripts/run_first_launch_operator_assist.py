"""Run the explicit, default-off public ETH operator-assist session."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from trader_assist_v0.runtime import OperatorAssistError, run_first_launch_operator_assist


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one public ETH operator-assist session.")
    parser.add_argument("--permit", required=True, type=Path)
    parser.add_argument("--shadow-output", required=True, type=Path)
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    try:
        result = asyncio.run(
            run_first_launch_operator_assist(
                permit_path=arguments.permit,
                shadow_output=arguments.shadow_output,
            )
        )
    except OperatorAssistError as exc:
        print(f"NOT_SUBMITTED SESSION STOPPED: {exc}", file=sys.stderr)
        return 1
    print("NOT_SUBMITTED SHADOW RECORD")
    print(f"RECORD {result.record_hash}")
    print(f"SHADOW {result.shadow_order_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
