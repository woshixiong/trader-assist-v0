"""Deterministic production-composition acceptance for the Three Setup release."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import sys
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow import production
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.integration import (
    IntegrationError,
    capture_binding_activation,
    eligible_core_binding_formals,
    verify_binding_activation,
)
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.notification_engine import (
    WebhookConfig,
    WebhookDeliveryAdapter,
    WebhookResponse,
)
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.shadow_records import EvidenceStore
from trader_assist_v0.multi_asset_shadow.shadow_records.records import (
    FormalSignal,
    MarketEvent,
    NotificationOutboxReference,
    OutcomeEnvelope,
    OutcomeTransitionEvidence,
    PlanRecord,
    ProvenanceRecord,
    ShadowOrder,
)
from trader_assist_v0.nautilus_e4.capture import SubscriptionPolicy, recover_capture_session
from trader_assist_v0.nautilus_e4.contracts import (
    MarketExpression,
    PitUniverseSnapshot,
    RunManifest,
)
from trader_assist_v0.nautilus_e4.storage import EvidenceStore as E4Store

SHA = "a" * 40


def _insert_immutable_witness_row(store: EvidenceStore, record_id: str, kind: str) -> int:
    with store._connection:
        cursor = store._connection.execute(
            """INSERT INTO immutable_records
               (record_id, record_type, canonical_hash, identity_json, payload_json)
               VALUES (?, ?, ?, '{}', '{}')""",
            (record_id, kind, sha256_hex(record_id.encode())),
        )
    return int(cursor.lastrowid)


def _simulate_external_immutable_corruption(store: EvidenceStore) -> None:
    # Model a store rewrite outside the authorized append-only production path.
    rows = store._connection.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='immutable_records'"
    ).fetchall()
    with store._connection:
        for row in rows:
            name = str(row[0]).replace('"', '""')
            store._connection.execute(f'DROP TRIGGER "{name}"')


def test_binding_activation_all_row_witness_blocks_nonformal_high_water_loss(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "evidence.sqlite")
    _insert_immutable_witness_row(store, "historical-formal", "formal_signal")
    high = _insert_immutable_witness_row(store, "historical-market", "market_event")
    activation = capture_binding_activation(
        store, release_sha=SHA, run_id="run", manifest_hash="manifest",
    )
    assert activation["activation_rowid"] == high
    verify_binding_activation(
        store, activation, release_sha=SHA, run_id="run", manifest_hash="manifest",
    )
    _insert_immutable_witness_row(store, "post-activation", "formal_signal")
    assert store._connection.execute(
        "SELECT record_id FROM immutable_records WHERE record_type='formal_signal' AND rowid > ?",
        (high,),
    ).fetchall()[0][0] == "post-activation"
    _simulate_external_immutable_corruption(store)
    with store._connection:
        store._connection.execute("DELETE FROM immutable_records WHERE rowid=?", (high,))
    with pytest.raises(IntegrationError, match="high-water|witness drift"):
        verify_binding_activation(
            store, activation, release_sha=SHA, run_id="run", manifest_hash="manifest",
        )
    store.close()


@pytest.mark.parametrize("mutation", ("delete_reuse", "rewrite", "hash", "type"))
def test_binding_activation_detects_all_row_rewrites(tmp_path: Path, mutation: str) -> None:
    store = EvidenceStore(tmp_path / "evidence.sqlite")
    _insert_immutable_witness_row(store, "old-formal", "formal_signal")
    high = _insert_immutable_witness_row(store, "old-nonformal", "market_event")
    activation = capture_binding_activation(
        store, release_sha=SHA, run_id="run", manifest_hash="manifest",
    )
    _simulate_external_immutable_corruption(store)
    with store._connection:
        if mutation == "delete_reuse":
            store._connection.execute("DELETE FROM immutable_records WHERE rowid=?", (high,))
        elif mutation == "rewrite":
            store._connection.execute(
                "UPDATE immutable_records SET rowid=rowid+10 WHERE rowid=?", (high,)
            )
        elif mutation == "hash":
            store._connection.execute(
                "UPDATE immutable_records SET canonical_hash=? WHERE rowid=?", ("b" * 64, high)
            )
        else:
            store._connection.execute(
                "UPDATE immutable_records SET record_type=? WHERE rowid=?", ("shadow_order", high)
            )
    if mutation == "delete_reuse":
        _insert_immutable_witness_row(store, "later-crossing-row", "market_event")
    with pytest.raises(IntegrationError, match="high-water|witness drift"):
        verify_binding_activation(
            store, activation, release_sha=SHA, run_id="run", manifest_hash="manifest",
        )
    store.close()


def test_binding_activation_detects_rowid_changing_vacuum(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence.sqlite")
    _insert_immutable_witness_row(store, "first", "market_event")
    _insert_immutable_witness_row(store, "middle", "market_event")
    _insert_immutable_witness_row(store, "highest", "market_event")
    activation = capture_binding_activation(
        store, release_sha=SHA, run_id="run", manifest_hash="manifest",
    )
    _simulate_external_immutable_corruption(store)
    with store._connection:
        store._connection.execute("DELETE FROM immutable_records WHERE record_id='middle'")
    store._connection.execute("VACUUM")
    with pytest.raises(IntegrationError, match="high-water|witness drift"):
        verify_binding_activation(
            store, activation, release_sha=SHA, run_id="run", manifest_hash="manifest",
        )
    store.close()


@pytest.mark.parametrize("field", (
    "release_sha", "run_id", "manifest_hash", "activation_rowid",
    "pre_fence_all_immutable_row_count", "pre_fence_all_immutable_sha256",
))
def test_binding_activation_identity_and_witness_corruption_fails_closed(
    tmp_path: Path, field: str
) -> None:
    store = EvidenceStore(tmp_path / "evidence.sqlite")
    _insert_immutable_witness_row(store, "old-nonformal", "market_event")
    activation = capture_binding_activation(
        store, release_sha=SHA, run_id="run", manifest_hash="manifest",
    )
    activation[field] = -1 if isinstance(activation[field], int) else "corrupt"
    with pytest.raises(IntegrationError):
        verify_binding_activation(
            store, activation, release_sha=SHA, run_id="run", manifest_hash="manifest",
        )
    store.close()


def _commit_test_formal(store: EvidenceStore, *, suffix: str) -> FormalSignal:
    confirmed_at = "1970-01-01T00:16:40Z"
    market_id = _market().identity.market_id
    provenance = ProvenanceRecord.create(
        identity={"test": suffix}, strategy_version="strategy", parameter_version="param",
        registry_version="registry", registry_hash="hash", cost_model_version="cost",
        release_sha=SHA, recorded_at="2026-08-16T00:00:00Z",
    )
    event = MarketEvent.create(
        identity={"test": suffix}, market_id=market_id, event_kind="SWEEP_RECLAIM",
        event_time=confirmed_at, side="LONG",
    )
    signal = FormalSignal.create(
        identity={"test": suffix}, market_event_id=event.record_id,
        market_id=market_id, setup_family="SWEEP_RECLAIM", setup_mode=None,
        side="LONG", approval_status="APPROVED", formalization_status="STRATEGY_ELIGIBLE",
        tier="P0", confirmed_at=confirmed_at,
        provenance_id=provenance.record_id,
    )
    plan = PlanRecord.create(
        identity={"test": suffix}, signal_id=signal.record_id,
        planned_entry="100", stop="99", tp1="102", tp2=None,
        risk_reference_sizing={}, created_at="2026-08-16T00:00:00Z",
        provenance_id=provenance.record_id,
    )
    shadow = ShadowOrder.create(
        identity={"test": suffix}, signal_id=signal.record_id,
        plan_id=plan.record_id, market_event_id=event.record_id,
        market_id=market_id, setup_family="SWEEP_RECLAIM", setup_mode=None,
        side="LONG", planned_entry="100", stop="99", tp1="102", tp2=None,
        risk_reference_sizing={}, provenance_id=provenance.record_id,
        strategy_version="strategy", parameter_version="param", registry_version="registry",
        registry_hash="hash", cost_model_version="cost",
        created_at=confirmed_at, confirmed_at=confirmed_at,
        submission_status="NOT_SUBMITTED",
        outcome_start_ms=1_000_000,
    )
    publication_id = f"publication-{suffix}"
    reference = NotificationOutboxReference.create(
        identity={"signal_id": signal.record_id, "publication_id": publication_id},
        signal_id=signal.record_id, publication_id=publication_id,
        published_at=confirmed_at, outbox_reference=publication_id,
    )
    with store._controlled_transaction():
        for record in (provenance, event, signal, plan, shadow, reference):
            store._write_one(record)
        store._connection.execute(
            """INSERT INTO notification_outbox
               (idempotency_key, schema_version, kind, content, created_at,
                state, next_attempt_at)
               VALUES (?, '1', 'FORMAL_SIGNAL', '{}', ?, 'PENDING', ?)""",
            (publication_id, confirmed_at, confirmed_at),
        )
    return signal


def test_binding_cohort_excludes_same_release_history_and_repairs_postfence_commit(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "evidence.sqlite")
    old = _commit_test_formal(store, suffix="historical")
    activation = capture_binding_activation(
        store, release_sha=SHA, run_id="run", manifest_hash="manifest",
    )
    current = _commit_test_formal(store, suffix="after-activation")
    # Simulate a domain commit followed by E4 bind failure: no E4 fact is
    # written here. Restart reuses the original fence and finds the bundle.
    fence = verify_binding_activation(
        store, activation, release_sha=SHA, run_id="run", manifest_hash="manifest",
    )
    eligible = eligible_core_binding_formals(store, fence=fence, release_sha=SHA)
    assert [item.signal.record_id for item in eligible] == [current.record_id]
    assert old.record_id not in [item.signal.record_id for item in eligible]
    assert [item.signal.record_id for item in eligible_core_binding_formals(
        store, fence=fence, release_sha=SHA,
    )] == [current.record_id]
    store.close()


def test_binding_research_readback_exposes_linked_missingness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, _node, _capture = _e4_composition_fixture(tmp_path, monkeypatch)
    domain = EvidenceStore(config.evidence_store_path)
    assert config.e4_evidence_root is not None
    e4 = E4Store(config.e4_evidence_root)
    manifest, snapshot = e4.load_manifest(), e4.load_snapshot()
    activation = capture_binding_activation(
        domain, release_sha=SHA, run_id=manifest.run_id,
        manifest_hash=manifest.manifest_hash,
    )
    market_id = _market().identity.market_id
    policy = SubscriptionPolicy(
        discovery=frozenset({market_id}), watch=frozenset({market_id}),
        actionable=frozenset({market_id}),
    )
    session = recover_capture_session(
        manifest=manifest,
        policy=policy,
        raw_sink=None, evidence_store=e4,
    )
    session.activate_binding(activation)
    signal = _commit_test_formal(domain, suffix="after-activation")
    formal = eligible_core_binding_formals(
        domain, fence=int(activation["activation_rowid"]), release_sha=SHA,
    )[0]
    # The domain transaction committed but the first E4 bind failed before
    # intent. The original activation survives and startup scans the same row.
    session = recover_capture_session(
        manifest=manifest, policy=policy, raw_sink=None, evidence_store=e4,
    )
    assert session.binding_activation == activation
    session.open_bound_structural_package(
        package_id=f"m1:shadow:{formal.shadow.record_id}",
        opportunity_id=f"m1:event:{formal.market_event.record_id}",
        thesis_id=f"m1:signal:{signal.record_id}",
        market_id=market_id, expression_id=snapshot.expressions[0].expression_id,
        created_ts=1_000_000_000_000, horizon_ns=formal.horizon_ms * 1_000_000,
        release_sha=SHA, contract_id=production.M1_BINDING_CONTRACT,
    )
    session.open_bound_structural_package(
        package_id=f"m1:shadow:{formal.shadow.record_id}",
        opportunity_id=f"m1:event:{formal.market_event.record_id}",
        thesis_id=f"m1:signal:{signal.record_id}",
        market_id=market_id, expression_id=snapshot.expressions[0].expression_id,
        created_ts=1_000_000_000_000, horizon_ns=formal.horizon_ms * 1_000_000,
        release_sha=SHA, contract_id=production.M1_BINDING_CONTRACT,
    )
    assert len(e4.load_lifecycle()) == 2
    app = object.__new__(production.E4ThreeSetupProductionApplication)
    app.capture = SimpleNamespace(
        capture_session=session, binding_activation=session.binding_activation,
        bound_packages=session.bound_packages,
    )
    app.bootstrap = SimpleNamespace(
        evidence=domain, coordinator=SimpleNamespace(_release_sha=SHA),
    )
    readback = app.read_core_binding_research()
    assert len(readback) == 1
    assert readback[0]["formal_signal"]["record_id"] == signal.record_id
    assert readback[0]["missingness"] == "ADMISSIONS_ABSENT"
    assert b'"ADMISSIONS_ABSENT"' in app.export_core_binding_research_jsonl()
    domain.close()


@pytest.mark.parametrize("transition_count", (0, 1, 2))
def test_binding_horizon_rejects_retained_transition_authority(
    tmp_path: Path, transition_count: int
) -> None:
    store = EvidenceStore(tmp_path / "evidence.sqlite")
    activation = capture_binding_activation(
        store, release_sha=SHA, run_id="run", manifest_hash="manifest",
    )
    signal = _commit_test_formal(store, suffix="current")
    shadow_id = store._connection.execute(
        "SELECT record_id FROM shadow_orders WHERE signal_id=?", (signal.record_id,)
    ).fetchone()[0]
    if transition_count:
        with store._controlled_transaction():
            for index in range(transition_count):
                transition = OutcomeTransitionEvidence.create(
                    identity={"index": index}, transition_id=f"transition-{index}",
                    shadow_order_id=shadow_id, market_id=_market().identity.market_id,
                    kind="ACCEPTED_REENTRY", occurred_at_ms=1_100_000 + index,
                    reference_price="100", payload_hash="a" * 64,
                )
                store._write_one(transition)
        with pytest.raises(IntegrationError, match="transition authority changed"):
            eligible_core_binding_formals(
                store, fence=int(activation["activation_rowid"]), release_sha=SHA,
            )
    else:
        assert eligible_core_binding_formals(
            store, fence=int(activation["activation_rowid"]), release_sha=SHA,
        )[0].horizon_ms == 1_000_000 + 120 * 60_000
    store.close()


def test_binding_extended_outcome_fails_closed_without_transition_authority(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence.sqlite")
    activation = capture_binding_activation(
        store, release_sha=SHA, run_id="run", manifest_hash="manifest",
    )
    signal = _commit_test_formal(store, suffix="current")
    shadow_id = store._connection.execute(
        "SELECT record_id FROM shadow_orders WHERE signal_id=?", (signal.record_id,)
    ).fetchone()[0]
    outcome = OutcomeEnvelope.create(
        identity={"test": "extended"}, signal_id=signal.record_id,
        shadow_order_id=shadow_id, observed_at="2026-08-16T00:00:00Z",
        path_maturity_status="MATURE", unresolved=False,
        evaluated_at_ms=9_000_000, original_deadline_ms=8_200_000,
        required_end_ms=9_000_000,
    )
    with store._controlled_transaction():
        store._write_one(outcome)
    with pytest.raises(IntegrationError, match="Outcome horizon"):
        eligible_core_binding_formals(
            store, fence=int(activation["activation_rowid"]), release_sha=SHA,
        )
    store.close()


@pytest.mark.parametrize("latest_status,expected_complete", (("GAPPED", False), ("MATURE", True)))
def test_binding_latest_outcome_controls_completeness(
    tmp_path: Path, latest_status: str, expected_complete: bool
) -> None:
    store = EvidenceStore(tmp_path / "evidence.sqlite")
    activation = capture_binding_activation(
        store, release_sha=SHA, run_id="run", manifest_hash="manifest",
    )
    signal = _commit_test_formal(store, suffix="current")
    shadow_id = store._connection.execute(
        "SELECT record_id FROM shadow_orders WHERE signal_id=?", (signal.record_id,)
    ).fetchone()[0]
    with store._controlled_transaction():
        for evaluated_at, status, unresolved in (
            (8_200_000, "MATURE", False),
            (8_200_001, latest_status, latest_status != "MATURE"),
        ):
            store._write_one(OutcomeEnvelope.create(
                identity={"evaluated_at": evaluated_at}, signal_id=signal.record_id,
                shadow_order_id=shadow_id, observed_at="1970-01-01T00:16:40Z",
                path_maturity_status=status, unresolved=unresolved,
                evaluated_at_ms=evaluated_at, original_deadline_ms=8_200_000,
                required_end_ms=8_200_000,
            ))
    formal = eligible_core_binding_formals(
        store, fence=int(activation["activation_rowid"]), release_sha=SHA,
    )[0]
    assert formal.horizon_ms == 8_200_000
    assert formal.complete_outcome is expected_complete
    store.close()


class Clock:
    def now(self) -> datetime:
        return datetime.fromtimestamp(600, UTC)


class PublicClient:
    def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
        assert coin == "BTC" and interval == "5m"
        return [
            {
                "i": "5m",
                "s": coin,
                "t": 300_000,
                "T": 599_999,
                "o": "100",
                "h": "101",
                "l": "99",
                "c": "100",
                "v": "10",
            }
        ]


class Webhook:
    def __init__(self) -> None:
        self.calls = 0

    def post(self, **_: object) -> WebhookResponse:
        self.calls += 1
        return WebhookResponse(204)


class FailingDispatcher:
    def __init__(self) -> None:
        self.closed = False

    def dispatch_due(self, *, now: datetime) -> tuple[object, ...]:
        del now
        raise sqlite3.DatabaseError("injected dispatcher authority failure")

    def close(self) -> None:
        self.closed = True


def _config_values() -> dict[str, object]:
    return {
        "schema": production.THREE_SETUP_CONFIG_SCHEMA,
        "release_sha": SHA,
        "evidence_store_path": str(production.THREE_SETUP_EVIDENCE_STORE_PATH),
        "registry_root": str(production.THREE_SETUP_REGISTRY_ROOT),
        "closed_bar_store_path": str(production.THREE_SETUP_CLOSED_BAR_STORE_PATH),
        "cost_model": {
            "version": "cost-1",
            "fee_bps_per_side": "0",
            "slippage_bps_per_side": "0",
            "stress_slippage_bps_per_side": "2",
        },
        "acknowledgement_timeout_seconds": 30,
        "notification_poll_seconds": 1,
    }


def _market() -> RegistryMarket:
    return RegistryMarket(
        display="BTC",
        tier=RegistryTier.P0,
        identity=MarketIdentity.create(dex="MAIN", coin="BTC"),
        asset_class=AssetClass.CRYPTO,
        size_decimals=5,
        price_max_decimals=1,
        max_leverage=Decimal("40"),
        is_hip3=False,
        market_status="ACTIVE",
        lifecycle=MarketLifecycle.ACTIVE,
        metadata_observed_at=datetime(2026, 8, 16, tzinfo=UTC),
        metadata_hash=sha256_hex(b"btc-metadata"),
    )


class E4Node:
    def __init__(self) -> None:
        self.strategy: object | None = None
        self.started = asyncio.Event()
        self.stopped = asyncio.Event()
        self.disposed = False
        self.run_calls = 0
        self.run_async_calls = 0
        self.stop_calls = 0
        self.handle_calls = 0
        self.run_completed = False
        self.run_cancelled = False
        self._is_running = False
        self.running_reads = 0
        self.running_observed = asyncio.Event()
        self.auto_running = True
        self.events: list[str] = []
        self.outcome = "wait"
        self.release = asyncio.Event()
        self.stop_error: Exception | None = None

    def add_strategy(self, strategy: object) -> None:
        self.strategy = strategy

    @property
    def is_running(self) -> bool:
        self.running_reads += 1
        if self._is_running:
            self.running_observed.set()
        return self._is_running

    @is_running.setter
    def is_running(self, value: bool) -> None:
        self._is_running = value

    def run(self) -> None:
        self.run_calls += 1
        raise AssertionError("hosted application called synchronous LiveNode.run")

    async def run_async(self) -> None:
        self.run_async_calls += 1
        assert self.handle_calls == 1
        self.events.append("run_start")
        self.is_running = self.auto_running
        self.started.set()
        try:
            if self.outcome == "wait":
                await self.stopped.wait()
            else:
                await self.release.wait()
                if self.outcome == "exception":
                    raise RuntimeError("node child failed")
                if self.outcome == "cancelled":
                    raise asyncio.CancelledError
        except asyncio.CancelledError:
            self.run_cancelled = True
            raise
        finally:
            self.is_running = False
            self.run_completed = True
            self.events.append("run_complete")

    def handle(self) -> E4Node:
        self.handle_calls += 1
        self.events.append("handle")
        return self

    def stop(self) -> None:
        self.stop_calls += 1
        self.events.append("stop")
        self.stopped.set()
        if self.stop_error is not None:
            raise self.stop_error

    def dispose(self) -> None:
        assert self.run_completed
        self.events.append("dispose")
        self.disposed = True


class E4Capture:
    def __init__(self) -> None:
        self.warmup_health = {"readiness": "READY"}
        self.capture_health = {
            "stream_health": "HEALTHY",
            "continuity_requirements_remaining": 0,
            "storage_failures": 0,
            "admitted_observer_failures": (),
        }
        self.observer: object | None = None

    def set_admitted_event_observer(self, observer: object) -> None:
        self.observer = observer


def _e4_composition_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[production.ThreeSetupProductionConfig, E4Node, E4Capture]:
    root = tmp_path / "state"
    monkeypatch.setattr(production, "THREE_SETUP_STATE_ROOT", root)
    monkeypatch.setattr(production, "THREE_SETUP_EVIDENCE_STORE_PATH", root / "evidence.sqlite")
    monkeypatch.setattr(production, "THREE_SETUP_REGISTRY_ROOT", root / "registry")
    monkeypatch.setattr(
        production, "THREE_SETUP_CLOSED_BAR_STORE_PATH", root / "closed-bars.sqlite"
    )
    market = _market()
    snapshot = PitUniverseSnapshot.create(
        observed_at_ns=1_800_000_000_000,
        expressions=(
            MarketExpression(
                market_id=market.identity.market_id,
                dex="MAIN",
                provider_coin=market.identity.coin,
                instrument_id="BTC-PERP.HYPERLIQUID",
                expression_id="expr-BTC",
                instrument_metadata_version="v1",
                instrument_metadata_hash=market.metadata_hash,
            ),
        ),
    )
    manifest = RunManifest.create(
        run_id="ts5a-e4-production-test",
        git_sha=SHA,
        git_tree="b" * 40,
        snapshot=snapshot,
        process_epoch="process-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
        capture_configuration={"bar_types": ["1-MINUTE", "5-MINUTE"]},
        subscription_policy={
            "discovery": [market.identity.market_id],
            "watch": [market.identity.market_id],
            "actionable": [market.identity.market_id],
        },
        trial_ledger_id="ts5a-test",
    )
    e4 = E4Store(tmp_path / "e4")
    e4.initialize(manifest, snapshot)
    registry = MarketRegistryManager(root / "registry", metadata_validator=lambda _: True)
    version = RegistryVersion.create(
        version="three-setup-e4",
        created_at=datetime(2026, 9, 27, tzinfo=UTC),
        markets=(market,),
    )
    registry.stage(version)
    registry.request_apply(version.version)
    node = E4Node()
    capture = E4Capture()
    fake_host = ModuleType("trader_assist_v0.nautilus_e4.host")
    fake_host.build_public_data_node = lambda: node  # type: ignore[attr-defined]
    fake_host.build_capture_strategy = lambda **_kwargs: capture  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "trader_assist_v0.nautilus_e4.host", fake_host)
    # The ordinary local dev venv omits optional rc5; authoritative rc5 tests
    # run in the qualified Linux environment. Preserve the real parser seam.
    fake_model = ModuleType("nautilus_trader.model")
    minute, last, external = object(), object(), object()
    fake_model.BarAggregation = SimpleNamespace(MINUTE=minute)  # type: ignore[attr-defined]
    fake_model.PriceType = SimpleNamespace(LAST=last)  # type: ignore[attr-defined]
    fake_model.AggregationSource = SimpleNamespace(EXTERNAL=external)  # type: ignore[attr-defined]

    class FakeBarType:
        @staticmethod
        def from_str(raw: str) -> SimpleNamespace:
            instrument, step, aggregation, price, source = raw.rsplit("-", 4)
            return SimpleNamespace(
                instrument_id=instrument,
                spec=SimpleNamespace(
                    step=int(step),
                    aggregation=minute if aggregation == "MINUTE" else object(),
                    price_type=last if price == "LAST" else object(),
                ),
                aggregation_source=external if source == "EXTERNAL" else object(),
            )

    fake_model.BarType = FakeBarType  # type: ignore[attr-defined]
    fake_package = ModuleType("nautilus_trader")
    fake_package.model = fake_model  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "nautilus_trader", fake_package)
    monkeypatch.setitem(sys.modules, "nautilus_trader.model", fake_model)
    config = production.ThreeSetupProductionConfig(
        release_sha=SHA,
        evidence_store_path=root / "evidence.sqlite",
        registry_root=root / "registry",
        closed_bar_store_path=root / "closed-bars.sqlite",
        cost_model=production.CostModel("cost-1", Decimal(), Decimal(), Decimal("2")),
        notification_poll_seconds=1,
        e4_evidence_root=tmp_path / "e4",
        e4_manifest_path=e4.manifest_path,
        e4_snapshot_path=e4.snapshot_path,
        e4_bar_types=(
            "BTC-PERP.HYPERLIQUID-1-MINUTE-LAST-EXTERNAL",
            "BTC-PERP.HYPERLIQUID-5-MINUTE-LAST-EXTERNAL",
        ),
    )
    return config, node, capture


def test_fixed_manifest_config_is_canonical_and_rejects_legacy_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "state"
    monkeypatch.setattr(production, "THREE_SETUP_STATE_ROOT", root)
    monkeypatch.setattr(production, "THREE_SETUP_EVIDENCE_STORE_PATH", root / "evidence.sqlite")
    monkeypatch.setattr(production, "THREE_SETUP_REGISTRY_ROOT", root / "registry")
    monkeypatch.setattr(
        production, "THREE_SETUP_CLOSED_BAR_STORE_PATH", root / "closed-bars.sqlite"
    )
    values = _config_values()
    path = tmp_path / "config.json"
    path.write_bytes(canonical_json_bytes(values))
    config = production.load_three_setup_config(path)
    assert config.evidence_store_path != Path("/var/lib/trader-assist-v0/runtime.db")
    values["closed_bar_store_path"] = "/var/lib/trader-assist-v0/runtime.db"
    path.write_bytes(canonical_json_bytes(values))
    with pytest.raises(production.ThreeSetupProductionError, match="fixed manifest"):
        production.load_three_setup_config(path)


@pytest.mark.parametrize("identity", ("manifest", "snapshot"))
def test_provided_e4_identity_must_match_durable_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    identity: str,
) -> None:
    config, _node, _capture = _e4_composition_fixture(tmp_path, monkeypatch)
    assert config.e4_evidence_root is not None
    store = E4Store(config.e4_evidence_root)
    if identity == "manifest":
        other = RunManifest.create(
            run_id="other-run",
            git_sha=SHA,
            git_tree="b" * 40,
            snapshot=store.load_snapshot(),
            process_epoch="process-1",
            continuity_epoch="continuity-1",
            admission_epoch="admission-1",
            capture_configuration={"bar_types": ["1-MINUTE", "5-MINUTE"]},
            subscription_policy={"discovery": [], "watch": [], "actionable": []},
            trial_ledger_id="other",
        )
        path = tmp_path / "other-manifest.json"
        path.write_text(other.model_dump_json(), encoding="utf-8")
        config = replace(config, e4_manifest_path=path)
    else:
        original = store.load_snapshot()
        other_snapshot = PitUniverseSnapshot.create(
            observed_at_ns=original.observed_at_ns + 1,
            expressions=original.expressions,
        )
        path = tmp_path / "other-snapshot.json"
        path.write_text(other_snapshot.model_dump_json(), encoding="utf-8")
        config = replace(config, e4_snapshot_path=path)
    with pytest.raises(production.ThreeSetupProductionError, match="durable evidence"):
        production.validate_three_setup_e4_identity(config)


@pytest.mark.parametrize("minute", (1, 5))
def test_selected_market_requires_both_exact_external_bar_types(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    minute: int,
) -> None:
    config, _node, _capture = _e4_composition_fixture(tmp_path, monkeypatch)
    remaining = tuple(bar for bar in config.e4_bar_types if f"-{minute}-MINUTE-" not in bar)
    with pytest.raises(production.ThreeSetupProductionError, match="subscriptions lack"):
        production.validate_three_setup_e4_identity(replace(config, e4_bar_types=remaining))


@pytest.mark.parametrize("change", ("market", "metadata"))
def test_registry_market_and_metadata_must_match_pit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    config, _node, _capture = _e4_composition_fixture(tmp_path, monkeypatch)
    market = _market()
    if change == "market":
        market = market.model_copy(
            update={
                "identity": MarketIdentity.create(dex="MAIN", coin="ETH"),
            }
        )
    else:
        market = market.model_copy(update={"metadata_hash": "0" * 64})
    selected = SimpleNamespace(markets=(market,))
    monkeypatch.setattr(
        production,
        "MarketRegistryManager",
        lambda *_args, **_kwargs: SimpleNamespace(active=lambda: selected),
    )
    with pytest.raises(production.ThreeSetupProductionError, match="Registry market differs"):
        production.validate_three_setup_e4_identity(config)


@pytest.mark.parametrize("suffix", ("MID-EXTERNAL", "LAST-INTERNAL", "LAST-EXTERNAL"))
def test_bar_identity_never_accepts_prefix_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
) -> None:
    config, _node, _capture = _e4_composition_fixture(tmp_path, monkeypatch)
    bad = f"BTC-PERP.HYPERLIQUID-1-MINUTE-{suffix}"
    bars = (bad, config.e4_bar_types[1])
    if suffix == "LAST-EXTERNAL":
        bad = "ETH-PERP.HYPERLIQUID-1-MINUTE-LAST-EXTERNAL"
        bars = (bad, config.e4_bar_types[1])
    with pytest.raises(production.ThreeSetupProductionError, match="subscriptions lack"):
        production.validate_three_setup_e4_identity(replace(config, e4_bar_types=bars))


def test_active_e4_rejects_legacy_rc4_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, _node, _capture = _e4_composition_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        production.RunManifest,
        "model_validate_json",
        lambda _: SimpleNamespace(git_sha=SHA, nautilus_version="2.0.0rc4"),
    )
    with pytest.raises(production.ThreeSetupProductionError, match="Nautilus identity differs"):
        production.validate_three_setup_e4_identity(config)


@pytest.mark.parametrize("flag", ("private_api", "exchange_write", "real_exec_client_registered"))
def test_e4_run_manifest_rejects_true_zero_write_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    flag: str,
) -> None:
    config, _node, _capture = _e4_composition_fixture(tmp_path, monkeypatch)
    assert config.e4_evidence_root is not None
    raw = E4Store(config.e4_evidence_root).load_manifest().model_dump(mode="json")
    raw[flag] = True
    with pytest.raises(ValueError):
        RunManifest.model_validate(raw)


@pytest.mark.parametrize(
    "retained_work",
    ("scanner_evidence", "strategy_evaluation", "formal_signal", "notification_outbox"),
)
def test_initial_pending_registry_rejects_retained_application_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, retained_work: str
) -> None:
    config, _node, _capture = _e4_composition_fixture(tmp_path, monkeypatch)
    evidence = EvidenceStore(config.evidence_store_path)
    with evidence._connection:
        if retained_work == "scanner_evidence":
            evidence._connection.execute(
                """INSERT INTO immutable_records(
                    record_id, record_type, canonical_hash, identity_json, payload_json
                ) VALUES ('retained-scanner', 'scanner_evidence', '0', '{}', '{}')"""
            )
        else:
            evidence._connection.execute(
                """INSERT INTO notification_outbox(
                    idempotency_key, schema_version, kind, content, created_at, state,
                    attempt_count, next_attempt_at
                ) VALUES ('retained-notification', '1', 'WATCH', '{}', '2026-08-16T00:00:00Z',
                          'PENDING', 0, '2026-08-16T00:00:00Z')"""
            )
    evidence.close()

    with pytest.raises(
        IntegrationError,
        match="cannot restore retained application evidence without active Registry authority",
    ):
        production.compose_three_setup_application(
            config=config,
            notification_adapter=WebhookDeliveryAdapter(
                client=Webhook(), config=WebhookConfig(url="https://example.invalid/hook")
            ),
            clock=Clock().now,
        )


def test_real_composition_owns_one_dispatcher_and_shuts_down_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    config, node, capture = _e4_composition_fixture(tmp_path, monkeypatch)
    application = production.compose_three_setup_application(
        config=config,
        notification_adapter=WebhookDeliveryAdapter(
            client=Webhook(), config=WebhookConfig(url="https://example.invalid/hook")
        ),
        clock=Clock().now,
    )
    assert isinstance(application, production.E4ThreeSetupProductionApplication)
    assert node.strategy is capture
    assert capture.observer is not None
    dispatcher_starts = 0
    original_dispatch_loop = application._dispatch_loop

    async def counted_dispatch_loop(shutdown: asyncio.Event) -> None:
        nonlocal dispatcher_starts
        dispatcher_starts += 1
        await original_dispatch_loop(shutdown)

    monkeypatch.setattr(application, "_dispatch_loop", counted_dispatch_loop)

    async def exercise() -> None:
        shutdown = asyncio.Event()
        task = asyncio.create_task(application.run(shutdown))
        await asyncio.wait_for(node.started.wait(), timeout=1)
        shutdown.set()
        await task

    with caplog.at_level(logging.INFO, logger="trader_assist_v0.three_setup"):
        asyncio.run(exercise())
    assert dispatcher_starts == 1
    assert node.run_calls == 0
    assert node.run_async_calls == 1
    assert node.handle_calls == 1
    assert node.stop_calls == 1
    assert not node.run_cancelled
    assert node.events == ["handle", "run_start", "stop", "run_complete", "dispose"]
    assert node.stopped.is_set() and node.disposed
    events = {json.loads(record.message)["event"] for record in caplog.records}
    assert {"STARTUP", "SHUTDOWN"} <= events
    with pytest.raises(sqlite3.ProgrammingError):
        application.bootstrap.evidence._connection.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        application.projection.store.connection.execute("SELECT 1")


class E4ControlledChild:
    def __init__(self, component: str) -> None:
        self.component = component
        self.outcome = "wait"
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def run(self, shutdown: asyncio.Event) -> None:
        self.started.set()
        await self.release.wait()
        if self.outcome == "exception":
            raise RuntimeError(f"{self.component} child failed")
        if self.outcome == "cancelled":
            raise asyncio.CancelledError
        if self.outcome == "wait":
            await shutdown.wait()


class E4ControlledCloser:
    def __init__(self) -> None:
        self.closed = False
        self.error: Exception | None = None

    def close(self) -> None:
        self.closed = True
        if self.error is not None:
            raise self.error


def e4_supervisor_application() -> tuple[
    production.E4ThreeSetupProductionApplication,
    E4Node,
    E4ControlledChild,
    E4ControlledChild,
    tuple[E4ControlledCloser, E4ControlledCloser, E4ControlledCloser],
]:
    node = E4Node()
    domain = E4ControlledChild("domain")
    dispatcher_child = E4ControlledChild("dispatcher")
    dispatcher = E4ControlledCloser()
    bootstrap_closer = E4ControlledCloser()
    projection = E4ControlledCloser()
    active = SimpleNamespace(version="v1", content_hash="hash")
    application = object.__new__(production.E4ThreeSetupProductionApplication)
    application.node = node
    application.e4_runtime = domain  # type: ignore[assignment]
    application.dispatcher = dispatcher  # type: ignore[assignment]
    application.projection = projection  # type: ignore[assignment]
    application.bootstrap = SimpleNamespace(  # type: ignore[assignment]
        registry=SimpleNamespace(active=lambda: active, pending_version=lambda: None),
        close=bootstrap_closer.close,
    )
    application.logger = logging.getLogger("trader_assist_v0.three_setup")
    application._dispatch_loop = dispatcher_child.run  # type: ignore[method-assign]
    return application, node, domain, dispatcher_child, (
        dispatcher,
        bootstrap_closer,
        projection,
    )


def e4_child_event(caplog: pytest.LogCaptureFixture) -> dict[str, object]:
    return next(
        event
        for record in caplog.records
        if (event := json.loads(record.message))["event"] == "PRODUCTION_CHILD_EXIT_UNEXPECTED"
    )


@pytest.mark.parametrize("component", ("node", "domain", "dispatcher"))
@pytest.mark.parametrize("outcome", ("exception", "normal", "cancelled"))
def test_e4_each_child_exit_is_fatal_and_journaled(
    component: str, outcome: str, caplog: pytest.LogCaptureFixture
) -> None:
    application, node, domain, dispatcher, closers = e4_supervisor_application()
    target = {"node": node, "domain": domain, "dispatcher": dispatcher}[component]
    target.outcome = outcome

    async def exercise() -> BaseException:
        shutdown = asyncio.Event()
        run_task = asyncio.create_task(application.run(shutdown))
        await asyncio.wait_for(
            asyncio.gather(node.started.wait(), domain.started.wait(), dispatcher.started.wait()),
            timeout=1,
        )
        target.release.set()
        try:
            await asyncio.wait_for(run_task, timeout=1)
        except BaseException as exc:
            return exc
        raise AssertionError("unexpected E4 child exit was not fatal")

    with caplog.at_level(logging.INFO, logger="trader_assist_v0.three_setup"):
        error = asyncio.run(exercise())
    expected_type = "RuntimeError" if outcome == "exception" else "ThreeSetupProductionError"
    assert type(error).__name__ == expected_type
    assert component in str(error)
    assert e4_child_event(caplog) == {
        "event": "PRODUCTION_CHILD_EXIT_UNEXPECTED",
        "component": component,
        "error_type": expected_type,
    }
    assert all(closer.closed for closer in closers)
    assert node.stop_calls == 1 and node.disposed and node.run_completed
    assert node.run_calls == 0 and node.run_async_calls == 1
    assert node.events.index("handle") < node.events.index("run_start")
    assert node.events.index("stop") < node.events.index("dispose")
    assert node.events.index("run_complete") < node.events.index("dispose")
    if component != "node":
        assert not node.run_cancelled


@pytest.mark.parametrize(
    ("outcomes", "expected_component", "expected_type"),
    [
        ({"node": "normal", "domain": "exception"}, "domain", "RuntimeError"),
        ({"node": "cancelled", "domain": "exception"}, "domain", "RuntimeError"),
        ({"node": "exception", "domain": "exception"}, "node", "RuntimeError"),
        ({"domain": "exception", "dispatcher": "exception"}, "domain", "RuntimeError"),
        ({"node": "normal", "domain": "normal"}, "node", "ThreeSetupProductionError"),
    ],
)
def test_e4_simultaneous_done_selection_is_stable(
    outcomes: dict[str, str], expected_component: str, expected_type: str
) -> None:
    async def exercise() -> production._SelectedE4ChildFailure | None:
        async def finish(outcome: str) -> None:
            if outcome == "exception":
                raise RuntimeError("selected child failed")
            if outcome == "cancelled":
                raise asyncio.CancelledError

        children = tuple(
            (component, asyncio.create_task(finish(outcomes.get(component, "normal"))))
            for component in ("node", "domain", "dispatcher")
        )
        await asyncio.gather(*(task for _, task in children), return_exceptions=True)
        return production._select_e4_child_failure(
            children, {task for _, task in children}, asyncio.Event()
        )

    selected = asyncio.run(exercise())
    assert selected is not None
    assert selected.component == expected_component
    assert selected.error_type == expected_type


def test_e4_startup_waits_for_running_without_unsupervised_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application, node, domain, dispatcher, closers = e4_supervisor_application()
    node.auto_running = False
    original_wait = asyncio.wait
    timed_wait_started = asyncio.Event()
    timeouts: list[float] = []

    async def recorded_wait(
        tasks: object, *, timeout: float | None = None, return_when: str = asyncio.ALL_COMPLETED
    ) -> object:
        if timeout is not None:
            timeouts.append(timeout)
            timed_wait_started.set()
        return await original_wait(tasks, timeout=timeout, return_when=return_when)  # type: ignore[arg-type]

    monkeypatch.setattr(production.asyncio, "wait", recorded_wait)

    async def exercise() -> None:
        shutdown = asyncio.Event()
        run_task = asyncio.create_task(application.run(shutdown))
        await asyncio.wait_for(
            asyncio.gather(node.started.wait(), domain.started.wait(), dispatcher.started.wait()),
            timeout=1,
        )
        await asyncio.wait_for(timed_wait_started.wait(), timeout=1)
        assert not run_task.done() and not node.is_running
        assert timeouts == [0.01]
        node.is_running = True
        await asyncio.wait_for(node.running_observed.wait(), timeout=1)
        assert not run_task.done()
        domain.release.set()
        dispatcher.release.set()
        shutdown.set()
        await asyncio.wait_for(run_task, timeout=1)

    asyncio.run(exercise())
    assert node.disposed and node.stop_calls == 1
    assert all(closer.closed for closer in closers)


@pytest.mark.parametrize("component", ("node", "domain", "dispatcher"))
@pytest.mark.parametrize("outcome", ("exception", "normal", "cancelled"))
def test_e4_startup_child_exit_before_running_is_fatal(
    component: str, outcome: str, caplog: pytest.LogCaptureFixture
) -> None:
    application, node, domain, dispatcher, _ = e4_supervisor_application()
    node.auto_running = False
    target = {"node": node, "domain": domain, "dispatcher": dispatcher}[component]
    target.outcome = outcome

    async def exercise() -> BaseException:
        shutdown = asyncio.Event()
        run_task = asyncio.create_task(application.run(shutdown))
        await asyncio.wait_for(
            asyncio.gather(node.started.wait(), domain.started.wait(), dispatcher.started.wait()),
            timeout=1,
        )
        target.release.set()
        try:
            await asyncio.wait_for(run_task, timeout=1)
        except BaseException as exc:
            return exc
        raise AssertionError("early child exit was not fatal")

    with caplog.at_level(logging.INFO, logger="trader_assist_v0.three_setup"):
        error = asyncio.run(exercise())
    expected_type = "RuntimeError" if outcome == "exception" else "ThreeSetupProductionError"
    assert type(error).__name__ == expected_type
    assert component in str(error)
    assert e4_child_event(caplog)["component"] == component
    assert e4_child_event(caplog)["error_type"] == expected_type
    assert node.disposed


def test_e4_running_transition_does_not_hide_simultaneous_child_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    application, node, domain, dispatcher, _ = e4_supervisor_application()
    node.auto_running = False
    domain.outcome = "exception"

    async def exercise() -> None:
        run_task = asyncio.create_task(application.run(asyncio.Event()))
        await asyncio.wait_for(
            asyncio.gather(node.started.wait(), domain.started.wait(), dispatcher.started.wait()),
            timeout=1,
        )
        node.is_running = True
        domain.release.set()
        with pytest.raises(RuntimeError, match="domain child failed"):
            await asyncio.wait_for(run_task, timeout=1)

    with caplog.at_level(logging.INFO, logger="trader_assist_v0.three_setup"):
        asyncio.run(exercise())
    assert e4_child_event(caplog)["component"] == "domain"


@pytest.mark.parametrize("node_outcome", ("normal", "cancelled"))
def test_e4_startup_simultaneous_exception_outranks_other_exit(
    node_outcome: str, caplog: pytest.LogCaptureFixture
) -> None:
    application, node, domain, dispatcher, _ = e4_supervisor_application()
    node.auto_running = False
    node.outcome = node_outcome
    domain.outcome = "exception"

    async def exercise() -> None:
        run_task = asyncio.create_task(application.run(asyncio.Event()))
        await asyncio.wait_for(
            asyncio.gather(node.started.wait(), domain.started.wait(), dispatcher.started.wait()),
            timeout=1,
        )
        node.release.set()
        domain.release.set()
        with pytest.raises(RuntimeError, match="domain child failed"):
            await asyncio.wait_for(run_task, timeout=1)

    with caplog.at_level(logging.INFO, logger="trader_assist_v0.three_setup"):
        asyncio.run(exercise())
    assert e4_child_event(caplog)["component"] == "domain"
    assert node.disposed


def test_e4_operator_shutdown_during_startup_is_clean() -> None:
    application, node, domain, dispatcher, closers = e4_supervisor_application()
    node.auto_running = False

    async def exercise() -> None:
        shutdown = asyncio.Event()
        run_task = asyncio.create_task(application.run(shutdown))
        await asyncio.wait_for(
            asyncio.gather(node.started.wait(), domain.started.wait(), dispatcher.started.wait()),
            timeout=1,
        )
        shutdown.set()
        await asyncio.wait_for(run_task, timeout=1)

    asyncio.run(exercise())
    assert node.disposed and node.stop_calls == 1
    assert all(closer.closed for closer in closers)


def test_e4_failed_stop_never_disposes_uncompleted_node() -> None:
    application, node, domain, dispatcher, closers = e4_supervisor_application()

    def failed_stop() -> None:
        node.stop_calls += 1
        raise ValueError("node stop failed before signalling")

    node.stop = failed_stop  # type: ignore[method-assign]

    async def exercise() -> None:
        shutdown = asyncio.Event()
        run_task = asyncio.create_task(application.run(shutdown))
        await asyncio.wait_for(
            asyncio.gather(node.started.wait(), domain.started.wait(), dispatcher.started.wait()),
            timeout=1,
        )
        shutdown.set()
        with pytest.raises(ValueError, match="node stop failed"):
            await asyncio.wait_for(run_task, timeout=2)
        assert not node.run_completed and not node.disposed

    asyncio.run(exercise())
    assert node.stop_calls == 1 and not node.disposed
    assert all(closer.closed for closer in closers)


def test_e4_selected_child_error_survives_cleanup_failure() -> None:
    application, node, domain, dispatcher, closers = e4_supervisor_application()
    domain.outcome = "exception"
    closers[0].error = ValueError("dispatcher cleanup failed")
    node.stop_error = ValueError("node stop failed")

    async def exercise() -> None:
        run_task = asyncio.create_task(application.run(asyncio.Event()))
        await asyncio.wait_for(
            asyncio.gather(node.started.wait(), domain.started.wait(), dispatcher.started.wait()),
            timeout=1,
        )
        domain.release.set()
        with pytest.raises(RuntimeError, match="domain child failed"):
            await asyncio.wait_for(run_task, timeout=2)

    asyncio.run(exercise())
    assert all(closer.closed for closer in closers)
    assert node.disposed and node.stop_calls == 1


def test_systemd_execstart_targets_the_executable_three_setup_wrapper() -> None:
    root = Path(__file__).parents[1]
    unit = (root / "deploy/p4a/systemd/trader-assist-v0-three-setup.service").read_text()
    wrapper = root / "scripts/p4a/run_three_setup_shadow_runtime.sh"
    assert "ExecStart=/opt/trader-assist-v0/scripts/p4a/run_three_setup_shadow_runtime.sh" in unit
    assert wrapper.stat().st_mode & 0o111


def test_dispatcher_authority_failure_is_fatal_and_closes_all_stores(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    version = RegistryVersion.create(
        version="three-setup", created_at=datetime(2026, 8, 16, tzinfo=UTC), markets=(_market(),)
    )
    registry.stage(version)
    registry.request_apply(version.version)
    closed = ClosedBarStore(tmp_path / "closed.sqlite")
    data = MultiAssetDataAuthority(store=closed, registry=registry)
    data.admit_rest_history(
        market=_market(),
        snapshot=[
            {
                "i": "5m",
                "s": "BTC",
                "t": 300_000,
                "T": 599_999,
                "o": "100",
                "h": "101",
                "l": "99",
                "c": "100",
                "v": "10",
            }
        ],
        received_at=Clock().now(),
    )
    bootstrap = production.MultiAssetProductionBootstrap.compose(
        registry=registry,
        data_authority=data,
        public_client=PublicClient(),  # type: ignore[arg-type]
        evidence_db_path=tmp_path / "evidence.sqlite",
        cost_model=production.CostModel("cost-1", Decimal(), Decimal(), Decimal("2")),
        release_sha=SHA,
        clock=Clock().now,
    )
    dispatcher = FailingDispatcher()
    application = production.ThreeSetupProductionApplication(
        bootstrap=bootstrap,
        dispatcher=dispatcher,  # type: ignore[arg-type]
        clock=Clock().now,
        notification_poll_seconds=1,
    )
    with caplog.at_level(logging.INFO, logger="trader_assist_v0.three_setup"):
        with pytest.raises(sqlite3.DatabaseError, match="injected dispatcher authority failure"):
            asyncio.run(application.run(asyncio.Event()))
    events = [json.loads(record.message) for record in caplog.records]
    assert {event["event"] for event in events} >= {"NOTIFICATION_FAILURE", "SHUTDOWN"}
    assert next(event for event in events if event["event"] == "NOTIFICATION_FAILURE") == {
        "event": "NOTIFICATION_FAILURE",
        "error_type": "DatabaseError",
    }
    assert dispatcher.closed
    with pytest.raises(sqlite3.ProgrammingError):
        bootstrap.evidence._connection.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        bootstrap.data_authority.store.connection.execute("SELECT 1")


class SupervisorCloser:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class SupervisorRuntime:
    def __init__(self, outcome: str) -> None:
        self.outcome = outcome
        self.on_finalized_5m = None
        self.on_reconnect = None
        self.on_session_event = None

    async def run(self, shutdown: asyncio.Event) -> None:
        if self.outcome == "normal":
            return
        if self.outcome == "exception":
            raise RuntimeError("runtime child failed")
        await shutdown.wait()


class SupervisorDispatcher(SupervisorCloser):
    def dispatch_due(self, *, now: datetime) -> tuple[object, ...]:
        del now
        return ()


def supervisor_application(runtime_outcome: str = "wait") -> tuple[object, object, object]:
    evidence = SupervisorCloser()
    closed_store = SupervisorCloser()
    bootstrap_closed = SupervisorCloser()
    runtime = SupervisorRuntime(runtime_outcome)
    active = SimpleNamespace(version="v1", content_hash="hash")
    bootstrap = SimpleNamespace(
        runtime=runtime,
        registry=SimpleNamespace(active=lambda: active, pending_version=lambda: None),
        coordinator=SimpleNamespace(_release_sha=SHA),
        evidence=evidence,
        data_authority=SimpleNamespace(store=closed_store),
        close=bootstrap_closed.close,
    )
    dispatcher = SupervisorDispatcher()
    application = production.ThreeSetupProductionApplication(
        bootstrap=bootstrap,  # type: ignore[arg-type]
        dispatcher=dispatcher,  # type: ignore[arg-type]
        clock=Clock().now,
        notification_poll_seconds=1,
    )
    return application, dispatcher, closed_store


@pytest.mark.parametrize("outcome", ["normal", "exception"])
def test_runtime_child_exit_before_operator_shutdown_is_fatal(
    outcome: str, caplog: pytest.LogCaptureFixture
) -> None:
    application, dispatcher, store = supervisor_application(outcome)
    expected = "PRODUCTION_CHILD_EXIT_UNEXPECTED" if outcome == "normal" else "runtime child failed"
    with caplog.at_level(logging.INFO, logger="trader_assist_v0.three_setup"):
        with pytest.raises(Exception, match=expected):
            asyncio.run(application.run(asyncio.Event()))  # type: ignore[attr-defined]
    child_event = next(
        json.loads(record.message)
        for record in caplog.records
        if json.loads(record.message)["event"] == "PRODUCTION_CHILD_EXIT_UNEXPECTED"
    )
    assert child_event["component"] == "runtime"
    assert dispatcher.closed and store.closed  # type: ignore[attr-defined]


@pytest.mark.parametrize("outcome", ["normal", "exception"])
def test_dispatcher_child_exit_before_operator_shutdown_is_fatal(
    outcome: str, caplog: pytest.LogCaptureFixture
) -> None:
    application, dispatcher, store = supervisor_application()

    async def dispatcher_exit(_: asyncio.Event) -> None:
        if outcome == "exception":
            raise RuntimeError("dispatcher child failed")

    application._dispatch_loop = dispatcher_exit  # type: ignore[attr-defined,method-assign]
    expected = (
        "PRODUCTION_CHILD_EXIT_UNEXPECTED" if outcome == "normal" else "dispatcher child failed"
    )
    with caplog.at_level(logging.INFO, logger="trader_assist_v0.three_setup"):
        with pytest.raises(Exception, match=expected):
            asyncio.run(application.run(asyncio.Event()))  # type: ignore[attr-defined]
    child_event = next(
        json.loads(record.message)
        for record in caplog.records
        if json.loads(record.message)["event"] == "PRODUCTION_CHILD_EXIT_UNEXPECTED"
    )
    assert child_event["component"] == "dispatcher"
    assert dispatcher.closed and store.closed  # type: ignore[attr-defined]


def test_explicit_operator_shutdown_is_clean() -> None:
    application, dispatcher, store = supervisor_application()
    shutdown = asyncio.Event()
    shutdown.set()
    asyncio.run(application.run(shutdown))  # type: ignore[attr-defined]
    assert dispatcher.closed and store.closed  # type: ignore[attr-defined]
