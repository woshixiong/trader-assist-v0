from __future__ import annotations

import shutil
import sqlite3
import subprocess
import time
from pathlib import Path

import pytest
from test_three_setup_operator_contracts import make_config, make_source

from trader_assist_v0.multi_asset_shadow.shadow_records.records import ProvenanceRecord
from trader_assist_v0.multi_asset_shadow.shadow_records.store import (
    EvidenceStore,
    ReadOnlyEvidenceSnapshot,
)
from trader_assist_v0.operator.approval import OperatorBlocked, OperatorEngine


def _runtime_write(path: Path, identity: str) -> None:
    record = ProvenanceRecord.create(
        identity={"isolation": identity},
        strategy_version="s",
        parameter_version="p",
        registry_version="r",
        registry_hash="h",
        cost_model_version="c",
        release_sha="sha",
        recorded_at="2026-01-01T00:00:00Z",
    )
    with EvidenceStore(path) as store:
        assert store.write((record,)) == (True,)


def test_runtime_connection_is_read_only_and_operator_lock_is_independent(tmp_path: Path) -> None:
    make_source(tmp_path / "runtime.sqlite", created_ms=time.time_ns() // 1_000_000)
    config = make_config(tmp_path)
    with ReadOnlyEvidenceSnapshot(config.runtime_evidence_path) as source:
        with pytest.raises(sqlite3.OperationalError):
            source._connection.execute("CREATE TABLE illicit_write (id INTEGER)")
    engine = OperatorEngine(config)
    projection, _ = engine.latest()
    operator_writer = sqlite3.connect(config.operator_ledger_path, timeout=0.1)
    operator_writer.execute("BEGIN IMMEDIATE")
    try:
        _runtime_write(config.runtime_evidence_path, "operator-writer-held")
        with pytest.raises(OperatorBlocked):
            engine.human_action(
                shadow_id=projection.package.parent_strategy_order_id,
                package_id=projection.package.package_id,
                package_hash=projection.package.package_hash,
                action_key="busy-action-123456789",
                action="REJECT",
                session_id="session",
            )
    finally:
        operator_writer.rollback()
        operator_writer.close()


def test_operator_corruption_and_process_death_do_not_stop_runtime_writer(tmp_path: Path) -> None:
    make_source(tmp_path / "runtime.sqlite", created_ms=time.time_ns() // 1_000_000)
    config = make_config(tmp_path)
    config.operator_ledger_path.write_bytes(b"not a database")
    with pytest.raises(OperatorBlocked):
        OperatorEngine(config).latest()
    _runtime_write(config.runtime_evidence_path, "after-operator-corruption")
    config.operator_ledger_path.unlink()
    OperatorEngine(config).latest()
    process = subprocess.run(
        (
            shutil.which("python") or "python",
            "-c",
            "import os, sqlite3, sys; c=sqlite3.connect(sys.argv[1]); "
            "c.execute('BEGIN IMMEDIATE'); os._exit(9)",
            str(config.operator_ledger_path),
        ),
        check=False,
    )
    assert process.returncode == 9
    _runtime_write(config.runtime_evidence_path, "after-operator-death")


def test_runtime_read_failure_blocks_operator_without_source_write(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    with pytest.raises(OperatorBlocked):
        OperatorEngine(config).latest()
    assert not config.runtime_evidence_path.exists()


def test_guard_is_called_before_operator_write_transaction(tmp_path: Path) -> None:
    make_source(tmp_path / "runtime.sqlite", created_ms=time.time_ns() // 1_000_000)
    config = make_config(tmp_path)
    def guard_reader(_source: ReadOnlyEvidenceSnapshot, _projection: object) -> None:
        connection = sqlite3.connect(config.operator_ledger_path, timeout=0.1)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.rollback()
        finally:
            connection.close()
        return None
    engine = OperatorEngine(config, guard_reader=guard_reader)
    projection, _ = engine.latest()
    assert engine.human_action(
        shadow_id=projection.package.parent_strategy_order_id,
        package_id=projection.package.package_id,
        package_hash=projection.package.package_hash,
        action_key="guard-before-write-1234", action="APPROVE",
        session_id="s",
    ) == "NO_SUBMIT"
