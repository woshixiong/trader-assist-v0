from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from websockets.asyncio.server import serve

from trader_assist_v0 import hyperliquid_raw_capture as raw

STAMP = "2026-10-11T10:00:00.123456Z"
COINS = ["ETH", "builder:SKHX"]


def metadata(request: dict[str, str]) -> Any:
    if request["type"] == "perpDexs":
        return [None, {"name": "builder"}]
    return {"universe": [{"name": "ETH" if request["dex"] == "" else "builder:SKHX"}]}


def test_discovery_uses_provider_namespace_and_rejects_ambiguity() -> None:
    coins, evidence = raw.discover_coins(metadata)
    assert coins == COINS
    assert evidence[-1]["request"] == {"type": "meta", "dex": "builder"}

    def ambiguous(request: dict[str, str]) -> Any:
        result = metadata(request)
        if request.get("dex") == "builder":
            result["universe"].append({"name": "builder:SKHX"})
        return result

    with pytest.raises(ValueError, match="ambiguous"):
        raw.discover_coins(ambiguous)


@pytest.mark.parametrize("channel", raw.CHANNELS)
def test_original_object_receive_timestamp_and_reopen(tmp_path: Path, channel: str) -> None:
    payload: Any = {"coin": COINS[1], "time": 123, "levels": [[{"px": "1.2300"}], []]}
    if channel == "trades":
        payload = [{"coin": COINS[1], "px": "1.2300", "sz": "0.10", "time": 123}]
    message = {"channel": channel, "data": payload}
    with raw.RawWriter(tmp_path) as writer:
        assert raw.record_message(writer, message, STAMP, COINS) == (COINS[1], channel)
    data = [item for item in raw.read_records(writer.paths) if item["kind"] == "data"]
    assert data == [
        {
            "schema_version": 1,
            "kind": "data",
            "channel": channel,
            "venue_coin": COINS[1],
            "received_at_utc": STAMP,
            "raw_payload": message,
        }
    ]


def test_rotation_unique_sessions_and_clean_fsync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    synced: list[int] = []
    fsync = os.fsync

    def observe(fd: int) -> None:
        synced.append(fd)
        fsync(fd)

    monkeypatch.setattr(raw.os, "fsync", observe)
    stamp = [STAMP]
    with raw.RawWriter(tmp_path, max_bytes=1024, clock=lambda: stamp[0]) as writer:
        writer.marker("large", value="x" * 800)
        writer.marker("next")
        stamp[0] = "2026-10-12T00:00:00.000000Z"
        writer.marker("next_day")
    assert len(writer.paths) >= 3
    assert len(synced) == len(writer.paths)
    before = {path: path.read_bytes() for path in writer.paths}
    with raw.RawWriter(tmp_path) as second:
        second.marker("new_session")
    assert all(path.read_bytes() == content for path, content in before.items())
    assert not set(second.paths).intersection(writer.paths)
    events = [record.get("event") for record in raw.read_records(writer.paths)]
    assert events.count("segment_start") == events.count("segment_end") == len(writer.paths)


