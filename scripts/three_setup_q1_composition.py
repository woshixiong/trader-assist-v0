#!/usr/bin/env python3
# mypy: disable-error-code="import-untyped,import-not-found"
"""Exact-candidate, public-only Three Setup constructor qualification."""

from __future__ import annotations

import argparse
import ast
import importlib.metadata
import inspect
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

BASE_SHA = "e3c0c67cc3d787bdf5044bdf598699a78652bdb5"
BASE_TREE = "d5d76f6994ac4b635ddd6ea0647a7050af9a3a49"
INSTRUMENT = "ETH-USD-PERP.HYPERLIQUID"
SCHEMA = "trader-assist-v0/three-setup-q1-composition/v1"
STAGES = (
    "ENTRY",
    "CANDIDATE_IDENTITY",
    "TARGET_ENVIRONMENT",
    "RELEASE_AND_IMPORT",
    "FIXTURE_IDENTITY",
    "NODE_BUILD",
    "CAPTURE_BUILD",
    "PROJECTION_BUILD",
    "REGISTRY_BIND",
    "BOOTSTRAP_COMPOSE",
    "APPLICATION_COMPOSE",
    "ZERO_WRITE_INSPECTION",
    "SAFE_TEARDOWN",
    "ARTIFACT_WRITE",
)
CQA = tuple(f"CQA{i:02}" for i in range(1, 19))
CQH = tuple(f"CQH{i:02}" for i in range(1, 13))
CODES = frozenset(
    {
        "NONE",
        "CANDIDATE_IDENTITY_MISMATCH",
        "CONTROL_CANDIDATE_CROSSOVER",
        "TARGET_RUNTIME_MISMATCH",
        "RELEASE_OR_IMPORT_MISMATCH",
        "FIXTURE_INSTRUMENT_MISMATCH",
        "BAR_TYPE_IDENTITY_MISMATCH",
        "E4_DURABLE_IDENTITY_MISMATCH",
        "REGISTRY_METADATA_MISMATCH",
        "RETAINED_REFERENCE_MISMATCH",
        "DOMAIN_STORE_OBSERVER_FAILURE",
        "DOMAIN_STORE_OWNERSHIP_MISMATCH",
        "DOMAIN_STORE_CLOSE_FAILURE",
        "REGISTRY_SELECTION_FAILURE",
        "NODE_CONSTRUCTION_FAILURE",
        "CAPTURE_CONSTRUCTION_FAILURE",
        "PROJECTION_CONSTRUCTION_FAILURE",
        "REGISTRY_BIND_FAILURE",
        "BOOTSTRAP_COMPOSITION_FAILURE",
        "APPLICATION_COMPOSITION_FAILURE",
        "BUILDER_AUDIT_UNAVAILABLE",
        "BUILDER_AUDIT_FAILURE",
        "EXPECTED_DATA_REGISTRATION_MISSING",
        "EXECUTION_CAPABILITY_PRESENT",
        "ZERO_WRITE_PROOF_UNAVAILABLE",
        "UNSTARTED_TEARDOWN_FAILURE",
        "COMPOSITION_STAGE_UNRESOLVED",
        "CHILD_CRASH_OR_TIMEOUT",
        "ARTIFACT_SCHEMA_FAILURE",
        "ACCEPTANCE_INCOMPLETE",
    }
)
TYPE_TOKENS = frozenset(
    {
        "ValueError",
        "RuntimeError",
        "TypeError",
        "OSError",
        "RegistryError",
        "E4ProjectionError",
        "ThreeSetupProductionError",
        "ExactReleaseError",
        "AssertionError",
        "SystemExit",
        "Unknown",
    }
)
FIXED_TIME = datetime(2026, 9, 27, tzinfo=UTC)
FIXED_NS = 1_801_000_000_000_000_000


class Gap(RuntimeError):
    def __init__(self, code: str, stage: str | None = None) -> None:
        if code not in CODES:
            raise ValueError("unknown bounded code")
        super().__init__(code)
        self.code = code
        self.stage = stage


class ControlReplan(Gap):
    """The frozen qualification surface cannot observe a required authority."""


@dataclass
class StageLedger:
    attempted: list[str] = field(default_factory=list)
    completed: list[str] = field(default_factory=list)
    current: str = "ENTRY"

    def enter(self, stage: str) -> None:
        if stage not in STAGES:
            raise Gap("COMPOSITION_STAGE_UNRESOLVED")
        index = STAGES.index(stage)
        if index != len(self.completed) or stage in self.attempted:
            raise Gap("COMPOSITION_STAGE_UNRESOLVED")
        self.current = stage
        self.attempted.append(stage)

    def done(self, stage: str) -> None:
        if self.current != stage or self.attempted[-1] != stage:
            raise Gap("COMPOSITION_STAGE_UNRESOLVED")
        self.completed.append(stage)


