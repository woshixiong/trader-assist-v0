from __future__ import annotations

import ast
import importlib.util
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from trader_assist_v0.jev.contracts import (
    ACTIVE_CONTEXT_MAX_AGE_SECONDS,
    FIVE_MINUTE_CLOSED_MAX_AGE_SECONDS,
    L2_MAX_AGE_SECONDS,
    METADATA_MAX_AGE_SECONDS,
    ONE_MINUTE_CLOSED_MAX_AGE_SECONDS,
    BBO,
    BlockReason,
    FreshnessInputs,
    L2Level,
    L2Snapshot,
    JevConfig,
    MarketIdentity,
    STATE_SCHEMA_VERSION,
    evaluate_freshness,
    evaluate_snapshot_publication_freshness,
    signal_is_fresh,
)


def _ns(seconds: float) -> int:
    return int(seconds * 1_000_000_000)


def _fresh(now_s: float = 100_000.0) -> tuple[int, FreshnessInputs]:
    now = _ns(now_s)
    return now, FreshnessInputs(
        l2_source_ts_ns=now - _ns(1),
        latest_1m_close_ts_ns=now - _ns(60),
        latest_5m_close_ts_ns=now - _ns(300),
        optional_active_context_ts_ns=now - _ns(5),
        metadata_ts_ns=now - _ns(60),
        bbo_value_ts_ns=now - _ns(60),
        latest_trade_ts_ns=None,
    )


def test_market_identity_is_configurable_and_has_no_market_literal() -> None:
    identity = MarketIdentity("ABC", "public-provider", "ABC-PERP")
    assert identity.market == "ABC"
    root = Path(__file__).parents[1] / "src" / "trader_assist_v0" / "jev"
    joined = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    assert "SKHX" not in joined


def test_l2_fails_closed_on_ordering_cross_and_invalid_bbo() -> None:
    bids = tuple(L2Level(100.0 - index, 1.0) for index in range(5))
    asks = tuple(L2Level(101.0 + index, 1.0) for index in range(5))
    valid = L2Snapshot(bids, asks, 1, 2, "unit")
    assert valid.bids[0].price == 100.0
    with pytest.raises(ValueError):
        L2Snapshot(tuple(reversed(bids)), asks, 1, 2, "unit")
    with pytest.raises(ValueError):
        L2Snapshot(tuple(L2Level(101.0 - index, 1.0) for index in range(5)), asks, 1, 2, "unit")
    with pytest.raises(ValueError):
        BBO(101.0, 1.0, 101.0, 1.0, 1, 2, True)


@pytest.mark.parametrize(
    ("field", "budget", "reason"),
    [
        ("l2_source_ts_ns", L2_MAX_AGE_SECONDS, BlockReason.L2_STALE),
        (
            "latest_1m_close_ts_ns",
            ONE_MINUTE_CLOSED_MAX_AGE_SECONDS,
            BlockReason.ONE_MINUTE_CANDLE_STALE,
        ),
        ("latest_5m_close_ts_ns", FIVE_MINUTE_CLOSED_MAX_AGE_SECONDS, BlockReason.NOT_READY),
        ("optional_active_context_ts_ns", ACTIVE_CONTEXT_MAX_AGE_SECONDS, BlockReason.NOT_READY),
        ("metadata_ts_ns", METADATA_MAX_AGE_SECONDS, BlockReason.NOT_READY),
    ],
)
def test_freshness_budget_boundary_equality_and_just_over(
    field: str, budget: float, reason: BlockReason
) -> None:
    now, inputs = _fresh()
    values = inputs.__dict__ if hasattr(inputs, "__dict__") else {
        name: getattr(inputs, name) for name in inputs.__dataclass_fields__
    }
    values[field] = now - _ns(budget)
    at_boundary = evaluate_freshness(now, FreshnessInputs(**values))
    assert reason not in at_boundary.reasons
    values[field] = now - _ns(budget + 0.001)
    over = evaluate_freshness(now, FreshnessInputs(**values))
    assert reason in over.reasons
    assert not over.valid


