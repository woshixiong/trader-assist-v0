#!/usr/bin/env python3
"""Bounded public proof, opt-in continuous recording, and offline readback."""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
from pathlib import Path

from trader_assist_v0.hyperliquid_raw_capture import (
    StopIntent,
    capture,
    capture_continuous,
    read_records,
)


async def continuous(output: Path) -> dict[str, object]:
    loop = asyncio.get_running_loop()
    stop = StopIntent()
    installed: list[signal.Signals] = []
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.request)
            installed.append(sig)
        return await capture_continuous(output, stop=stop)
    finally:
        for installed_sig in installed:
            loop.remove_signal_handler(installed_sig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--duration", type=float)
    modes.add_argument("--readback", action="store_true")
    modes.add_argument("--continuous", action="store_true")
    args = parser.parse_args()
    if args.readback:
        print(
            json.dumps(
                {
                    "reopened_records": sum(
                        1 for _ in read_records(sorted(args.output.glob("*.ndjson")))
                    )
                }
            )
        )
        return 0
    if args.continuous:
        result = asyncio.run(continuous(args.output))
        print(json.dumps(result, sort_keys=True))
        return 0
    result = asyncio.run(
        capture(args.output, duration=180 if args.duration is None else args.duration)
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["transport_storage"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
