"""Read-only bounded event-health qualification, never service control."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def validate_report(report: dict[str, object], now: int) -> None:
    generated = report.get("generated_ns")
    if not isinstance(generated, int) or not 0 <= now - generated <= 10_000_000_000:
        raise ValueError("HEALTH_REPORT_STALE_OR_INVALID")
    if report.get("status") != "HEALTHY" or report.get("reasons"):
        raise ValueError("DEGRADED_NATIVE_HEALTH")
    counts = report.get("counts")
    if (
        not isinstance(counts, dict)
        or not counts
        or any(not isinstance(value, int) or value <= 0 for value in counts.values())
    ):
        raise ValueError("MISSING_VALID_NATIVE_EVENTS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--health", type=Path, required=True)
    parser.add_argument("--duration-seconds", type=int, default=86400)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.duration_seconds <= 0:
        parser.error("duration must be positive")
    started = time.monotonic()
    samples = 0
    result = {
        "status": "FAIL",
        "requested_seconds": args.duration_seconds,
        "target_host_24h": False,
    }
    try:
        while True:
            validate_report(json.loads(args.health.read_text()), time.time_ns())
            samples += 1
            elapsed = time.monotonic() - started
            if elapsed >= args.duration_seconds:
                result.update(status="PASS", target_host_24h=args.duration_seconds >= 86400)
                break
            time.sleep(min(5, args.duration_seconds - elapsed))
    except (OSError, ValueError, TypeError) as exc:
        result["reason"] = str(exc)
    finally:
        result.update(samples=samples, elapsed_seconds=time.monotonic() - started)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
