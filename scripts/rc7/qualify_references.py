# mypy: disable-error-code="import-not-found"
"""Bounded isolated native provider qualification. No daemon or production restart cycle."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from trader_assist_v0.nautilus_e4.native_archive import observe_archive, require_archive_capacity
from trader_assist_v0.nautilus_e4.native_reference import (
    CANDIDATES,
    ReferenceReader,
    reference_actor,
    reference_proof,
)
from trader_assist_v0.nautilus_e4.native_runtime import build_native_node


async def qualify(root: Path, venue: str, duration: int) -> dict[str, Any]:
    if root.exists():
        raise ValueError("reference qualification requires a fresh isolated root")
    root.mkdir(parents=True)
    reader = ReferenceReader()
    node = build_native_node(root, venues=(venue,))
    node.add_actor(reference_actor(reader, venues=(venue,)))
    instance_id = str(node.instance_id)
    handle = node.handle()
    started = time.monotonic()
    bounded = False
    failure: str | None = None

    async def monitor() -> None:
        nonlocal bounded
        while time.monotonic() - started < duration:
            require_archive_capacity(
                observe_archive(root),
                max_bytes=64 * 1024 * 1024,
                free_bytes=shutil.disk_usage(root).free,
                minimum_free_bytes=reader.health.minimum_free_bytes,
            )
            await asyncio.sleep(1)
        bounded = True
        handle.stop()

    async def stop_on_failure() -> None:
        try:
            await monitor()
        except Exception:
            handle.stop()
            raise

    task = asyncio.create_task(stop_on_failure())
    try:
        await asyncio.wait_for(node.run_async(), timeout=duration + 30)
    except Exception as exc:
        failure = f"{type(exc).__name__}:{exc}"
    finally:
        handle.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            failure = failure or f"{type(exc).__name__}:{exc}"
        try:
            node.dispose()
        except Exception as exc:
            failure = failure or f"{type(exc).__name__}:{exc}"
    result = reader.coverage()
    result.update(
        venue=venue,
        instance_id=instance_id,
        bounded_complete=bounded,
        status="INCOMPLETE",
        external_order_writes=0,
        source_head=os.environ.get("GITHUB_SHA", "UNBOUND"),
    )
    try:
        if failure or not bounded:
            raise RuntimeError(failure or "NATIVE_NODE_STOPPED_EARLY")
        result.update(reference_proof(root, instance_id, reader, required_venues=(venue,)))
    except Exception as exc:
        result["failure"] = f"{type(exc).__name__}:{exc}"
    (root / "reference-proof.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


async def run(args: argparse.Namespace) -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true" or not 65 <= args.duration_seconds <= 90:
        raise ValueError("public reference qualification requires isolated CI and 65..90 seconds")
    results = {}
    for venue in CANDIDATES:
        results[venue] = await qualify(args.root / venue, venue, args.duration_seconds)
    args.root.mkdir(parents=True, exist_ok=True)
    (args.root / "reference-proof.json").write_text(json.dumps(results, indent=2) + "\n")
    print(
        json.dumps(
            {
                v: {
                    "status": r["status"],
                    "qualified": r.get("qualified", {}),
                    "failure": r.get("failure"),
                }
                for v, r in results.items()
            }
        )
    )
    if any(r["status"] != "AVAILABLE_NATIVE_SUBSET_PROVEN" for r in results.values()):
        raise SystemExit("NATIVE_REFERENCE_PUBLIC_QUALIFICATION_INCOMPLETE")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--duration-seconds", type=int, default=75)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
