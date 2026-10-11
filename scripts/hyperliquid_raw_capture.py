#!/usr/bin/env python3
"""Bounded public proof and offline NDJSON source readback."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from trader_assist_v0.hyperliquid_raw_capture import capture, read_records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=180)
    parser.add_argument("--readback", action="store_true")
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
    result = asyncio.run(capture(args.output, duration=args.duration))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["transport_storage"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
