"""Append-only strategy-neutral evidence, not an OMS or matching engine.

Native Sandbox owns orders, fills, accounts and positions. The ledger records
its facts plus *all* strategy decisions, including those that never submit.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


class ShadowLedger:
    def __init__(self, path: Path, *, strategy_id: str, strategy_version: str) -> None:
        if not strategy_id or not strategy_version:
            raise ValueError("strategy identity and version are required")
        self.strategy_id = strategy_id
        self.strategy_version = strategy_version
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL,
                kind TEXT NOT NULL, payload TEXT NOT NULL,
                previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS immutable_update BEFORE UPDATE ON events
                BEGIN SELECT RAISE(ABORT, 'immutable ledger'); END;
            CREATE TRIGGER IF NOT EXISTS immutable_delete BEFORE DELETE ON events
                BEGIN SELECT RAISE(ABORT, 'immutable ledger'); END;
        """)
        self.verify()

    def append(self, *, event_id: str, kind: str, ts_ns: int, payload: dict[str, Any]) -> str:
        if not event_id or not kind or ts_ns <= 0:
            raise ValueError("event identity/kind/time required")
        envelope = {
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "provenance": "SIMULATED_SANDBOX",
            "ts_ns": ts_ns,
            "payload": payload,
        }
        raw = json.dumps(envelope, sort_keys=True, separators=(",", ":"), allow_nan=False)
        # Serialize append identity/hash and insertion under one database write lock.
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            duplicate = self.db.execute(
                "SELECT kind,payload,event_hash FROM events WHERE event_id=?", (event_id,)
            ).fetchone()
            if duplicate:
                if duplicate[:2] != (kind, raw):
                    raise ValueError("conflicting immutable event identity")
                return str(duplicate[2])
            prior = self.db.execute("SELECT event_hash FROM events ORDER BY sequence DESC LIMIT 1")
            last = prior.fetchone()
            previous = "0" * 64 if last is None else last[0]
            digest = hashlib.sha256(f"{previous}|{event_id}|{kind}|{raw}".encode()).hexdigest()
            self.db.execute(
                "INSERT INTO events(event_id,kind,payload,previous_hash,event_hash) "
                "VALUES(?,?,?,?,?)",
                (event_id, kind, raw, previous, digest),
            )
        return digest

    def decision(
        self,
        *,
        decision_id: str,
        ts_ns: int,
        source_identity: str,
        source_ts_ns: int,
        outcome: str,
        details: dict[str, Any],
    ) -> str:
        if not source_identity or not 0 < source_ts_ns <= ts_ns:
            raise ValueError("decision requires causal source identity/time")
        if outcome not in {"SUBMIT", "REJECT", "WAIT", "PASS", "UNFILLED", "LOST"}:
            raise ValueError("unclassified decision outcome")
        return self.append(
            event_id=f"decision:{decision_id}",
            kind="DECISION",
            ts_ns=ts_ns,
            payload={
                "source_identity": source_identity,
                "source_ts_ns": source_ts_ns,
                "outcome": outcome,
                "details": details,
            },
        )

    def native_event(self, event: Any) -> str:
        payload = event.to_dict()
        return self.append(
            event_id=str(event.event_id),
            kind=type(event).__name__,
            ts_ns=event.ts_init,
            payload=payload,
        )

    def verify(self) -> int:
        previous = "0" * 64
        count = 0
        for event_id, kind, payload, link, digest in self.db.execute(
            "SELECT event_id,kind,payload,previous_hash,event_hash FROM events ORDER BY sequence"
        ):
            expected = hashlib.sha256(
                f"{previous}|{event_id}|{kind}|{payload}".encode()
            ).hexdigest()
            if link != previous or digest != expected:
                raise ValueError("corrupt immutable shadow ledger")
            previous = digest
            count += 1
        return count

    def close(self) -> None:
        self.db.close()
