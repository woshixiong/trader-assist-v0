from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from trader_assist_v0.runtime.eth_public_capture import run_eth_public_capture


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one permit-bounded ETH public Capture")
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--permit", required=True, type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        asyncio.run(
            run_eth_public_capture(
                storage_root=args.storage_root,
                permit_path=args.permit,
                _status=print,
            )
        )
    except BaseException as exc:
        print(f"ERROR {type(exc).__name__}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