@dataclass
class StoreLedger:
    store: Any = None
    state: str = "UNCONSTRUCTED"
    close_owner: str = "NONE"
    close_attempt_count: int = 0
    close_succeeded: bool = False
    duplicate_close: bool = False
    caller: str = "CANDIDATE"
    bootstrap: Any = None

    def capture(self, store: Any) -> None:
        if self.store is not None or self.state != "UNCONSTRUCTED":
            raise Gap("DOMAIN_STORE_OWNERSHIP_MISMATCH")
        self.store = store
        self.state = "CONSTRUCTED_OWNED_BY_HARNESS"

    def transfer(self, bootstrap: Any, evidence: Any) -> None:
        if (
            self.state != "CONSTRUCTED_OWNED_BY_HARNESS"
            or self.close_attempt_count != 0
            or evidence is not self.store
            or bootstrap.evidence is not self.store
        ):
            raise Gap("DOMAIN_STORE_OWNERSHIP_MISMATCH")
        self.bootstrap = bootstrap
        self.state = "TRANSFERRED_TO_BOOTSTRAP"

    def observed_close(
        self, original: Callable[..., Any], instance: Any, *args: Any, **kwargs: Any
    ) -> Any:
        if instance is not self.store:
            return original(instance, *args, **kwargs)
        self.close_attempt_count += 1
        if self.close_attempt_count > 1:
            self.duplicate_close = True
        self.close_owner = self.caller
        try:
            result = original(instance, *args, **kwargs)
        except BaseException:
            self.state = "CLOSE_FAILED"
            raise
        self.close_succeeded = True
        self.state = "CLOSED"
        return result

    def teardown(self) -> None:
        if self.store is None or self.close_attempt_count:
            return
        if self.state == "TRANSFERRED_TO_BOOTSTRAP":
            self.caller = "BOOTSTRAP"
            self.bootstrap.close()
        elif self.state == "CONSTRUCTED_OWNED_BY_HARNESS":
            self.caller = "HARNESS"
            self.store.close()
        else:
            raise Gap("DOMAIN_STORE_OWNERSHIP_MISMATCH")

    def safe(self) -> bool:
        return (
            self.store is not None
            and self.close_attempt_count == 1
            and self.close_succeeded
            and not self.duplicate_close
            and self.state == "CLOSED"
        )


@dataclass
class BuilderAudit:
    expected_builder: Any = None
    built_node: Any = None
    registrations: dict[str, int] = field(
        default_factory=lambda: {
            "data": 0,
            "exec": 0,
            "sim_exec": 0,
            "order": 0,
            "signer": 0,
        }
    )
    data_type: str = "UNRUN"
    installed: bool = False
    restored: bool = False
    bypassed: bool = False
    _saved: list[tuple[type, str, Any]] = field(default_factory=list)

    def install(self, builder_type: type) -> None:
        names = {
            "add_data_client": "data",
            "add_exec_client": "exec",
            "add_simulated_exec_client": "sim_exec",
            "build": "build",
        }
        for optional, kind in (
            ("add_execution_client", "exec"),
            ("add_order_client", "order"),
            ("add_signer", "signer"),
        ):
            if hasattr(builder_type, optional):
                names[optional] = kind
        for required in (
            "add_data_client",
            "add_exec_client",
            "add_simulated_exec_client",
            "build",
        ):
            if not callable(getattr(builder_type, required, None)):
                raise ControlReplan("BUILDER_AUDIT_UNAVAILABLE", "NODE_BUILD")
        try:
            for name, kind in names.items():
                original = builder_type.__dict__.get(name)
                if original is None or not callable(getattr(builder_type, name, None)):
                    raise ControlReplan("BUILDER_AUDIT_UNAVAILABLE", "NODE_BUILD")

                def observed(
                    receiver: Any,
                    *args: Any,
                    _original: Any = original,
                    _kind: str = kind,
                    **kwargs: Any,
                ) -> Any:
                    if self.expected_builder is None:
                        self.expected_builder = receiver
                    elif receiver is not self.expected_builder:
                        self.bypassed = True
                    if _kind != "build":
                        self.registrations[_kind] += 1
                        if _kind == "data" and len(args) >= 2:
                            self.data_type = type(args[1]).__name__
                    result = _original(receiver, *args, **kwargs)
                    if _kind == "build":
                        self.built_node = result
                    return result

                setattr(builder_type, name, observed)
                if getattr(builder_type, name) is not observed:
                    raise ControlReplan("BUILDER_AUDIT_UNAVAILABLE", "NODE_BUILD")
                self._saved.append((builder_type, name, original))
            self.installed = True
        except BaseException as exc:
            self.restore()
            if isinstance(exc, Gap):
                raise
            raise ControlReplan("BUILDER_AUDIT_UNAVAILABLE", "NODE_BUILD") from exc

    def restore(self) -> None:
        failed = False
        for cls, name, original in reversed(self._saved):
            try:
                setattr(cls, name, original)
                if cls.__dict__.get(name) is not original:
                    failed = True
            except BaseException:
                failed = True
        self._saved.clear()
        self.restored = not failed
        if failed:
            raise ControlReplan("BUILDER_AUDIT_UNAVAILABLE", "SAFE_TEARDOWN")

    def valid(self, node: Any) -> bool:
        return (
            self.installed
            and not self.bypassed
            and self.expected_builder is not None
            and self.built_node is node
            and self.registrations == {"data": 1, "exec": 0, "sim_exec": 0, "order": 0, "signer": 0}
            and self.data_type == "HyperliquidDataClientFactory"
        )


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ("git", "-C", str(root), *args), capture_output=True, text=True, check=False
    )
    if proc.returncode:
        raise Gap("CANDIDATE_IDENTITY_MISMATCH", "CANDIDATE_IDENTITY")
    return proc.stdout.strip()


def _verify_checkout(control: Path, candidate: Path, control_head: str) -> None:
    if (
        control.resolve() == candidate.resolve()
        or candidate.resolve() in control.resolve().parents
        or control.resolve() in candidate.resolve().parents
    ):
        raise Gap("CONTROL_CANDIDATE_CROSSOVER", "CANDIDATE_IDENTITY")
    if (
        _git(candidate, "rev-parse", "HEAD") != BASE_SHA
        or _git(candidate, "rev-parse", "HEAD^{tree}") != BASE_TREE
    ):
        raise Gap("CANDIDATE_IDENTITY_MISMATCH", "CANDIDATE_IDENTITY")
    if _git(control, "rev-parse", "HEAD") != control_head:
        raise Gap("CANDIDATE_IDENTITY_MISMATCH", "CANDIDATE_IDENTITY")
    if _git(candidate, "status", "--porcelain=v1", "--untracked-files=all"):
        raise Gap("CANDIDATE_IDENTITY_MISMATCH", "CANDIDATE_IDENTITY")