def test_exclusive_lock_across_processes_and_shutdown_readback(tmp_path: Path) -> None:
    code = """
import sys
from pathlib import Path
from trader_assist_v0.hyperliquid_raw_capture import RawWriter
with RawWriter(Path(sys.argv[1])) as writer:
    writer.marker('child_saved')
"""
    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}
    with raw.RawWriter(tmp_path):
        child = subprocess.run(
            [sys.executable, "-c", code, str(tmp_path)],
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert child.returncode != 0
        assert "BlockingIOError" in child.stderr
    child = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert child.returncode == 0, child.stderr
    records = list(raw.read_records(sorted(tmp_path.glob("*.ndjson"))))
    assert any(record.get("event") == "child_saved" for record in records)
    assert all(record["clean"] for record in records if record.get("event") == "stop")


def test_write_failure_stops_without_reconnect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with raw.RawWriter(tmp_path) as writer:

        def disk_full(record: dict[str, Any]) -> None:
            raise OSError("disk full")

        with monkeypatch.context() as scoped:
            scoped.setattr(writer, "_line", disk_full)
            with pytest.raises(OSError, match="disk full"):
                raw.record_message(
                    writer, {"channel": "bbo", "data": {"coin": "ETH"}}, STAMP, COINS
                )
    assert not any(record.get("event") == "reconnect" for record in raw.read_records(writer.paths))


def test_ack_empty_trades_unknown_coin_and_partial_line(tmp_path: Path) -> None:
    with raw.RawWriter(tmp_path) as writer:
        raw.record_message(
            writer,
            {
                "channel": "subscriptionResponse",
                "data": {
                    "method": "subscribe",
                    "subscription": {"coin": COINS[1], "type": "trades"},
                },
            },
            STAMP,
            COINS,
        )
        assert raw.record_message(writer, {"channel": "trades", "data": []}, STAMP, COINS) is None
        with pytest.raises(ValueError, match="unexpected data coin"):
            raw.record_message(writer, {"channel": "bbo", "data": {"coin": "GUESS"}}, STAMP, COINS)
    assert not any(record["kind"] == "data" for record in raw.read_records(writer.paths))
    partial = tmp_path / "partial.ndjson"
    partial.write_text('{"schema_version":1}', encoding="utf-8")
    with pytest.raises(ValueError, match="partial line"):
        list(raw.read_records([partial]))


def test_reconnect_requires_fresh_acks_and_marks_unknown_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coins_and_evidence = raw.discover_coins(metadata)
    monkeypatch.setattr(raw, "discover_coins", lambda: coins_and_evidence)

    async def scenario() -> dict[str, Any]:
        connections = 0

        async def provider(websocket: Any) -> None:
            nonlocal connections
            connections += 1
            for _ in range(6):
                message = json.loads(await websocket.recv())
                await websocket.send(
                    json.dumps({"channel": "subscriptionResponse", "data": message})
                )
            await websocket.send(json.dumps({"channel": "bbo", "data": {"coin": "ETH", "bbo": []}}))
            if connections == 1:
                await websocket.close()
            else:
                await websocket.wait_closed()

        async with serve(provider, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            monkeypatch.setattr(raw, "WS_URL", f"ws://127.0.0.1:{port}")
            return await raw.capture(tmp_path, duration=0.5)

    result = asyncio.run(scenario())
    assert result["transport_storage"] == "PASS"
    assert result["family_coverage"]["builder:SKHX/trades"] == "INCOMPLETE"
    records = list(raw.read_records(sorted(tmp_path.glob("*.ndjson"))))
    assert sum(record.get("event") == "ack" for record in records) == 12
    assert any(
        record.get("event") == "gap" and record["missing"] == "UNKNOWN" for record in records
    )


def test_public_real_receipt_ubuntu(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    explicit = os.environ.get("HYPERLIQUID_RAW_PUBLIC_PROOF") == "1"
    issue_ci = (
        os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("GITHUB_JOB") == "contracts"
        and os.environ.get("GITHUB_HEAD_REF") == "feature/issue-322-rc5-public-raw-p0"
    )
    if not (explicit or issue_ci):
        pytest.skip("bounded public proof is opt-in or exact Issue #322 contracts job")
    assert sys.platform == "linux", "authoritative public proof requires Linux"
    result = asyncio.run(raw.capture(tmp_path, duration=60))
    # Emit only bounded proof, not public raw payloads; preserve canonical CI evidence.
    with capsys.disabled():
        print("I322_PUBLIC_PROOF=" + json.dumps(result, sort_keys=True), flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as output:
            output.write(
                "\nIssue #322 public proof\n```json\n"
                + json.dumps(result, sort_keys=True)
                + "\n```\n"
            )
    assert result["transport_storage"] == "PASS", result
    assert result["reopened_records"] > 0
