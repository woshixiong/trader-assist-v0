#!/usr/bin/env python3
# mypy: disable-error-code="import-not-found"
"""Q1 evidence-only qualification of the frozen public Three Setup candidate.

The harness is a control-plane script. Product modules are imported only after
the caller binds PYTHONPATH to the separate, exact candidate checkout.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

BASE_SHA = "36d57b3a9f4677354f1d5d63bca17c6fb72befbd"
BASE_TREE = "d642119ddd8b9e554ae9bd441de44daac3e97599"
SCHEMA = "trader-assist-v0/three-setup-q1-qualification/v1"
CLASSES = (
    "PASS",
    "PRODUCT_BLOCKER",
    "PROVIDER_DATA_INCOMPLETE",
    "HARNESS_OR_EXECUTION_SURFACE_GAP",
)
MANDATORY = tuple(
    [f"B{i:02}" for i in range(1, 13)]
    + [f"C{i:02}" for i in range(1, 17)]
    + [f"D{i:02}" for i in range(1, 11)]
)
ADVERSARIAL = tuple(f"H{i:02}" for i in range(1, 23))


class DiagnosticFailure(RuntimeError):
    """A classified failure with an optional validated child diagnostic."""

    def __init__(self, message: str, diagnostic: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.diagnostic = diagnostic


class QualificationGap(DiagnosticFailure):
    """The harness or execution surface cannot prove the frozen claim."""


class ProductBlocker(DiagnosticFailure):
    """An observed candidate product invariant failed."""


class ProviderIncomplete(DiagnosticFailure):
    """Public provider data did not satisfy the finite proof window."""


DIAGNOSTIC_STAGE = "ENTRY"
STAGES = frozenset(
    {
        "ENTRY", "CANDIDATE_IDENTITY", "RELEASE_MANIFEST", "DEPENDENCY_LOCKS",
        "TARGET_IMPORT", "TARGET_PIP", "TARGET_RUNTIME", "PUBLIC_FIXTURE",
        "E4_STORE", "CHILD_IDENTITY", "CHILD_RETAINED", "CHILD_COMPOSITION",
        "CHILD_LIVE", "CHILD_RESULT", "CHILD_1", "CHILD_2", "ARTIFACT_WRITE",
    }
)
KNOWN_FAILURES = frozenset(
    {
        "frozen candidate identity differs", "candidate HEAD drift", "candidate tree drift",
        "candidate checkout is not clean", "product module imported outside candidate source",
        "product script imported outside candidate checkout",
        "domain EvidenceStore integrity failed",
        "domain EvidenceStore SQLite read failed",
        "artifact includes private or secret-shaped data",
        "artifact includes secret-shaped content", "staged release unexpectedly includes Git state",
        "pilot lock identity differs", "candidate import is absent",
        "project distribution installed in target venv", "target pip check failed",
        "target platform differs from Ubuntu x86_64 Python 3.12",
        "public MAIN metadata unavailable", "public MAIN metadata shape unavailable",
        "public ETH perpetual metadata unavailable", "Registry identity changed",
        "exact external LAST 1m/5m BarTypes are unavailable",
        "Registry/PIT metadata binding failed", "segment has no Registry authority",
        "partial readiness reached product boundary callback",
        "active Registry readiness failed", "product application child failed during segment",
        "old boundary became newly actionable", "retained Registry identity is missing",
        "segment candidate release identity drift", "child process produced no bounded result",
        "candidate product segment failed", "candidate provider segment incomplete",
        "child segment execution surface failed", "E4 store identity failed",
    }
)


def _mark_stage(stage: str) -> None:
    global DIAGNOSTIC_STAGE
    if stage not in STAGES:
        raise ValueError("unknown diagnostic stage")
    DIAGNOSTIC_STAGE = stage


def _failure_diagnostic(exc: BaseException) -> dict[str, str]:
    if isinstance(exc, DiagnosticFailure) and exc.diagnostic is not None:
        return exc.diagnostic
    stage = DIAGNOSTIC_STAGE
    diagnostic = {"reason_stage": stage, "reason_code": type(exc).__name__}
    if isinstance(exc, DiagnosticFailure) and str(exc) in KNOWN_FAILURES:
        diagnostic["reason_detail"] = str(exc)
    return diagnostic


def _child_diagnostic(result: dict[str, Any]) -> dict[str, str] | None:
    stage, code, detail = (
        result.get("reason_stage"), result.get("reason_code"), result.get("reason_detail")
    )
    if (
        stage not in STAGES
        or not isinstance(code, str)
        or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", code)
    ):
        return None
    if detail is not None and (detail not in KNOWN_FAILURES or code not in {
        "QualificationGap", "ProviderIncomplete", "ProductBlocker"
    }):
        return None
    diagnostic = {"reason_stage": stage, "reason_code": code}
    if detail is not None:
        diagnostic["reason_detail"] = detail
    return diagnostic


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(root), *args),
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def exact_identity(candidate: Path, expected_sha: str, expected_tree: str) -> None:
    if expected_sha != BASE_SHA or expected_tree != BASE_TREE:
        raise QualificationGap("frozen candidate identity differs")
    if _git(candidate, "rev-parse", "HEAD") != expected_sha:
        raise QualificationGap("candidate HEAD drift")
    if _git(candidate, "rev-parse", "HEAD^{tree}") != expected_tree:
        raise QualificationGap("candidate tree drift")
    if _git(candidate, "status", "--porcelain=v1", "--untracked-files=all"):
        raise QualificationGap("candidate checkout is not clean")


def _assert_import_origins(candidate: Path) -> None:
    source_root = (candidate / "src" / "trader_assist_v0").resolve()
    script_root = (candidate / "scripts").resolve()
    for name, module in tuple(sys.modules.items()):
        origin = getattr(module, "__file__", None)
        if origin is None:
            continue
        actual = Path(origin).resolve()
        if (
            name == "trader_assist_v0" or name.startswith("trader_assist_v0.")
        ) and not actual.is_relative_to(source_root):
            raise QualificationGap("product module imported outside candidate source")
        if name.startswith("scripts.") and not actual.is_relative_to(script_root):
            raise QualificationGap("product script imported outside candidate checkout")


def classify(matrix: dict[str, bool], cause: str | None) -> str:
    """No incomplete or unproven claim can become PASS."""
    if cause == "PRODUCT_BLOCKER":
        return "PRODUCT_BLOCKER"
    if cause == "HARNESS_OR_EXECUTION_SURFACE_GAP":
        return "HARNESS_OR_EXECUTION_SURFACE_GAP"
    if cause == "PROVIDER_DATA_INCOMPLETE":
        return "PROVIDER_DATA_INCOMPLETE"
    return (
        "PASS"
        if all(matrix.get(key) is True for key in MANDATORY)
        else "HARNESS_OR_EXECUTION_SURFACE_GAP"
    )


def adversarial_matrix(matrix: dict[str, bool]) -> dict[str, bool]:
    def all_pass(*keys: str) -> bool:
        return all(matrix.get(key) is True for key in keys)

    try:
        _safe_artifact({"private_key": "sentinel"})
    except QualificationGap:
        redaction_proven = True
    else:
        redaction_proven = False
    checks = {
        "H01": all_pass("B01"),
        "H02": all_pass("B01"),
        "H03": all_pass("B04"),
        "H04": all_pass("B05"),
        "H05": all_pass("B02", "B06"),
        "H06": all_pass("B07", "B08"),
        "H07": all_pass("B09"),
        "H08": all_pass("B10"),
        "H09": all_pass("B12"),
        "H10": all_pass("C13"),
        "H11": all_pass("C12"),
        "H12": all_pass("C10"),
        "H13": all_pass("C11"),
        "H14": all_pass("C14"),
        "H15": all_pass("C15", "C16", "D08", "D09"),
        "H16": all_pass("D03", "D04"),
        "H17": all_pass("D05", "D06"),
        "H18": classify(matrix, "PROVIDER_DATA_INCOMPLETE") == "PROVIDER_DATA_INCOMPLETE",
        "H19": classify(matrix, "HARNESS_OR_EXECUTION_SURFACE_GAP")
        == "HARNESS_OR_EXECUTION_SURFACE_GAP",
        "H20": redaction_proven,
        "H21": all_pass("B01"),
        "H22": classify(matrix | {"B01": False}, None) != "PASS",
    }
    assert set(checks) == set(ADVERSARIAL)
    return checks


def _integrity(connection: sqlite3.Connection) -> bool:
    try:
        rows = connection.execute("PRAGMA integrity_check").fetchall()
    except sqlite3.DatabaseError:
        return False
    return len(rows) == 1 and rows[0][0] == "ok"


def _submission_proof(value: Any) -> tuple[int, bool]:
    """Inspect retained candidate evidence without interpreting Strategy semantics."""
    if isinstance(value, dict):
        count = 0
        valid = True
        if "venue_submitted" in value or "not_submitted" in value:
            count = 1
            valid = value.get("venue_submitted") is False and value.get("not_submitted") is True
        for child in value.values():
            child_count, child_valid = _submission_proof(child)
            count += child_count
            valid = valid and child_valid
        return count, valid
    if isinstance(value, list | tuple):
        found = [_submission_proof(item) for item in value]
        return sum(item[0] for item in found), all(item[1] for item in found)
    return 0, True


def _domain_state(path: Path) -> dict[str, Any]:
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
            db.row_factory = sqlite3.Row
            integrity = _integrity(db)
            if not integrity:
                raise ProductBlocker("domain EvidenceStore integrity failed")
            records = db.execute(
                "SELECT record_id, record_type, payload_json "
                "FROM immutable_records ORDER BY record_id"
            ).fetchall()
            outbox = db.execute(
                "SELECT idempotency_key, state, attempt_count "
                "FROM notification_outbox ORDER BY idempotency_key"
            ).fetchall()
    except sqlite3.DatabaseError as exc:
        raise ProductBlocker("domain EvidenceStore SQLite read failed") from exc
    shadows = [
        json.loads(row["payload_json"]) for row in records if row["record_type"] == "shadow_order"
    ]
    return {
        "integrity_ok": integrity,
        "record_ids": [row["record_id"] for row in records],
        "outbox": [dict(row) for row in outbox],
        "shadow_count": len(shadows),
        "all_not_submitted": all(
            row.get("submission_status") == "NOT_SUBMITTED"
            and row.get("venue_submitted", False) is False
            for row in shadows
        ),
    }


def _safe_artifact(value: Any) -> None:
    wire = json.dumps(value, sort_keys=True).lower()
    forbidden = (
        "api_key",
        "api_secret",
        "private_key",
        "wallet_address",
        "account_address",
        "account_id",
        "authorization",
        "bearer ",
        "webhook",
        "raw_log",
    )
    if any(marker in wire for marker in forbidden):
        raise QualificationGap("artifact includes private or secret-shaped data")
    if re.search(r"(ghp_[a-z0-9]{20}|sk-[a-z0-9]{20}|begin [a-z ]*private key)", wire):
        raise QualificationGap("artifact includes secret-shaped content")


def _write_result(path: Path, result: dict[str, Any]) -> None:
    _safe_artifact(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    path.write_bytes(encoded)


def _release_and_environment(candidate: Path, sha: str, tree: str) -> dict[str, Any]:
    _mark_stage("RELEASE_MANIFEST")
    from scripts import check_dependency_lock as locks
    from scripts.verify_exact_release import (
        build_release_manifest,
        release_paths,
        verify_staged_release,
    )
    from trader_assist_v0.nautilus_e4.host import assert_exact_nautilus_version
    from trader_assist_v0.nautilus_e4.safety import assert_public_only

    release = build_release_manifest(candidate, release_sha=sha, release_tree=tree)
    with tempfile.TemporaryDirectory(prefix="q1-release-") as temporary:
        staged = Path(temporary)
        for original in release_paths(candidate):
            target = staged / original.relative_to(candidate)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
        if (staged / ".git").exists():
            raise QualificationGap("staged release unexpectedly includes Git state")
        verify_staged_release(
            staged,
            release,
            expected_release_sha=sha,
            expected_release_tree=tree,
            expected_manifest_digest=str(release["manifest_sha256"]),
        )
    _mark_stage("DEPENDENCY_LOCKS")
    runtime = locks._read_lock(str(candidate / "requirements-runtime.lock"))
    pilot = locks._read_lock(str(candidate / "requirements-nautilus-pilot.lock"))
    if pilot != {"nautilus-trader": ("2.0.0rc5", locks.PILOT_WHEEL_SHA256)}:
        raise QualificationGap("pilot lock identity differs")
    locks._verify_installed(runtime, pilot, project_distribution_expected=False)
    _mark_stage("TARGET_IMPORT")
    locks._verify_target_import(candidate / "src")
    if importlib.util.find_spec("trader_assist_v0") is None:
        raise QualificationGap("candidate import is absent")
    try:
        importlib.metadata.distribution("trader-assist-v0")
    except importlib.metadata.PackageNotFoundError:
        pass
    else:
        raise QualificationGap("project distribution installed in target venv")
    _assert_import_origins(candidate)
    _mark_stage("TARGET_PIP")
    host_python = (
        Path(sys.base_prefix) / "bin" / f"python{sys.version_info.major}.{sys.version_info.minor}"
    )
    if subprocess.run(
        (str(host_python), "-m", "pip", "--python", sys.executable, "check"),
        capture_output=True,
        check=False,
    ).returncode:
        raise QualificationGap("target pip check failed")
    _mark_stage("TARGET_RUNTIME")
    if (
        platform.system() != "Linux"
        or platform.machine() != "x86_64"
        or sys.version_info[:2] != (3, 12)
    ):
        raise QualificationGap("target platform differs from Ubuntu x86_64 Python 3.12")
    rc5 = assert_exact_nautilus_version()
    proof = assert_public_only(env=os.environ)
    return {
        "release_manifest_digest": release["manifest_sha256"],
        "runtime_identity": (
            f"{platform.system()}-{platform.machine()}-Python-{platform.python_version()}"
        ),
        "nautilus_version": rc5,
        "dependency_closure": {
            "runtime_count": len(runtime),
            "pilot_count": len(pilot),
            "pip_check": True,
        },
        "import_origin": str((candidate / "src" / "trader_assist_v0").resolve()),
        "zero_write_proof": proof.model_dump(mode="json"),
    }


def _fixture(root: Path, sha: str, tree: str) -> dict[str, Any]:
    from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
    from trader_assist_v0.multi_asset_shadow.hyperliquid_public import (
        HyperliquidPublicClient,
        PublicDataError,
    )
    from trader_assist_v0.multi_asset_shadow.models import (
        AssetClass,
        MarketIdentity,
        MarketLifecycle,
        RegistryMarket,
        RegistryTier,
        RegistryVersion,
    )
    from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
    from trader_assist_v0.nautilus_e4.contracts import (
        MarketExpression,
        PitUniverseSnapshot,
        RunManifest,
    )
    from trader_assist_v0.nautilus_e4.storage import EvidenceStore as E4EvidenceStore

    observed = datetime.now(UTC)
    try:
        public_meta = HyperliquidPublicClient().metadata("")
    except PublicDataError as exc:
        raise ProviderIncomplete("public MAIN metadata unavailable") from exc
    if not isinstance(public_meta, dict) or not isinstance(public_meta.get("universe"), list):
        raise QualificationGap("public MAIN metadata shape unavailable")
    selected = [
        item
        for item in public_meta["universe"]
        if isinstance(item, dict) and item.get("name") == "ETH"
    ]
    if len(selected) != 1 or type(selected[0].get("szDecimals")) is not int:
        raise QualificationGap("public ETH perpetual metadata unavailable")
    meta = selected[0]
    size_decimals = meta["szDecimals"]
    metadata_hash = sha256_hex(canonical_json_bytes(meta))
    identity = MarketIdentity.create(dex="MAIN", coin="ETH")
    market = RegistryMarket(
        display="ETH",
        tier=RegistryTier.P0,
        identity=identity,
        asset_class=AssetClass.CRYPTO,
        size_decimals=size_decimals,
        price_max_decimals=6 - size_decimals,
        max_leverage=Decimal(str(meta["maxLeverage"]))
        if meta.get("maxLeverage") is not None
        else None,
        is_hip3=False,
        market_status="ACTIVE",
        lifecycle=MarketLifecycle.ACTIVE,
        metadata_observed_at=observed,
        metadata_hash=metadata_hash,
    )
    expression = MarketExpression(
        market_id=identity.market_id,
        dex="MAIN",
        provider_coin="ETH",
        instrument_id="ETH-PERP.HYPERLIQUID",
        expression_id="q1-eth-main",
        instrument_metadata_version="PUBLIC_MAIN_META_V1",
        instrument_metadata_hash=metadata_hash,
    )
    snapshot = PitUniverseSnapshot.create(observed_at_ns=time.time_ns(), expressions=(expression,))
    manifest = RunManifest.create(
        run_id=f"q1-eth-{sha[:12]}",
        git_sha=sha,
        git_tree=tree,
        snapshot=snapshot,
        process_epoch=f"q1-process-{sha[:12]}",
        continuity_epoch=f"q1-continuity-{sha[:12]}",
        admission_epoch=f"q1-admission-{sha[:12]}",
        capture_configuration={"market": identity.market_id, "public_only": True},
        subscription_policy={
            "discovery": [identity.market_id],
            "watch": [identity.market_id],
            "actionable": [identity.market_id],
        },
        trial_ledger_id="q1-three-setup-qualification",
    )
    e4_root = root / "e4"
    e4 = E4EvidenceStore(e4_root)
    e4.initialize(manifest, snapshot)
    registry = MarketRegistryManager(
        root / "registry",
        metadata_validator=lambda item: item.metadata_hash == metadata_hash
        and item.identity == identity,
    )
    version = RegistryVersion.create(version="q1-eth-main", created_at=observed, markets=(market,))
    registry.stage(version)
    registry.request_apply(version.version)
    return {
        "market": market,
        "snapshot": snapshot,
        "manifest": manifest,
        "registry": version,
        "e4_root": e4_root,
    }


class MemoryNotificationAdapter:
    """Duck-typed product dispatcher port; no transport or destination exists."""

    def __init__(self) -> None:
        self.attempted: list[str] = []

    def deliver(self, envelope: Any) -> Any:
        from trader_assist_v0.multi_asset_shadow.notification_engine.delivery import WebhookResponse

        self.attempted.append(envelope.idempotency_key)
        return WebhookResponse(status_code=204)


def _compose(root: Path, fixture: dict[str, Any], adapter: MemoryNotificationAdapter) -> Any:
    from nautilus_trader.model import AggregationSource, BarAggregation, BarType, PriceType

    from trader_assist_v0.multi_asset_shadow.bootstrap import MultiAssetProductionBootstrap
    from trader_assist_v0.multi_asset_shadow.e4_markettruth import E4MarketTruthProjection
    from trader_assist_v0.multi_asset_shadow.notification_engine.delivery import OutboxDispatcher
    from trader_assist_v0.multi_asset_shadow.planning import CostModel
    from trader_assist_v0.multi_asset_shadow.production import E4ThreeSetupProductionApplication
    from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
    from trader_assist_v0.multi_asset_shadow.shadow_records import EvidenceStore
    from trader_assist_v0.nautilus_e4.capture import SubscriptionPolicy
    from trader_assist_v0.nautilus_e4.host import build_capture_strategy, build_public_data_node
    from trader_assist_v0.nautilus_e4.storage import EvidenceStore as E4EvidenceStore

    market, snapshot, manifest = fixture["market"], fixture["snapshot"], fixture["manifest"]
    e4 = E4EvidenceStore(fixture["e4_root"])
    evidence = EvidenceStore(root / "evidence.sqlite")
    holder: dict[str, Any] = {}
    registry = MarketRegistryManager(
        root / "registry",
        metadata_validator=lambda item: holder["projection"].validate_market(item),
    )
    selected = registry.active() or registry.pending_version()
    if selected is None or selected.content_hash != fixture["registry"].content_hash:
        raise ProductBlocker("Registry identity changed")
    policy = SubscriptionPolicy(
        discovery=frozenset((market.identity.market_id,)),
        watch=frozenset((market.identity.market_id,)),
        actionable=frozenset((market.identity.market_id,)),
    )
    bars = tuple(
        f"{snapshot.expressions[0].instrument_id}-{minute}-MINUTE-LAST-EXTERNAL"
        for minute in (1, 5)
    )
    parsed = tuple(BarType.from_str(item) for item in bars)
    if not all(
        str(bar.instrument_id) == snapshot.expressions[0].instrument_id
        and bar.spec.step == minute
        and bar.spec.aggregation is BarAggregation.MINUTE
        and bar.spec.price_type is PriceType.LAST
        and bar.aggregation_source is AggregationSource.EXTERNAL
        for bar, minute in zip(parsed, (1, 5), strict=True)
    ):
        raise QualificationGap("exact external LAST 1m/5m BarTypes are unavailable")
    node = build_public_data_node()
    capture = build_capture_strategy(
        manifest=manifest,
        snapshot=snapshot,
        policy=policy,
        bar_types=bars,
        evidence_root=fixture["e4_root"],
    )
    projection = E4MarketTruthProjection(
        e4_store=e4,
        domain_evidence=evidence,
        registry=registry,
        manifest=manifest,
        snapshot=snapshot,
        warmup_health=lambda: capture.warmup_health,
        capture_health=lambda: capture.capture_health,
        clock_ms=lambda: time.time_ns() // 1_000_000,
    )
    holder["projection"] = projection
    if not projection.validate_market(market):
        raise ProductBlocker("Registry/PIT metadata binding failed")
    registry.bind_e4_evidence_authority(projection)
    node.add_strategy(capture)
    bootstrap = MultiAssetProductionBootstrap.compose_e4(
        registry=registry,
        projection=projection,
        evidence=evidence,
        cost_model=CostModel("q1-fixture", Decimal(0), Decimal(0), Decimal(2)),
        release_sha=manifest.git_sha,
    )
    return E4ThreeSetupProductionApplication(
        node=node,
        capture=capture,
        bootstrap=bootstrap,
        dispatcher=OutboxDispatcher(outbox=bootstrap.outbox, adapter=cast(Any, adapter)),
        clock=lambda: datetime.now(UTC),
        notification_poll_seconds=1,
    )


async def _segment(app: Any, *, seconds: int, old_event: Any | None = None) -> dict[str, Any]:
    from trader_assist_v0.multi_asset_shadow.runtime import (
        BoundaryMode,
        E4ThreeSetupRuntime,
        RuntimeReadinessSnapshot,
    )

    shutdown = asyncio.Event()
    reports: list[dict[str, Any]] = []
    original = app.e4_runtime.on_finalized_5m

    async def observe(bar: Any, mode: Any) -> Any:
        assert original is not None
        report = await original(bar, mode)
        reports.append(
            {
                "boundary_open_time_ms": bar.open_time_ms,
                "mode": mode.value,
                "disposition": report.disposition.value,
            }
        )
        return report

    app.e4_runtime.on_finalized_5m = observe
    selected = app.bootstrap.registry.active() or app.bootstrap.registry.pending_version()
    if selected is None:
        raise ProductBlocker("segment has no Registry authority")
    task = asyncio.create_task(app.run(shutdown))
    started = time.monotonic()
    child_exit = False
    partial_nonactionable = False
    try:
        while time.monotonic() - started < seconds:
            if task.done():
                child_exit = True
                break
            observation = app.capture.public_provider_observation
            warmup = app.capture.warmup_health
            if (
                observation.get("provider_observation_pass")
                and warmup.get("readiness") == "READY"
                and reports
            ):
                break
            await asyncio.sleep(0.5)
        if old_event is not None:
            old_open_ms = old_event.source.ts_event // 1_000_000
            active = app.bootstrap.registry.active()
            if (
                active is not None
                and any(item.lifecycle.value == "ACTIVE" for item in active.markets)
                and not old_event.out_of_order
            ):
                # Exercise the candidate runtime's own readiness gate with a
                # hash-valid partial snapshot; no product callback may fire.
                partial = E4ThreeSetupRuntime(
                    projection=app.projection,
                    registry=app.bootstrap.registry,
                    clock=lambda: datetime.fromtimestamp((old_open_ms + 300_001) / 1000, UTC),
                )
                snapshot = RuntimeReadinessSnapshot.create(
                    registry_version=active.version,
                    registry_content_hash=active.content_hash,
                    data_ready=False,
                    ready_market_ids=(),
                    failed_market_ids=(),
                    latest_closed_5m_open_time_ms=old_open_ms,
                    observed_at_ms=old_open_ms + 300_001,
                )
                partial.readiness_snapshot = lambda: snapshot  # type: ignore[method-assign]
                partial_calls: list[str] = []

                async def partial_callback(_bar: Any, _mode: Any) -> Any:
                    partial_calls.append("actionable")
                    raise ProductBlocker("partial readiness reached product boundary callback")

                partial.on_finalized_5m = partial_callback
                await partial._on_5m(old_event)
                partial_nonactionable = not partial_calls
            while (
                int(time.time() * 1000) <= old_open_ms + 360_000
                and time.monotonic() - started < seconds
            ):
                await asyncio.sleep(0.5)
            if int(time.time() * 1000) > old_open_ms + 360_000:
                await app.e4_runtime._on_5m(old_event)
        try:
            readiness = app.e4_runtime.readiness_snapshot()
            readiness_result = {
                "data_ready": readiness.data_ready,
                "snapshot_hash": readiness.snapshot_hash,
            }
        except Exception as exc:
            if app.bootstrap.registry.active() is not None:
                raise ProductBlocker("active Registry readiness failed") from exc
            readiness_result = {"data_ready": False, "snapshot_hash": ""}
        result = {
            "public_provider_observation": app.capture.public_provider_observation,
            "warmup": app.capture.warmup_health,
            "readiness": readiness_result,
            "boundary_observations": reports,
            "closed_bar_integrity_ok": _integrity(app.projection.store.connection),
            "closed_bar_row_count": app.projection.store.connection.execute(
                "SELECT COUNT(*) FROM closed_bars"
            ).fetchone()[0],
            "child_exit_unexpected": child_exit,
            "partial_nonactionable": partial_nonactionable,
            "capture_health": {
                "admitted_observer_failure_count": len(
                    app.capture.capture_health.get("admitted_observer_failures", ())
                )
            },
            "registry_version": selected.version,
            "registry_hash": selected.content_hash,
            "application_class": type(app).__name__,
        }
    finally:
        shutdown.set()
        try:
            await asyncio.wait_for(task, timeout=30)
        except Exception as exc:
            raise ProductBlocker("product application child failed during segment") from exc
    if any(
        item["mode"] == BoundaryMode.LIVE_ACTIONABLE.value
        for item in reports
        if old_event is not None
        and item["boundary_open_time_ms"] == old_event.source.ts_event // 1_000_000
    ):
        raise ProductBlocker("old boundary became newly actionable")
    return result


def _fixture_from_retained(root: Path) -> dict[str, Any]:
    from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
    from trader_assist_v0.nautilus_e4.storage import EvidenceStore as E4EvidenceStore

    e4_root = root / "e4"
    e4 = E4EvidenceStore(e4_root)
    snapshot, manifest = e4.load_snapshot(), e4.load_manifest()
    registry = MarketRegistryManager(root / "registry", metadata_validator=lambda _: True)
    selected = registry.active() or registry.pending_version()
    if selected is None or len(selected.markets) != 1:
        raise ProductBlocker("retained Registry identity is missing")
    return {
        "market": selected.markets[0],
        "snapshot": snapshot,
        "manifest": manifest,
        "registry": selected,
        "e4_root": e4_root,
    }


async def _child_segment(
    candidate: Path, root: Path, index: int, seconds: int, sha: str, tree: str
) -> dict[str, Any]:
    _mark_stage("CHILD_RETAINED")
    from trader_assist_v0.nautilus_e4.storage import EvidenceStore as E4EvidenceStore

    fixture = _fixture_from_retained(root)
    manifest = fixture["manifest"]
    if manifest.git_sha != sha or manifest.git_tree != tree:
        raise QualificationGap("segment candidate release identity drift")
    e4 = E4EvidenceStore(fixture["e4_root"])
    retained = e4.load_admissions()
    old = (
        next(
            (
                event
                for event in reversed(retained)
                if event.source.data_kind.value == "BAR"
                and "-5-MINUTE-LAST-EXTERNAL" in event.source.event_context
            ),
            None,
        )
        if index == 2
        else None
    )
    adapter = MemoryNotificationAdapter()
    _mark_stage("CHILD_COMPOSITION")
    app = _compose(root, fixture, adapter)
    reconstructed_rows = app.projection.store.connection.execute(
        "SELECT COUNT(*) FROM closed_bars"
    ).fetchone()[0]
    _mark_stage("CHILD_LIVE")
    segment = await _segment(app, seconds=seconds, old_event=old)
    _assert_import_origins(candidate)
    checkpoint = e4.load_runtime_checkpoint(manifest)
    return {
        "classification": "SEGMENT_COMPLETE",
        "pid": os.getpid(),
        "segment": segment,
        "domain": _domain_state(root / "evidence.sqlite"),
        "adapter_attempt_count": len(adapter.attempted),
        "adapter_type": type(adapter).__name__,
        "reconstructed_bar_count": reconstructed_rows,
        "checkpoint_hash": None if checkpoint is None else checkpoint.checkpoint_hash,
        "old_boundary_open_ms": None if old is None else old.source.ts_event // 1_000_000,
    }


def _run_child(
    candidate: Path, root: Path, index: int, sha: str, tree: str, seconds: int
) -> dict[str, Any]:
    target = root / f"segment-{index}-result.json"
    command = (
        sys.executable,
        str(Path(__file__).resolve()),
        "--candidate",
        str(candidate),
        "--candidate-sha",
        sha,
        "--candidate-tree",
        tree,
        "--result",
        str(target),
        "--root",
        str(root),
        "--internal-segment",
        str(index),
        "--segment-seconds",
        str(seconds),
    )
    completed = subprocess.run(command, capture_output=True, check=False, timeout=seconds + 60)
    _mark_stage("CHILD_RESULT")
    if not target.is_file():
        raise QualificationGap("child process produced no bounded result")
    result = json.loads(target.read_text(encoding="utf-8"))
    if completed.returncode != 0 or result.get("classification") != "SEGMENT_COMPLETE":
        diagnostic = _child_diagnostic(result)
        if result.get("classification") == "PRODUCT_BLOCKER":
            raise ProductBlocker("candidate product segment failed", diagnostic)
        if result.get("classification") == "PROVIDER_DATA_INCOMPLETE":
            raise ProviderIncomplete("candidate provider segment incomplete", diagnostic)
        raise QualificationGap("child segment execution surface failed", diagnostic)
    return cast(dict[str, Any], result)


async def qualify(candidate: Path, root: Path, sha: str, tree: str, seconds: int) -> dict[str, Any]:
    matrix = {key: False for key in MANDATORY}
    _mark_stage("CANDIDATE_IDENTITY")
    exact_identity(candidate, sha, tree)
    matrix["B01"] = True
    env = _release_and_environment(candidate, sha, tree)
    for key in ("B02", "B03", "B04", "B05"):
        matrix[key] = True
    _mark_stage("PUBLIC_FIXTURE")
    fixture = _fixture(root, sha, tree)
    manifest, snapshot, version = fixture["manifest"], fixture["snapshot"], fixture["registry"]
    from trader_assist_v0.nautilus_e4.storage import EvidenceStore as E4EvidenceStore

    _mark_stage("E4_STORE")
    e4 = E4EvidenceStore(fixture["e4_root"])
    matrix.update({key: True for key in ("B06", "B07", "B08", "B09", "B10", "B11", "B12")})
    if e4.load_manifest() != manifest or e4.load_snapshot() != snapshot:
        raise ProductBlocker("E4 store identity failed")
    _mark_stage("CHILD_1")
    first_child = _run_child(candidate, root, 1, sha, tree, seconds)
    first, first_domain = first_child["segment"], first_child["domain"]
    retained = e4.load_admissions()
    old = next(
        (
            event
            for event in reversed(retained)
            if event.source.data_kind.value == "BAR"
            and "-5-MINUTE-LAST-EXTERNAL" in event.source.event_context
        ),
        None,
    )
    _mark_stage("CHILD_2")
    second_child = _run_child(candidate, root, 2, sha, tree, seconds)
    second, second_domain = second_child["segment"], second_child["domain"]
    reconstructed_rows = second_child["reconstructed_bar_count"]
    segments = e4.load_process_segments()
    checkpoint = e4.load_runtime_checkpoint(manifest)
    checkpoint_state = checkpoint.state if checkpoint is not None else {}
    execution_count, execution_safe = _submission_proof(checkpoint_state)
    first_ids, second_ids = set(first_domain["record_ids"]), set(second_domain["record_ids"])
    first_outbox = {item["idempotency_key"] for item in first_domain["outbox"]}
    second_outbox = {item["idempotency_key"] for item in second_domain["outbox"]}
    provider_ready = all(
        segment["public_provider_observation"].get("provider_observation_pass")
        and segment["warmup"].get("readiness") == "READY"
        and segment["readiness"].get("data_ready") is True
        for segment in (first, second)
    )
    matrix.update(
        {
            "C01": first_child["pid"] != second_child["pid"]
            and first["application_class"]
            == second["application_class"]
            == "E4ThreeSetupProductionApplication",
            "C02": env["nautilus_version"] == "2.0.0rc5",
            "C03": bool(first["public_provider_observation"].get("quote_observed")),
            "C04": bool(first["public_provider_observation"].get("trade_observed")),
            "C05": bool(first["public_provider_observation"].get("depth10_observed")),
            "C06": bool(
                first["public_provider_observation"].get("finalized_bar_evidence_persisted")
            ),
            "C07": first["warmup"].get("readiness") == "READY",
            "C08": first["readiness"]["data_ready"] is True
            and bool(first["readiness"]["snapshot_hash"]),
            "C09": any(
                item["boundary_open_time_ms"] % 300_000 == 0
                for item in first["boundary_observations"]
            ),
            "C10": old is not None
            and second["partial_nonactionable"]
            and not any(
                item["mode"] == "LIVE_ACTIONABLE"
                for item in second["boundary_observations"]
                if item["boundary_open_time_ms"] == old.source.ts_event // 1_000_000
            ),
            "C11": first_domain["all_not_submitted"]
            and second_domain["all_not_submitted"]
            and execution_safe,
            "C12": manifest.real_exec_client_registered is False,
            "C13": first_child["adapter_type"]
            == second_child["adapter_type"]
            == "MemoryNotificationAdapter",
            "C14": not first["child_exit_unexpected"] and not second["child_exit_unexpected"],
            "C15": first_domain["integrity_ok"],
            "C16": first["closed_bar_integrity_ok"],
            "D01": not first["child_exit_unexpected"],
            "D02": e4.load_manifest() == manifest
            and e4.load_snapshot() == snapshot
            and first["registry_version"] == second["registry_version"]
            and first["registry_hash"] == second["registry_hash"],
            "D03": old is not None
            and reconstructed_rows > 0
            and not any(
                item["mode"] == "LIVE_ACTIONABLE"
                for item in second["boundary_observations"]
                if item["boundary_open_time_ms"] == old.source.ts_event // 1_000_000
            ),
            "D04": old is not None
            and any(
                item["mode"] == "RECOVERY_CONTEXT_ONLY"
                for item in second["boundary_observations"]
                if item["boundary_open_time_ms"] == old.source.ts_event // 1_000_000
            ),
            "D05": first_ids <= second_ids and len(second_domain["record_ids"]) == len(second_ids),
            "D06": first_outbox <= second_outbox
            and len(second_domain["outbox"]) == len(second_outbox),
            "D07": first_child["pid"] != second_child["pid"]
            and len(segments) >= 2
            and checkpoint is not None
            and first_child["checkpoint_hash"] is not None
            and segments[1].get("predecessor_checkpoint_hash") == first_child["checkpoint_hash"],
            "D08": second_domain["integrity_ok"],
            "D09": second["closed_bar_integrity_ok"],
            "D10": not second["child_exit_unexpected"],
        }
    )
    product_failure = not all(
        (
            matrix["C11"],
            matrix["C14"],
            matrix["C15"],
            matrix["C16"],
            matrix["D05"],
            matrix["D06"],
            matrix["D07"],
            matrix["D08"],
            matrix["D09"],
            matrix["D10"],
        )
    )
    decisive_provider_proof = provider_ready and all(
        matrix[key] for key in ("C03", "C04", "C05", "C06", "C07", "C09", "C10", "D03", "D04")
    )
    cause = (
        "PRODUCT_BLOCKER"
        if product_failure
        else None
        if decisive_provider_proof
        else "PROVIDER_DATA_INCOMPLETE"
    )
    adversarial = adversarial_matrix(matrix)
    result = {
        "schema": SCHEMA,
        "harness_head_sha": _git(Path(__file__).resolve().parents[1], "rev-parse", "HEAD"),
        "harness_head_tree": _git(Path(__file__).resolve().parents[1], "rev-parse", "HEAD^{tree}"),
        "candidate_sha": sha,
        "candidate_tree": tree,
        "candidate_release_manifest_digest": env["release_manifest_digest"],
        "runtime_identity": env["runtime_identity"],
        "nautilus_version": env["nautilus_version"],
        "dependency_closure": env["dependency_closure"],
        "import_origin": env["import_origin"],
        "zero_write_proof": env["zero_write_proof"],
        "e4_manifest_hash": manifest.manifest_hash,
        "pit_snapshot_hash": snapshot.snapshot_hash,
        "registry_version": version.version,
        "registry_hash": version.content_hash,
        "bar_types": [
            f"{snapshot.expressions[0].instrument_id}-{n}-MINUTE-LAST-EXTERNAL" for n in (1, 5)
        ],
        "public_provider_observation": [
            first["public_provider_observation"],
            second["public_provider_observation"],
        ],
        "warmup_readiness": [first["warmup"], second["warmup"]],
        "boundary_observations": [first["boundary_observations"], second["boundary_observations"]],
        "stale_partial_adversarial_result": {
            "old_boundary_recovery_only": matrix["D04"],
            "partial_readiness_nonactionable": second["partial_nonactionable"],
        },
        "shadow_not_submitted_counts": {
            "shadow_by_segment": [first_domain["shadow_count"], second_domain["shadow_count"]],
            "execution_chain_evidence_count": execution_count,
        },
        "outbox_idempotency_evidence": {
            "first_count": len(first_domain["outbox"]),
            "second_count": len(second_domain["outbox"]),
            "adapter_attempt_count": first_child["adapter_attempt_count"]
            + second_child["adapter_attempt_count"],
        },
        "process_segment_restart_evidence": {
            "segment_count": len(segments),
            "checkpoint_present": checkpoint is not None,
            "reconstructed_bar_count": reconstructed_rows,
            "process_ids_distinct": first_child["pid"] != second_child["pid"],
        },
        "sqlite_integrity": {
            "domain_evidence": [first_domain["integrity_ok"], second_domain["integrity_ok"]],
            "product_closed_bar_store": {
                "storage_mode": "sqlite::memory:",
                "reconstruction_source": "retained_e4_admissions",
                "segment_integrity": [
                    first["closed_bar_integrity_ok"],
                    second["closed_bar_integrity_ok"],
                ],
            },
        },
        "child_exit_status": [first["child_exit_unexpected"], second["child_exit_unexpected"]],
        "acceptance_matrix": matrix,
        "adversarial_matrix": adversarial,
        "artifact_hashes": e4.artifact_hashes(),
        "classification": (
            classify(matrix, cause)
            if all(adversarial.values())
            else classify(matrix, cause or "HARNESS_OR_EXECUTION_SURFACE_GAP")
        ),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-sha", default=BASE_SHA)
    parser.add_argument("--candidate-tree", default=BASE_TREE)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--segment-seconds", type=int, default=900)
    parser.add_argument("--internal-segment", type=int, choices=(1, 2))
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    if not 60 <= args.segment_seconds <= 1200:
        parser.error("segment window must be 60..1200 seconds")
    if args.internal_segment is not None:
        if args.root is None:
            parser.error("internal segment requires --root")
        try:
            _mark_stage("CHILD_IDENTITY")
            exact_identity(args.candidate.resolve(), args.candidate_sha, args.candidate_tree)
            child_result = asyncio.run(
                _child_segment(
                    args.candidate.resolve(),
                    args.root,
                    args.internal_segment,
                    args.segment_seconds,
                    args.candidate_sha,
                    args.candidate_tree,
                )
            )
        except ProductBlocker as exc:
            child_result = {"classification": "PRODUCT_BLOCKER", **_failure_diagnostic(exc)}
        except ProviderIncomplete as exc:
            child_result = {
                "classification": "PROVIDER_DATA_INCOMPLETE", **_failure_diagnostic(exc)
            }
        except Exception as exc:
            child_result = {
                "classification": "HARNESS_OR_EXECUTION_SURFACE_GAP", **_failure_diagnostic(exc)
            }
        _write_result(args.result, child_result)
        return 0 if child_result["classification"] == "SEGMENT_COMPLETE" else 2
    example_path = (
        Path(__file__).resolve().parents[1]
        / "deploy/p4a/evidence/three-setup-q1-qualification-v1.json.example"
    )
    result: dict[str, Any] = json.loads(example_path.read_text(encoding="utf-8"))
    result.update(
        candidate_sha=args.candidate_sha,
        candidate_tree=args.candidate_tree,
        harness_head_sha=_git(Path(__file__).resolve().parents[1], "rev-parse", "HEAD"),
        harness_head_tree=_git(Path(__file__).resolve().parents[1], "rev-parse", "HEAD^{tree}"),
    )
    _mark_stage("ENTRY")
    try:
        with tempfile.TemporaryDirectory(prefix="q1-three-setup-") as temporary:
            result = asyncio.run(
                qualify(
                    args.candidate.resolve(),
                    Path(temporary),
                    args.candidate_sha,
                    args.candidate_tree,
                    args.segment_seconds,
                )
            )
    except ProductBlocker as exc:
        result.update(classification="PRODUCT_BLOCKER", **_failure_diagnostic(exc))
    except ProviderIncomplete as exc:
        result.update(classification="PROVIDER_DATA_INCOMPLETE", **_failure_diagnostic(exc))
    except SystemExit as exc:
        result.update(
            classification="HARNESS_OR_EXECUTION_SURFACE_GAP",
            **_failure_diagnostic(exc),
        )
    except Exception as exc:
        result.update(
            classification="HARNESS_OR_EXECUTION_SURFACE_GAP",
            **_failure_diagnostic(exc),
        )
    try:
        _mark_stage("ARTIFACT_WRITE")
        _write_result(args.result, result)
    except QualificationGap:
        result = json.loads(example_path.read_text(encoding="utf-8"))
        result.update(reason_stage="ARTIFACT_WRITE", reason_code="ArtifactRedactionFailure")
        _write_result(args.result, result)
    print(f"Q1_CLASSIFICATION={result['classification']}")
    return 0 if result["classification"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