def _verify_runtime() -> None:
    import trader_assist_v0
    from trader_assist_v0.nautilus_e4.host import assert_exact_nautilus_version
    from trader_assist_v0.nautilus_e4.safety import assert_public_only

    if (
        platform.system() != "Linux"
        or platform.machine() != "x86_64"
        or sys.version_info[:2] != (3, 12)
    ):
        raise Gap("TARGET_RUNTIME_MISMATCH", "TARGET_ENVIRONMENT")
    if assert_exact_nautilus_version() != "2.0.0rc5" or not assert_public_only(env=os.environ):
        raise Gap("TARGET_RUNTIME_MISMATCH", "TARGET_ENVIRONMENT")
    if importlib.metadata.version("nautilus-trader") != "2.0.0rc5":
        raise Gap("TARGET_RUNTIME_MISMATCH", "TARGET_ENVIRONMENT")
    if not Path(trader_assist_v0.__file__).resolve().is_file():
        raise Gap("RELEASE_OR_IMPORT_MISMATCH", "TARGET_ENVIRONMENT")


def _verify_release(candidate: Path) -> str:
    candidate = candidate.resolve(strict=True)
    from scripts import check_dependency_lock as locks
    from scripts.verify_exact_release import (
        build_release_manifest,
        release_paths,
        verify_staged_release,
    )

    runtime = locks._read_lock(str(candidate / "requirements-runtime.lock"))
    pilot = locks._read_lock(str(candidate / "requirements-nautilus-pilot.lock"))
    if pilot != {"nautilus-trader": ("2.0.0rc5", locks.PILOT_WHEEL_SHA256)}:
        raise Gap("TARGET_RUNTIME_MISMATCH", "RELEASE_AND_IMPORT")
    locks._verify_installed(runtime, pilot, project_distribution_expected=False)
    host_python = (
        Path(sys.base_prefix) / "bin" / f"python{sys.version_info.major}.{sys.version_info.minor}"
    )
    pip_check = subprocess.run(
        (str(host_python), "-m", "pip", "--python", sys.executable, "check"),
        capture_output=True,
        check=False,
    )
    if pip_check.returncode:
        raise Gap("TARGET_RUNTIME_MISMATCH", "RELEASE_AND_IMPORT")
    locks._verify_target_import(candidate / "src")
    for name in (
        "trader_assist_v0.multi_asset_shadow.production",
        "trader_assist_v0.nautilus_e4.host",
        "scripts.verify_exact_release",
    ):
        module = __import__(name, fromlist=["*"])
        origin = getattr(module, "__file__", None)
        if origin is None or not Path(origin).resolve().is_relative_to(candidate.resolve()):
            raise Gap("CONTROL_CANDIDATE_CROSSOVER", "RELEASE_AND_IMPORT")
    release = build_release_manifest(candidate, release_sha=BASE_SHA, release_tree=BASE_TREE)
    with tempfile.TemporaryDirectory(prefix="q1-comp-release-") as temp:
        stage = Path(temp)
        for original in release_paths(candidate):
            target = stage / original.relative_to(candidate)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
        if (stage / ".git").exists():
            raise Gap("RELEASE_OR_IMPORT_MISMATCH", "RELEASE_AND_IMPORT")
        verify_staged_release(
            stage,
            release,
            expected_release_sha=BASE_SHA,
            expected_release_tree=BASE_TREE,
            expected_manifest_digest=str(release["manifest_sha256"]),
        )
    return str(release["manifest_sha256"])


def _fixture(root: Path) -> tuple[Any, Any, Any, Any, Any]:
    from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
    from trader_assist_v0.multi_asset_shadow.models import (
        AssetClass,
        MarketIdentity,
        MarketLifecycle,
        RegistryMarket,
        RegistryTier,
        RegistryVersion,
    )
    from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
    from trader_assist_v0.multi_asset_shadow.shadow_records import EvidenceStore as DomainStore
    from trader_assist_v0.nautilus_e4.contracts import (
        MarketExpression,
        PitUniverseSnapshot,
        RunManifest,
    )
    from trader_assist_v0.nautilus_e4.storage import EvidenceStore as E4Store

    metadata = {"name": "ETH", "szDecimals": 4, "maxLeverage": 40}
    metadata_hash = sha256_hex(canonical_json_bytes(metadata))
    identity = MarketIdentity.create(dex="MAIN", coin="ETH")
    market = RegistryMarket(
        display="ETH",
        tier=RegistryTier.P0,
        identity=identity,
        asset_class=AssetClass.CRYPTO,
        size_decimals=4,
        price_max_decimals=2,
        max_leverage=Decimal("40"),
        is_hip3=False,
        market_status="ACTIVE",
        lifecycle=MarketLifecycle.ACTIVE,
        metadata_observed_at=FIXED_TIME,
        metadata_hash=metadata_hash,
    )
    expression = MarketExpression(
        market_id=identity.market_id,
        dex="MAIN",
        provider_coin="ETH",
        instrument_id=INSTRUMENT,
        expression_id="q1-eth-main",
        instrument_metadata_version="SYNTHETIC_PUBLIC_MAIN_V1",
        instrument_metadata_hash=metadata_hash,
    )
    snapshot = PitUniverseSnapshot.create(observed_at_ns=FIXED_NS, expressions=(expression,))
    manifest = RunManifest.create(
        run_id="q1-composition-frozen",
        git_sha=BASE_SHA,
        git_tree=BASE_TREE,
        snapshot=snapshot,
        process_epoch="q1-composition-process",
        continuity_epoch="q1-composition-continuity",
        admission_epoch="q1-composition-admission",
        capture_configuration={"market": identity.market_id, "public_only": True},
        subscription_policy={
            "discovery": [identity.market_id],
            "watch": [identity.market_id],
            "actionable": [identity.market_id],
        },
        trial_ledger_id="q1-composition-synthetic",
    )
    e4 = E4Store(root / "e4")
    e4.initialize(manifest, snapshot)
    if e4.load_manifest() != manifest or e4.load_snapshot() != snapshot or e4.load_admissions():
        raise Gap("E4_DURABLE_IDENTITY_MISMATCH", "FIXTURE_IDENTITY")
    registry = MarketRegistryManager(
        root / "registry",
        metadata_validator=lambda item: item.identity == identity
        and item.metadata_hash == metadata_hash,
    )
    version = RegistryVersion.create(
        version="q1-eth-main", created_at=FIXED_TIME, markets=(market,)
    )
    registry.stage(version)
    registry.request_apply(version.version)
    if (
        registry.active() is not None
        or registry.pending_version() != version
        or any(registry.history.glob("*.json"))
    ):
        raise Gap("REGISTRY_METADATA_MISMATCH", "FIXTURE_IDENTITY")
    domain = DomainStore(root / "evidence.sqlite")
    try:
        retained = domain._connection.execute("SELECT COUNT(*) FROM immutable_records").fetchone()[
            0
        ]
        outbox = domain._connection.execute("SELECT COUNT(*) FROM notification_outbox").fetchone()[
            0
        ]
        if retained or outbox:
            raise Gap("RETAINED_REFERENCE_MISMATCH", "FIXTURE_IDENTITY")
    finally:
        domain.close()
    return market, snapshot, manifest, version, e4


