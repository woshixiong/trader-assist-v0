"""Focused negative proofs for the Q1 composition qualification harness."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "three_setup_q1_composition.py"
SPEC = importlib.util.spec_from_file_location("q1_composition_qualification", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
q1 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = q1
SPEC.loader.exec_module(q1)

from trader_assist_v0.multi_asset_shadow import production  # noqa: E402
from trader_assist_v0.multi_asset_shadow.planning import CostModel  # noqa: E402
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager  # noqa: E402


@contextmanager
def observed_domain(ledger):
    saved = []

    def install(obj, name, replacement):
        prior = obj.__dict__[name] if isinstance(obj, type) else getattr(obj, name)
        setattr(obj, name, replacement)
        saved.append((obj, name, prior))

    q1._install_store_observers(production, ledger, install)
    try:
        yield
    finally:
        for obj, name, prior in reversed(saved):
            setattr(obj, name, prior)


class FakeNode:
    def __init__(self):
        self.run_count = 0
        self.stop_count = 0
        self.cancel_count = 0
        self.dispose_count = 0

    def run(self):
        self.run_count += 1

    async def run_async(self):
        self.run_count += 1

    def handle(self):
        self.stop_count += 1
        return self

    def stop(self):
        self.stop_count += 1

    def dispose(self):
        self.dispose_count += 1


class HyperliquidDataClientFactory:
    pass


class FakeBuilder:
    def __init__(self):
        self.data = []
        self.execution = []

    def add_data_client(self, *args, **kwargs):
        self.data.append((args, kwargs))
        return self

    def add_exec_client(self, *args, **kwargs):
        self.execution.append((args, kwargs))
        return self

    def add_simulated_exec_client(self, *args, **kwargs):
        self.execution.append((args, kwargs))
        return self

    def build(self):
        return FakeNode()


class QualificationGuards(unittest.TestCase):
    def intermediate(self):
        result = q1._safe_result()
        result.update(
            control_head="1" * 40,
            reason_stage="ARTIFACT_WRITE",
            stages_attempted=list(q1.STAGES),
            stages_completed=list(q1.STAGES),
            zero_write=True,
            node_disposed=True,
            teardown_attempted=True,
        )
        result["cqa"] = {key: key != "CQA18" for key in q1.CQA}
        result["builder"].update(
            data=1,
            data_type="HyperliquidDataClientFactory",
            same_builder_node=True,
            restored=True,
        )
        result["store"].update(
            state="CLOSED", close_owner="BOOTSTRAP", close_attempt_count=1, close_succeeded=True
        )
        return result

    def proofs(self):
        contracts = {
            "schema": q1.SCHEMA,
            "check_name": "contracts",
            "control_head": "1" * 40,
            "status": "completed",
            "conclusion": "success",
        }
        terminal = {
            "schema": q1.SCHEMA,
            "verified": True,
            "pr_number": "123",
            "control_head": "1" * 40,
            "candidate_sha": q1.BASE_SHA,
            "candidate_tree": q1.BASE_TREE,
        }
        return contracts, terminal

    def test_composition_child_does_not_run_focused_tests(self):
        names = set(q1._run_child.__code__.co_names)
        self.assertNotIn("_run_adversarial_tests", names)
        self.assertNotIn("unittest", names)
        self.assertNotIn("pytest", names)

    def test_finalizer_refuses_false_runtime_predicate(self):
        result = self.intermediate()
        result["cqa"]["CQA15"] = False
        contracts, terminal = self.proofs()
        with self.assertRaises(q1.Gap):
            q1._finalize_result(result, contracts, terminal, "1" * 40, "123")

    def test_finalizer_refuses_missing_exact_head_contracts(self):
        result = self.intermediate()
        contracts, terminal = self.proofs()
        contracts["control_head"] = "2" * 40
        with self.assertRaises(q1.Gap):
            q1._finalize_result(result, contracts, terminal, "1" * 40, "123")

    def test_finalizer_refuses_missing_terminal_identity(self):
        result = self.intermediate()
        contracts, terminal = self.proofs()
        terminal["verified"] = False
        with self.assertRaises(q1.Gap):
            q1._finalize_result(result, contracts, terminal, "1" * 40, "123")

    def test_finalizer_pass_requires_all_proofs(self):
        result = self.intermediate()
        contracts, terminal = self.proofs()
        final = q1._finalize_result(result, contracts, terminal, "1" * 40, "123")
        self.assertEqual((final["classification"], final["reason_code"]), ("PASS", "NONE"))
        self.assertTrue(all(final["cqa"].values()))
        self.assertTrue(all(final["cqh"].values()))
        self.assertFalse(result["cqa"]["CQA18"])

    def fixture(self, stack: ExitStack, root: Path):
        state = root / "state"
        state.mkdir()
        stack.enter_context(patch.object(production, "THREE_SETUP_STATE_ROOT", state))
        stack.enter_context(
            patch.object(production, "THREE_SETUP_EVIDENCE_STORE_PATH", state / "evidence.sqlite")
        )
        stack.enter_context(
            patch.object(production, "THREE_SETUP_REGISTRY_ROOT", state / "registry")
        )
        stack.enter_context(
            patch.object(
                production, "THREE_SETUP_CLOSED_BAR_STORE_PATH", state / "closed-bars.sqlite"
            )
        )
        market, snapshot, manifest, version, e4 = q1._fixture(state)
        bars = tuple(f"{q1.INSTRUMENT}-{minute}-MINUTE-LAST-EXTERNAL" for minute in (1, 5))
        config = production.ThreeSetupProductionConfig(
            release_sha=q1.BASE_SHA,
            evidence_store_path=production.THREE_SETUP_EVIDENCE_STORE_PATH,
            registry_root=production.THREE_SETUP_REGISTRY_ROOT,
            closed_bar_store_path=production.THREE_SETUP_CLOSED_BAR_STORE_PATH,
            cost_model=CostModel("test", Decimal(0), Decimal(0), Decimal(2)),
            notification_poll_seconds=1,
            e4_evidence_root=e4.root,
            e4_manifest_path=e4.manifest_path,
            e4_snapshot_path=e4.snapshot_path,
            e4_bar_types=bars,
        )
        return market, snapshot, manifest, version, e4, config

    def test_cqh01_wrong_candidate_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            control, candidate = Path(tmp) / "control", Path(tmp) / "candidate"
            control.mkdir()
            candidate.mkdir()
            with patch.object(q1, "_git", return_value="0" * 40):
                with self.assertRaises(q1.Gap) as ctx:
                    q1._verify_checkout(control, candidate, "1" * 40)
            self.assertEqual(ctx.exception.code, "CANDIDATE_IDENTITY_MISMATCH")

    def test_cqh02_checkout_crossover(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(q1.Gap) as ctx:
                q1._verify_checkout(Path(tmp), Path(tmp), "1" * 40)
            self.assertEqual(ctx.exception.code, "CONTROL_CANDIDATE_CROSSOVER")

    def test_cqh03_old_instrument_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            market, snapshot, manifest, version, e4, _ = self.fixture(stack, Path(tmp))
            old_expression = snapshot.expressions[0].model_copy(
                update={"instrument_id": "ETH-PERP.HYPERLIQUID"}
            )
            wrong = snapshot.model_copy(update={"expressions": (old_expression,)})
            with self.assertRaises(q1.Gap) as caught:
                q1._check_fixture_identity(market, wrong, manifest, version, e4)
            self.assertEqual(caught.exception.code, "FIXTURE_INSTRUMENT_MISMATCH")

    def test_cqh04_wrong_bar_instrument_is_rejected(self):
        self.assertFalse(
            q1._bar_identity_matches(q1.INSTRUMENT, ("ETH-PERP.HYPERLIQUID", q1.INSTRUMENT))
        )

    def test_cqh05_manifest_pit_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            market, snapshot, manifest, version, e4, _ = self.fixture(stack, Path(tmp))
            wrong = manifest.model_copy(update={"pit_snapshot_hash": "0" * 64})
            with self.assertRaises(q1.Gap) as caught:
                q1._check_fixture_identity(market, snapshot, wrong, version, e4)
            self.assertEqual(caught.exception.code, "E4_DURABLE_IDENTITY_MISMATCH")

    def test_cqh06_registry_metadata_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            market, snapshot, manifest, version, e4, _ = self.fixture(stack, Path(tmp))
            wrong = market.model_copy(update={"metadata_hash": "0" * 64})
            with self.assertRaises(q1.Gap) as caught:
                q1._check_fixture_identity(wrong, snapshot, manifest, version, e4)
            self.assertEqual(caught.exception.code, "REGISTRY_METADATA_MISMATCH")

    def test_cqh07_durable_identity_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            market, snapshot, manifest, version, e4, _ = self.fixture(stack, Path(tmp))
            e4.manifest_path.write_text("{}")
            with self.assertRaises(q1.Gap) as caught:
                q1._check_fixture_identity(market, snapshot, manifest, version, e4)
            self.assertEqual(caught.exception.code, "E4_DURABLE_IDENTITY_MISMATCH")

    def test_cqh08_retained_reference_without_admission(self):
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            market, snapshot, manifest, _, e4, _ = self.fixture(stack, Path(tmp))
            from trader_assist_v0.multi_asset_shadow.e4_markettruth import (
                E4MarketTruthProjection,
                E4ProjectionError,
            )
            from trader_assist_v0.multi_asset_shadow.shadow_records import EvidenceStore

            domain = EvidenceStore(Path(tmp) / "state" / "evidence.sqlite")
            domain._connection.execute(
                "INSERT INTO immutable_records("
                "record_id,record_type,canonical_hash,identity_json,payload_json"
                ") VALUES (?,?,?,?,?)",
                (
                    "bad-ref",
                    "e4_market_bar_ref",
                    "0",
                    "{}",
                    json.dumps({"admission_hash": "0" * 64}),
                ),
            )
            domain._connection.commit()
            registry = MarketRegistryManager(
                Path(tmp) / "state" / "registry", metadata_validator=lambda _: True
            )
            with self.assertRaises(E4ProjectionError):
                E4MarketTruthProjection(
                    e4_store=e4,
                    domain_evidence=domain,
                    registry=registry,
                    manifest=manifest,
                    snapshot=snapshot,
                    warmup_health=lambda: {},
                    capture_health=lambda: {},
                    clock_ms=lambda: 0,
                )
            domain.close()

    def test_cqh09_same_builder_audit_rejects_exec(self):
        audit = q1.BuilderAudit()
        audit.install(FakeBuilder)
        try:
            builder = FakeBuilder()
            builder.add_data_client(None, HyperliquidDataClientFactory())
            builder.add_exec_client(object())
            node = builder.build()
            self.assertEqual(audit.registrations["exec"], 1)
            self.assertFalse(audit.valid(node))
        finally:
            audit.restore()
        self.assertTrue(audit.restored)

    def test_builder_audit_positive_and_restore(self):
        original = FakeBuilder.__dict__["add_data_client"]
        audit = q1.BuilderAudit()
        audit.install(FakeBuilder)
        try:
            builder = FakeBuilder()
            builder.add_data_client(None, HyperliquidDataClientFactory())
            node = builder.build()
            self.assertTrue(audit.valid(node))
        finally:
            audit.restore()
        self.assertIs(FakeBuilder.__dict__["add_data_client"], original)

    def test_cqh10_artifact_rejects_secret_shaped_text(self):
        result = q1._safe_result()
        result["extra"] = "api_key=bad"
        with self.assertRaises(q1.Gap):
            q1._validate_result(result)

    def test_cqh11_registry_candidate_close_exactly_once(self):
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            _, _, _, _, _, config = self.fixture(stack, Path(tmp))
            ledger = q1.StoreLedger()
            original_pending = MarketRegistryManager.pending_version
            calls = 0

            def pending(manager):
                nonlocal calls
                calls += 1
                return original_pending(manager) if calls == 1 else None

            fake_host = ModuleType("trader_assist_v0.nautilus_e4.host")
            fake_host.build_public_data_node = lambda: None
            fake_host.build_capture_strategy = lambda **_kwargs: None
            with (
                observed_domain(ledger),
                patch.object(MarketRegistryManager, "pending_version", pending),
                patch.dict(sys.modules, {"trader_assist_v0.nautilus_e4.host": fake_host}),
            ):
                with self.assertRaises(production.ThreeSetupProductionError):
                    production.compose_three_setup_application(
                        config=config, notification_adapter=object()
                    )
                ledger.teardown()
            self.assertEqual(ledger.close_attempt_count, 1)
            self.assertEqual(ledger.close_owner, "CANDIDATE")
            self.assertEqual(ledger.state, "CLOSED")
            self.assertIsNone(ledger.bootstrap)
            self.assertEqual(calls, 2)

    def test_cqh11_node_failure_harness_close_once(self):
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            _, _, _, _, _, config = self.fixture(stack, Path(tmp))
            ledger = q1.StoreLedger()
            fake_host = ModuleType("trader_assist_v0.nautilus_e4.host")
            fake_host.build_public_data_node = lambda: (_ for _ in ()).throw(RuntimeError("node"))
            fake_host.build_capture_strategy = lambda **_kwargs: None
            with (
                observed_domain(ledger),
                patch.dict(sys.modules, {"trader_assist_v0.nautilus_e4.host": fake_host}),
            ):
                with self.assertRaises(RuntimeError):
                    production.compose_three_setup_application(
                        config=config, notification_adapter=object()
                    )
                ledger.teardown()
            self.assertEqual(
                (ledger.close_attempt_count, ledger.close_owner, ledger.state),
                (1, "HARNESS", "CLOSED"),
            )
            self.assertIsNone(ledger.bootstrap)

    def test_cqh11_capture_failure_harness_close_once(self):
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            _, _, _, _, _, config = self.fixture(stack, Path(tmp))
            ledger = q1.StoreLedger()
            node = FakeNode()
            fake_host = ModuleType("trader_assist_v0.nautilus_e4.host")
            fake_host.build_public_data_node = lambda: node
            fake_host.build_capture_strategy = lambda **_kwargs: (_ for _ in ()).throw(
                RuntimeError("capture")
            )
            with (
                observed_domain(ledger),
                patch.dict(sys.modules, {"trader_assist_v0.nautilus_e4.host": fake_host}),
            ):
                with self.assertRaises(RuntimeError):
                    production.compose_three_setup_application(
                        config=config, notification_adapter=object()
                    )
                ledger.teardown()
                node.dispose()
            self.assertEqual(
                (ledger.close_attempt_count, ledger.close_owner, ledger.state),
                (1, "HARNESS", "CLOSED"),
            )
            self.assertEqual(
                (node.run_count, node.stop_count, node.cancel_count, node.dispose_count),
                (0, 0, 0, 1),
            )

    def test_failed_first_close_never_retries(self):
        ledger = q1.StoreLedger()

        class Broken:
            def close(self):
                raise RuntimeError("failed")

        obj = Broken()
        ledger.capture(obj)
        with self.assertRaises(RuntimeError):
            ledger.observed_close(Broken.close, obj)
        ledger.teardown()
        self.assertEqual((ledger.close_attempt_count, ledger.state), (1, "CLOSE_FAILED"))

    def test_bootstrap_transfer_closes_same_store_once(self):
        ledger = q1.StoreLedger()

        class Store:
            def close(self):
                pass

        obj = Store()
        ledger.capture(obj)

        class Bootstrap:
            evidence = obj

            def close(self):
                ledger.observed_close(Store.close, obj)

        bootstrap = Bootstrap()
        ledger.transfer(bootstrap, obj)
        ledger.teardown()
        self.assertEqual(
            (ledger.close_attempt_count, ledger.close_owner, ledger.state),
            (1, "BOOTSTRAP", "CLOSED"),
        )

    def test_cqh12_skipped_stage_cannot_pass(self):
        result = q1._safe_result()
        result["classification"] = "PASS"
        with self.assertRaises(q1.Gap):
            q1._validate_result(result)
        stages = q1.StageLedger()
        with self.assertRaises(q1.Gap):
            stages.enter("NODE_BUILD")


if __name__ == "__main__":
    unittest.main()
