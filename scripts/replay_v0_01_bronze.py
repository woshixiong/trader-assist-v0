from __future__ import annotations

import argparse
import os
import tempfile
from datetime import date
from pathlib import Path

from trader_assist_v0.data.bronze import BronzeStore
from trader_assist_v0.data.replay import replay_segment
from trader_assist_v0.data.source_catalog import SOURCE_CATALOG_VERSION


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+b", prefix=".report-", suffix=".tmp", dir=path.parent, delete=False
        ) as handle:
            temporary_name = handle.name
            written = handle.write(payload)
            if written != len(payload):
                raise OSError("short derived replay-report write")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify one explicitly finalized offline Bronze segment"
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--date", type=date.fromisoformat, required=True)
    parser.add_argument("--segment", required=True)
    parser.add_argument("--source-catalog-version", default=SOURCE_CATALOG_VERSION)
    parser.add_argument(
        "--expected-terminal-hash",
        help="Optional additional assertion; never replaces the mandatory checkpoint",
    )
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    store = BronzeStore(args.root)
    report = replay_segment(
        store,
        manifest_date=args.date,
        segment_id=args.segment,
        source_catalog_version=args.source_catalog_version,
        expected_terminal_hash=args.expected_terminal_hash,
    )
    encoded = report.model_dump_json(indent=2).encode("utf-8") + b"\n"
    if args.write_report:
        report_path = store.path(f"reports/{args.segment}.replay.json")
        _atomic_write(report_path, encoded)
    print(encoded.decode("utf-8"), end="")
    return 0 if report.status.value == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