def _check_fixture_identity(
    market: Any, snapshot: Any, manifest: Any, version: Any, e4: Any
) -> None:
    expressions = snapshot.expressions
    if len(expressions) != 1 or expressions[0].instrument_id != INSTRUMENT:
        raise Gap("FIXTURE_INSTRUMENT_MISMATCH", "FIXTURE_IDENTITY")
    expression = expressions[0]
    if (
        market.identity.market_id != expression.market_id
        or market.identity.dex != expression.dex
        or market.identity.coin != expression.provider_coin
        or market.metadata_hash != expression.instrument_metadata_hash
        or market.price_max_decimals != 6 - market.size_decimals
        or len(version.markets) != 1
        or version.markets[0] != market
    ):
        raise Gap("REGISTRY_METADATA_MISMATCH", "FIXTURE_IDENTITY")
    if (
        manifest.git_sha != BASE_SHA
        or manifest.git_tree != BASE_TREE
        or manifest.pit_snapshot_hash != snapshot.snapshot_hash
        or manifest.pit_snapshot_id != snapshot.snapshot_id
    ):
        raise Gap("E4_DURABLE_IDENTITY_MISMATCH", "FIXTURE_IDENTITY")
    try:
        if e4.load_manifest() != manifest or e4.load_snapshot() != snapshot:
            raise Gap("E4_DURABLE_IDENTITY_MISMATCH", "FIXTURE_IDENTITY")
    except Gap:
        raise
    except (OSError, ValueError) as exc:
        raise Gap("E4_DURABLE_IDENTITY_MISMATCH", "FIXTURE_IDENTITY") from exc


def _bar_identity_matches(instrument: str, parsed_instruments: tuple[str, ...]) -> bool:
    return instrument == INSTRUMENT and parsed_instruments == (INSTRUMENT, INSTRUMENT)


def _bars() -> tuple[str, str]:
    from nautilus_trader.model import AggregationSource, BarAggregation, BarType, PriceType

    bars = tuple(f"{INSTRUMENT}-{minute}-MINUTE-LAST-EXTERNAL" for minute in (1, 5))
    parsed = tuple(BarType.from_str(bar) for bar in bars)
    if not _bar_identity_matches(INSTRUMENT, tuple(str(bar.instrument_id) for bar in parsed)):
        raise Gap("BAR_TYPE_IDENTITY_MISMATCH", "FIXTURE_IDENTITY")
    if any(
        str(bar.instrument_id) != INSTRUMENT
        or bar.spec.step != minute
        or bar.spec.aggregation is not BarAggregation.MINUTE
        or bar.spec.price_type is not PriceType.LAST
        or bar.aggregation_source is not AggregationSource.EXTERNAL
        for bar, minute in zip(parsed, (1, 5), strict=True)
    ):
        raise Gap("BAR_TYPE_IDENTITY_MISMATCH", "FIXTURE_IDENTITY")
    return bars  # type: ignore[return-value]


def _safe_result() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "classification": "HARNESS_OR_EXECUTION_SURFACE_GAP",
        "reason_stage": "ENTRY",
        "reason_code": "ACCEPTANCE_INCOMPLETE",
        "reason_type": "UNRUN",
        "candidate_sha": BASE_SHA,
        "candidate_tree": BASE_TREE,
        "control_head": "UNRUN",
        "release_digest": "UNRUN",
        "manifest_hash": "UNRUN",
        "pit_hash": "UNRUN",
        "registry_hash": "UNRUN",
        "instrument_id": "UNRUN",
        "stages_attempted": ["ENTRY"],
        "stages_completed": [],
        "cqa": {key: False for key in CQA},
        "cqh": {key: False for key in CQH},
        "builder": {
            "data": 0,
            "exec": 0,
            "sim_exec": 0,
            "order": 0,
            "signer": 0,
            "data_type": "UNRUN",
            "same_builder_node": False,
            "restored": False,
        },
        "store": {
            "state": "UNCONSTRUCTED",
            "close_owner": "NONE",
            "close_attempt_count": 0,
            "close_succeeded": False,
        },
        "zero_write": False,
        "node_disposed": False,
        "run_started": False,
        "teardown_attempted": False,
        "control_replan_required": False,
    }