def test_no_trade_and_old_bbo_are_diagnostics_not_continuity_failure() -> None:
    now, inputs = _fresh()
    result = evaluate_freshness(now, inputs)
    assert result.valid
    assert result.latest_trade_age_seconds is None
    assert result.bbo_value_age_seconds == pytest.approx(60.0)


def test_health_flags_fail_closed() -> None:
    now, inputs = _fresh()
    base = {name: getattr(inputs, name) for name in inputs.__dataclass_fields__}
    cases = (
        ("connected", False, BlockReason.DISCONNECTED),
        ("gap", True, BlockReason.GAP),
        ("conflict", True, BlockReason.CONFLICT),
        ("invalid_frame", True, BlockReason.INVALID_FRAME),
        ("ready", False, BlockReason.NOT_READY),
    )
    for field, value, reason in cases:
        values = dict(base)
        values[field] = value
        result = evaluate_freshness(now, FreshnessInputs(**values))
        assert reason in result.reasons
        assert not result.valid


def test_jev_lock_is_exact_pin_and_rejects_unhashed_or_unpinned(tmp_path: Path) -> None:
    script_path = Path(__file__).parents[1] / "scripts" / "check_dependency_lock.py"
    spec = importlib.util.spec_from_file_location("dependency_lock", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.JEV_REQUIREMENT == "typesafe-sdk==0.7.0"

    lock = Path(__file__).parents[1] / "requirements-jev.lock"
    module.ROOT = lock.parent
    entries = module._read_lock("requirements-jev.lock")
    assert entries["typesafe-sdk"][0] == "0.7.0"
    assert len(entries) == 13

    module.ROOT = tmp_path
    (tmp_path / "bad.lock").write_text("typesafe-sdk==0.7.0\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="unhashed or unpinned"):
        module._read_lock("bad.lock")
    (tmp_path / "bad.lock").write_text(
        "typesafe-sdk>=0.7.0 --hash=sha256:" + "0" * 64 + "\n", encoding="utf-8"
    )
    with pytest.raises(SystemExit, match="unhashed or unpinned"):
        module._read_lock("bad.lock")


def test_publication_and_signal_age_contracts_are_inclusive_at_boundary() -> None:
    start = _ns(100.0)
    assert evaluate_snapshot_publication_freshness(
        snapshot_ready_ts_ns=start, publication_ts_ns=start + _ns(5.0)
    ).valid
    assert not evaluate_snapshot_publication_freshness(
        snapshot_ready_ts_ns=start, publication_ts_ns=start + _ns(5.001)
    ).valid
    assert signal_is_fresh(signal_publication_ts_ns=start, at_ts_ns=start + _ns(15.0))
    assert not signal_is_fresh(signal_publication_ts_ns=start, at_ts_ns=start + _ns(15.001))
    assert not signal_is_fresh(
        signal_publication_ts_ns=start,
        at_ts_ns=start + _ns(10.0),
        next_evaluation_ts_ns=start + _ns(9.0),
    )


def test_identity_contracts_are_immutable() -> None:
    market = MarketIdentity("ABC", "provider", "ABC-PERP")
    config = JevConfig(
        config_version="JEV_CONFIG_V0",
        market=market,
        state_schema_version=STATE_SCHEMA_VERSION,
        question_version="JEV_QUESTIONS_V0",
        feature_version="JEV_FEATURES_V0",
        strategy_version="THREE_SETUP_CANONICAL",
        cost_version="COST_V0",
        requested_model="model-a",
    )
    with pytest.raises(FrozenInstanceError):
        config.requested_model = "model-b"  # type: ignore[misc]


def test_p1_has_no_custom_network_or_exchange_write_surface() -> None:
    root = Path(__file__).parents[1] / "src" / "trader_assist_v0" / "jev"
    forbidden_import_roots = {"httpx", "httpx2", "requests", "socket", "websockets"}
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".", 1)[0] for alias in node.names}
                assert not (roots & forbidden_import_roots)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                assert node.module.split(".", 1)[0] not in forbidden_import_roots
    adapter_source = (root / "typesafe_client.py").read_text(encoding="utf-8")
    assert "api_key=" not in adapter_source
    assert "wallet" not in adapter_source.lower()
    assert "signing" not in adapter_source.lower()
