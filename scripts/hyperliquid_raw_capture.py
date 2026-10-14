#!/usr/bin/env python3
"""Bounded public proof, opt-in continuous recording, and offline readback."""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
import sys
from pathlib import Path

from trader_assist_v0.hyperliquid_raw_capture import (
    HealthPolicy,
    StopIntent,
    capture,
    capture_continuous,
    failure_exit_status,
    read_records,
)


async def continuous(
    output: Path,
    policy: HealthPolicy | None = None,
) -> dict[str, object]:
    loop = asyncio.get_running_loop()
    stop = StopIntent()
    installed: list[signal.Signals] = []
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.request)
            installed.append(sig)
        return await capture_continuous(output, stop=stop, policy=policy)
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
    parser.add_argument("--eth-depth-seconds", type=float)
    parser.add_argument("--bbo-warning-seconds", type=float)
    args = parser.parse_args()
    if not args.continuous and (
        args.eth_depth_seconds is not None or args.bbo_warning_seconds is not None
    ):
        parser.error("freshness options require --continuous")
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
        policy = HealthPolicy(
            depth_seconds=60 if args.eth_depth_seconds is None else args.eth_depth_seconds,
            bbo_warning_seconds=(
                300 if args.bbo_warning_seconds is None else args.bbo_warning_seconds
            ),
        )
        try:
            policy.validate()
            result = asyncio.run(continuous(args.output, policy))
        except Exception as exc:
            status = failure_exit_status(exc)
            print(f"capture failed: {type(exc).__name__}: {exc}; exit={status}", file=sys.stderr)
            for note in getattr(exc, "__notes__", ()):
                print(note, file=sys.stderr)
            return status
        print(json.dumps(result, sort_keys=True))
        return 0
    result = asyncio.run(
        capture(args.output, duration=180 if args.duration is None else args.duration)
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["transport_storage"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