def _validate_result(result: dict[str, Any]) -> None:
    if (
        result["schema"] != SCHEMA
        or result["reason_stage"] not in STAGES
        or result["reason_code"] not in CODES
    ):
        raise Gap("ARTIFACT_SCHEMA_FAILURE", "ARTIFACT_WRITE")
    if set(result["cqa"]) != set(CQA) or set(result["cqh"]) != set(CQH):
        raise Gap("ARTIFACT_SCHEMA_FAILURE", "ARTIFACT_WRITE")
    raw = json.dumps(result, sort_keys=True, separators=(",", ":"))
    if re.search(
        r"(?i)(api[_-]?key|api[_-]?secret|private[_-]?key|wallet|account[_-]?id|authorization|traceback|exception:|https?://)",
        raw,
    ):
        raise Gap("ARTIFACT_SCHEMA_FAILURE", "ARTIFACT_WRITE")
    if result["classification"] == "PASS" and (
        result["stages_attempted"] != list(STAGES)
        or result["stages_completed"] != list(STAGES)
        or result["reason_code"] != "NONE"
        or not all(result["cqa"].values())
        or not all(result["cqh"].values())
        or result["run_started"]
        or not result["node_disposed"]
        or not result["zero_write"]
    ):
        raise Gap("ACCEPTANCE_INCOMPLETE", "ARTIFACT_WRITE")


def _write_result(path: Path, result: dict[str, Any]) -> None:
    _validate_result(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    nxt = path.with_name(path.name + ".next")
    nxt.write_text(
        json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    nxt.replace(path)


def _install_store_observers(
    production: Any, stores: StoreLedger, patch: Callable[[Any, str, Any], None]
) -> None:
    domain_type = production.EvidenceStore
    original_close = domain_type.close

    def construct_store(*args: Any, **kwargs: Any) -> Any:
        value = domain_type(*args, **kwargs)
        stores.capture(value)
        return value

    def close_store(instance: Any, *args: Any, **kwargs: Any) -> Any:
        return stores.observed_close(original_close, instance, *args, **kwargs)

    patch(domain_type, "close", close_store)
    patch(production, "EvidenceStore", construct_store)


def _observe_product(
    production: Any, host: Any, ledger: StageLedger, stores: StoreLedger, audit: BuilderAudit
) -> tuple[Any, Any, Any]:
    from nautilus_trader.common import Environment
    from nautilus_trader.live import LiveNode
    from nautilus_trader.model import TraderId

    from trader_assist_v0.multi_asset_shadow.bootstrap import MultiAssetProductionBootstrap
    from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager

    builder_type = type(
        LiveNode.builder("TRADEOS-Q1-AUDIT", TraderId("TRADEOS-Q1-AUDIT"), Environment.LIVE)
    )
    audit.install(builder_type)
    originals: list[tuple[Any, str, Any]] = []
    objects: dict[str, Any] = {}

    def patch(obj: Any, name: str, replacement: Any) -> None:
        prior = obj.__dict__[name] if isinstance(obj, type) else getattr(obj, name)
        setattr(obj, name, replacement)
        originals.append((obj, name, prior))

    def wrap(stage: str, original: Callable[..., Any], key: str) -> Callable[..., Any]:
        def call(*args: Any, **kwargs: Any) -> Any:
            ledger.enter(stage)
            value = original(*args, **kwargs)
            objects[key] = value
            ledger.done(stage)
            return value

        return call

    original_bind = MarketRegistryManager.bind_e4_evidence_authority

    def bind(instance: Any, authority: Any) -> Any:
        ledger.enter("REGISTRY_BIND")
        result = original_bind(instance, authority)
        ledger.done("REGISTRY_BIND")
        return result

    original_bootstrap = MultiAssetProductionBootstrap.compose_e4

    def compose_bootstrap(cls: type[Any], /, **kwargs: Any) -> Any:
        ledger.enter("BOOTSTRAP_COMPOSE")
        bootstrap = original_bootstrap(**kwargs)
        stores.transfer(bootstrap, kwargs["evidence"])
        objects["bootstrap"] = bootstrap
        ledger.done("BOOTSTRAP_COMPOSE")
        return bootstrap

    try:
        _install_store_observers(production, stores, patch)
        patch(
            host, "build_public_data_node", wrap("NODE_BUILD", host.build_public_data_node, "node")
        )
        patch(
            host,
            "build_capture_strategy",
            wrap("CAPTURE_BUILD", host.build_capture_strategy, "capture"),
        )
        patch(
            production,
            "E4MarketTruthProjection",
            wrap("PROJECTION_BUILD", production.E4MarketTruthProjection, "projection"),
        )
        patch(MarketRegistryManager, "bind_e4_evidence_authority", bind)
        patch(MultiAssetProductionBootstrap, "compose_e4", classmethod(compose_bootstrap))
        patch(
            production,
            "E4ThreeSetupProductionApplication",
            wrap(
                "APPLICATION_COMPOSE", production.E4ThreeSetupProductionApplication, "application"
            ),
        )
        return objects, originals, audit
    except BaseException:
        for obj, name, prior in reversed(originals):
            setattr(obj, name, prior)
        audit.restore()
        raise


def _zero_write(
    app: Any,
    node: Any,
    capture: Any,
    projection: Any,
    bootstrap: Any,
    audit: BuilderAudit,
    manifest: Any,
    factory_source: str,
) -> None:
    from trader_assist_v0.nautilus_e4.safety import assert_public_only

    proof = assert_public_only(env=os.environ)
    if not audit.valid(node):
        if any(audit.registrations[key] for key in ("exec", "sim_exec", "order", "signer")):
            raise Gap("EXECUTION_CAPABILITY_PRESENT", "ZERO_WRITE_INSPECTION")
        raise Gap("EXPECTED_DATA_REGISTRATION_MISSING", "ZERO_WRITE_INSPECTION")
    source = ast.parse(factory_source)
    calls = [
        n.func.attr
        for n in ast.walk(source)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    ]
    if calls.count("add_data_client") != 1 or any(
        name in calls
        for name in (
            "add_exec_client",
            "add_simulated_exec_client",
            "add_execution_client",
            "add_order_client",
            "add_signer",
        )
    ):
        raise Gap("ZERO_WRITE_PROOF_UNAVAILABLE", "ZERO_WRITE_INSPECTION")
    if (
        type(node).__name__ != "LiveNode"
        or app.node is not node
        or app.capture is not capture
        or app.projection is not projection
        or app.bootstrap is not bootstrap
        or app.e4_runtime is not bootstrap.runtime
    ):
        raise Gap("APPLICATION_COMPOSITION_FAILURE", "ZERO_WRITE_INSPECTION")
    if not projection.validate_market(
        (bootstrap.registry.active() or bootstrap.registry.pending_version()).markets[0]
    ):
        raise Gap("REGISTRY_METADATA_MISMATCH", "ZERO_WRITE_INSPECTION")
    if any(
        getattr(app, name, None) is not None
        for name in ("execution_client", "order_client", "signer")
    ):
        raise Gap("EXECUTION_CAPABILITY_PRESENT", "ZERO_WRITE_INSPECTION")
    config = getattr(node, "config", None)
    config = config() if callable(config) else config
    if config is not None:
        for name in (
            "exec_clients",
            "execution_clients",
            "execution_client",
            "order_client",
            "signer",
        ):
            if getattr(config, name, None) not in (None, False, (), {}, []):
                raise Gap("EXECUTION_CAPABILITY_PRESENT", "ZERO_WRITE_INSPECTION")
    if (
        any(
            getattr(manifest, name) is not False
            for name in ("private_api", "exchange_write", "real_exec_client_registered")
        )
        or proof.signing is not False
    ):
        raise Gap("EXECUTION_CAPABILITY_PRESENT", "ZERO_WRITE_INSPECTION")


def _composition_ready(result: dict[str, Any]) -> bool:
    """The child may finish successfully while its artifact remains non-PASS."""
    try:
        _validate_result(result)
        builder = result["builder"]
        store = result["store"]
        return (
            result["classification"] == "HARNESS_OR_EXECUTION_SURFACE_GAP"
            and result["reason_stage"] == "ARTIFACT_WRITE"
            and result["reason_code"] == "ACCEPTANCE_INCOMPLETE"
            and result["reason_type"] == "UNRUN"
            and result["candidate_sha"] == BASE_SHA
            and result["candidate_tree"] == BASE_TREE
            and result["stages_attempted"] == list(STAGES)
            and result["stages_completed"] == list(STAGES)
            and all(result["cqa"][key] is True for key in CQA[:-1])
            and result["cqa"]["CQA18"] is False
            and all(value is False for value in result["cqh"].values())
            and builder["data"] == 1
            and all(builder[key] == 0 for key in ("exec", "sim_exec", "order", "signer"))
            and builder["data_type"] == "HyperliquidDataClientFactory"
            and builder["same_builder_node"] is True
            and builder["restored"] is True
            and store["state"] == "CLOSED"
            and store["close_owner"] == "BOOTSTRAP"
            and store["close_attempt_count"] == 1
            and store["close_succeeded"] is True
            and result["zero_write"] is True
            and result["node_disposed"] is True
            and result["run_started"] is False
            and result["teardown_attempted"] is True
            and result["control_replan_required"] is False
        )
    except (Gap, KeyError, TypeError, ValueError):
        return False


def _finalize_result(
    intermediate: dict[str, Any],
    contracts: dict[str, Any],
    terminal: dict[str, Any],
    control_head: str,
    pr_number: str,
) -> dict[str, Any]:
    if not _composition_ready(intermediate):
        raise Gap("ACCEPTANCE_INCOMPLETE", "ARTIFACT_WRITE")
    if intermediate["control_head"] != control_head or not re.fullmatch(
        r"[0-9a-f]{40}", control_head
    ):
        raise Gap("CANDIDATE_IDENTITY_MISMATCH", "ARTIFACT_WRITE")
    if contracts != {
        "schema": SCHEMA,
        "check_name": "contracts",
        "control_head": control_head,
        "status": "completed",
        "conclusion": "success",
    }:
        raise Gap("ACCEPTANCE_INCOMPLETE", "ARTIFACT_WRITE")
    if terminal != {
        "schema": SCHEMA,
        "verified": True,
        "pr_number": pr_number,
        "control_head": control_head,
        "candidate_sha": BASE_SHA,
        "candidate_tree": BASE_TREE,
    }:
        raise Gap("CANDIDATE_IDENTITY_MISMATCH", "ARTIFACT_WRITE")
    final: dict[str, Any] = json.loads(json.dumps(intermediate))
    final["cqh"] = {key: True for key in CQH}
    final["cqa"]["CQA18"] = True
    final.update(classification="PASS", reason_code="NONE", reason_type="UNRUN")
    _validate_result(final)
    return final


def _run_child(control: Path, candidate: Path, control_head: str, result_path: Path) -> int:
    ledger = StageLedger()
    result = _safe_result()
    result["control_head"] = (
        control_head if re.fullmatch(r"[0-9a-f]{40}", control_head) else "UNRUN"
    )
    _write_result(result_path, result)
    stores = StoreLedger()
    audit = BuilderAudit()
    objects: dict[str, Any] = {}
    originals: list[tuple[Any, str, Any]] = []
    root_created = False
    failure: Gap | None = None
    exception_type = "UNRUN"
    production: Any = None
    fixture_checked = False
    bars_checked = False
    product_composed = False
    try:
        ledger.enter("ENTRY")
        ledger.done("ENTRY")
        ledger.enter("CANDIDATE_IDENTITY")
        _verify_checkout(control, candidate, control_head)
        ledger.done("CANDIDATE_IDENTITY")
        ledger.enter("TARGET_ENVIRONMENT")
        _verify_runtime()
        ledger.done("TARGET_ENVIRONMENT")
        ledger.enter("RELEASE_AND_IMPORT")
        result["release_digest"] = _verify_release(candidate)
        ledger.done("RELEASE_AND_IMPORT")
        ledger.enter("FIXTURE_IDENTITY")
        from trader_assist_v0.multi_asset_shadow import production as product
        from trader_assist_v0.multi_asset_shadow.planning import CostModel
        from trader_assist_v0.nautilus_e4 import host

        production = product
        root = production.THREE_SETUP_STATE_ROOT
        if root.exists():
            raise Gap("CANDIDATE_IDENTITY_MISMATCH", "FIXTURE_IDENTITY")
        root.mkdir(parents=True, exist_ok=False)
        root_created = True
        market, snapshot, manifest, version, e4 = _fixture(root)
        _check_fixture_identity(market, snapshot, manifest, version, e4)
        fixture_checked = True
        bars = _bars()
        bars_checked = True
        result.update(
            manifest_hash=manifest.manifest_hash,
            pit_hash=snapshot.snapshot_hash,
            registry_hash=version.content_hash,
            instrument_id=INSTRUMENT,
        )
        config = production.ThreeSetupProductionConfig(
            release_sha=BASE_SHA,
            evidence_store_path=production.THREE_SETUP_EVIDENCE_STORE_PATH,
            registry_root=production.THREE_SETUP_REGISTRY_ROOT,
            closed_bar_store_path=production.THREE_SETUP_CLOSED_BAR_STORE_PATH,
            cost_model=CostModel("q1-composition-synthetic", Decimal(0), Decimal(0), Decimal(2)),
            notification_poll_seconds=1,
            e4_evidence_root=e4.root,
            e4_manifest_path=e4.manifest_path,
            e4_snapshot_path=e4.snapshot_path,
            e4_bar_types=bars,
        )

        # Inert adapter: the application constructor stores it but never dispatches.
        class NoTransport:
            def deliver(self, _message: Any) -> Any:
                raise Gap("EXECUTION_CAPABILITY_PRESENT", "ZERO_WRITE_INSPECTION")

        factory_source = inspect.getsource(host.build_public_data_node)
        objects, originals, audit = _observe_product(production, host, ledger, stores, audit)
        objects["factory_source"] = factory_source
        # The public seam selects Registry before building the node. Stay at this stage until then.
        ledger.done("FIXTURE_IDENTITY")
        app = production.compose_three_setup_application(
            config=config, notification_adapter=NoTransport(), clock=lambda: FIXED_TIME
        )
        if app is not objects.get("application"):
            raise Gap("APPLICATION_COMPOSITION_FAILURE", "APPLICATION_COMPOSE")
        product_composed = True
        ledger.enter("ZERO_WRITE_INSPECTION")
        _zero_write(
            app,
            objects["node"],
            objects["capture"],
            objects["projection"],
            objects["bootstrap"],
            audit,
            manifest,
            objects["factory_source"],
        )
        ledger.done("ZERO_WRITE_INSPECTION")
        result["zero_write"] = True
    except BaseException as exc:
        exception_type = type(exc).__name__ if type(exc).__name__ in TYPE_TOKENS else "Unknown"
        if isinstance(exc, Gap):
            failure = exc
        elif (
            stores.store is not None
            and stores.close_attempt_count
            and ledger.current == "FIXTURE_IDENTITY"
        ):
            failure = Gap("REGISTRY_SELECTION_FAILURE", "FIXTURE_IDENTITY")
        else:
            stage_codes = {
                "NODE_BUILD": "NODE_CONSTRUCTION_FAILURE",
                "CAPTURE_BUILD": "CAPTURE_CONSTRUCTION_FAILURE",
                "PROJECTION_BUILD": "PROJECTION_CONSTRUCTION_FAILURE",
                "REGISTRY_BIND": "REGISTRY_BIND_FAILURE",
                "BOOTSTRAP_COMPOSE": "BOOTSTRAP_COMPOSITION_FAILURE",
                "APPLICATION_COMPOSE": "APPLICATION_COMPOSITION_FAILURE",
            }
            failure = Gap(
                stage_codes.get(ledger.current, "COMPOSITION_STAGE_UNRESOLVED"), ledger.current
            )
    finally:
        result["teardown_attempted"] = True
        if "ZERO_WRITE_INSPECTION" in ledger.completed:
            try:
                ledger.enter("SAFE_TEARDOWN")
            except Gap as exc:
                failure = failure or exc
        closers: tuple[tuple[str, Callable[[], Any]], ...] = (
            ("store", stores.teardown),
            (
                "projection",
                lambda: objects["projection"].close() if "projection" in objects else None,
            ),
            ("node", lambda: objects["node"].dispose() if "node" in objects else None),
        )
        for key, closer in closers:
            try:
                closer()
                if key == "node" and "node" in objects:
                    result["node_disposed"] = True
            except BaseException:
                failure = failure or Gap(
                    "DOMAIN_STORE_CLOSE_FAILURE"
                    if key == "store"
                    else "UNSTARTED_TEARDOWN_FAILURE",
                    "SAFE_TEARDOWN",
                )
        if stores.store is not None and not stores.safe():
            failure = failure or Gap("DOMAIN_STORE_CLOSE_FAILURE", "SAFE_TEARDOWN")
        try:
            for obj, name, prior in reversed(originals):
                setattr(obj, name, prior)
                if (
                    obj.__dict__[name] if isinstance(obj, type) else getattr(obj, name)
                ) is not prior:
                    raise Gap("DOMAIN_STORE_OBSERVER_FAILURE", "SAFE_TEARDOWN")
        except BaseException:
            failure = failure or Gap("DOMAIN_STORE_OBSERVER_FAILURE", "SAFE_TEARDOWN")
        try:
            audit.restore()
        except BaseException:
            failure = failure or ControlReplan("BUILDER_AUDIT_UNAVAILABLE", "SAFE_TEARDOWN")
        if "SAFE_TEARDOWN" in ledger.attempted and failure is None:
            ledger.done("SAFE_TEARDOWN")
        if root_created:
            try:
                shutil.rmtree(root)
            except BaseException:
                failure = failure or Gap("UNSTARTED_TEARDOWN_FAILURE", "SAFE_TEARDOWN")
    if failure is None and "SAFE_TEARDOWN" in ledger.completed:
        try:
            ledger.enter("ARTIFACT_WRITE")
            ledger.done("ARTIFACT_WRITE")
        except Gap as exc:
            failure = exc
    result["stages_attempted"] = ledger.attempted
    result["stages_completed"] = ledger.completed
    result["builder"] = {
        **audit.registrations,
        "data_type": audit.data_type,
        "same_builder_node": audit.built_node is objects.get("node")
        and audit.expected_builder is not None,
        "restored": audit.restored,
    }
    result["store"] = {
        "state": stores.state,
        "close_owner": stores.close_owner,
        "close_attempt_count": stores.close_attempt_count,
        "close_succeeded": stores.close_succeeded,
    }
    result["reason_type"] = exception_type
    result["control_replan_required"] = isinstance(failure, ControlReplan)
    if failure is None and len(ledger.completed) == len(STAGES):
        completed = set(ledger.completed)
        result["cqa"] = {
            "CQA01": "CANDIDATE_IDENTITY" in completed,
            "CQA02": "TARGET_ENVIRONMENT" in completed,
            "CQA03": "RELEASE_AND_IMPORT" in completed
            and re.fullmatch(r"[0-9a-f]{64}", result["release_digest"]) is not None,
            "CQA04": fixture_checked and result["instrument_id"] == INSTRUMENT,
            "CQA05": bars_checked,
            "CQA06": not result["run_started"],
            "CQA07": "NODE_BUILD" in completed and objects.get("node") is audit.built_node,
            "CQA08": "CAPTURE_BUILD" in completed and objects.get("capture") is not None,
            "CQA09": "PROJECTION_BUILD" in completed and objects.get("projection") is not None,
            "CQA10": result["zero_write"],
            "CQA11": "REGISTRY_BIND" in completed,
            "CQA12": "BOOTSTRAP_COMPOSE" in completed
            and stores.bootstrap is objects.get("bootstrap"),
            "CQA13": product_composed and "APPLICATION_COMPOSE" in completed,
            "CQA14": audit.valid(objects.get("node")) and audit.restored,
            "CQA15": stores.safe() and result["node_disposed"] and result["teardown_attempted"],
            "CQA16": result["schema"] == SCHEMA,
            "CQA17": result["stages_attempted"] == list(STAGES)
            and result["stages_completed"] == list(STAGES),
            "CQA18": False,
        }
        result["reason_stage"] = "ARTIFACT_WRITE"
        result["reason_code"] = "ACCEPTANCE_INCOMPLETE"
    else:
        result["reason_stage"] = (failure.stage or ledger.current) if failure else ledger.current
        result["reason_code"] = failure.code if failure else "ACCEPTANCE_INCOMPLETE"
    try:
        _write_result(result_path, result)
    except BaseException:
        minimal = _safe_result()
        minimal["reason_stage"] = "ARTIFACT_WRITE"
        minimal["reason_code"] = "ARTIFACT_SCHEMA_FAILURE"
        _write_result(result_path, minimal)
        return 1
    return 0 if _composition_ready(result) else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--control-head", required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument("--contracts-proof", type=Path)
    parser.add_argument("--terminal-proof", type=Path)
    parser.add_argument("--pr-number")
    args = parser.parse_args()
    if args.finalize:
        if not (args.contracts_proof and args.terminal_proof and args.pr_number):
            return 1
        try:
            _verify_checkout(args.control, args.candidate, args.control_head)
            intermediate = json.loads(args.result.read_text(encoding="utf-8"))
            contracts = json.loads(args.contracts_proof.read_text(encoding="utf-8"))
            terminal = json.loads(args.terminal_proof.read_text(encoding="utf-8"))
            final = _finalize_result(
                intermediate, contracts, terminal, args.control_head, args.pr_number
            )
            _write_result(args.result, final)
        except (Gap, OSError, ValueError, KeyError, TypeError):
            return 1
        return 0
    if args.child:
        return _run_child(args.control, args.candidate, args.control_head, args.result)
    initial = _safe_result()
    _write_result(args.result, initial)
    cmd = (
        sys.executable,
        str(Path(__file__).resolve()),
        "--control",
        str(args.control),
        "--candidate",
        str(args.candidate),
        "--control-head",
        args.control_head,
        "--result",
        str(args.result),
        "--child",
    )
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120, check=False
        )
    except subprocess.TimeoutExpired:
        result = json.loads(args.result.read_text())
        result.update(reason_stage="SAFE_TEARDOWN", reason_code="CHILD_CRASH_OR_TIMEOUT")
        _write_result(args.result, result)
        return 1
    try:
        result = json.loads(args.result.read_text())
        _validate_result(result)
    except (OSError, ValueError, KeyError, TypeError):
        return 1
    return 0 if proc.returncode == 0 and _composition_ready(result) else 1


if __name__ == "__main__":
    raise SystemExit(main())
