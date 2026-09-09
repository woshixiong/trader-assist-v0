from __future__ import annotations

import ast
import importlib.util
import inspect
import os
from datetime import UTC, datetime
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

import pytest

if importlib.util.find_spec("nautilus_trader") is None:
    if os.environ.get("NAUTILUS_PILOT_REQUIRED") == "1":
        raise AssertionError("authoritative E3 CI requires the exact Nautilus pilot distribution")
    pytest.skip("optional nautilus-pilot dependency is absent", allow_module_level=True)

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.node import BacktestNode

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.models import ClosedBar
from trader_assist_v0.nautilus_pilot.contracts import StrategyInputEvent
from trader_assist_v0.nautilus_pilot.host import (
    NautilusPilotStrategy,
    NautilusPilotStrategyConfig,
    build_custom_data,
    build_importable_strategy_config,
)
from trader_assist_v0.nautilus_pilot.strategy_package import (
    PilotStrategyEvaluator,
    StrategyPackageManifest,
)

BASE_SHA = "3bf7f4e1c1a852b780da599147e39b109392385c"
MARKET = "2" * 64
FIVE_MINUTES_MS = 300_000


def _manifest() -> StrategyPackageManifest:
    return StrategyPackageManifest.create(trade_os_release_sha=BASE_SHA)


def _event(index: int) -> StrategyInputEvent:
    center = Decimal(100 + index % 9)
    close_time_ms = (index + 1) * FIVE_MINUTES_MS
    bar = ClosedBar.create(
        market_id=MARKET,
        interval="5m",
        open_time_ms=index * FIVE_MINUTES_MS,
        close_time_ms=close_time_ms,
        open=center,
        high=center + Decimal("2.000"),
        low=center - Decimal("2.00"),
        close=center + Decimal("0.5000"),
        volume=Decimal(f"{10 + index % 7}.00000"),
        source_id="E3_REPRESENTATIVE_CURRENT_FIXTURE",
        provenance_hash=sha256_hex(f"fixture-{index}".encode()),
        received_at=datetime.fromtimestamp(close_time_ms / 1_000, tz=UTC),
    )
    return StrategyInputEvent.create(
        strategy_package_hash=_manifest().manifest_hash,
        closed_bar=bar,
    )


def _config() -> NautilusPilotStrategyConfig:
    manifest = _manifest()
    return NautilusPilotStrategyConfig(
        package_version=manifest.package_version,
        strategy_version=manifest.strategy_version,
        parameter_version=manifest.parameter_version,
        scanner_version=manifest.scanner_version,
        kernel_schema_version=manifest.kernel_schema_version,
        trade_os_release_sha=manifest.trade_os_release_sha,
        manifest_hash=manifest.manifest_hash,
        market_id=MARKET,
        minimum_tick="0.1",
    )


def test_exact_rc4_and_public_importable_strategy_config_surface() -> None:
    assert version("nautilus-trader") == "2.0.0rc4"
    manifest = _manifest()
    importable = build_importable_strategy_config(
        manifest=manifest,
        market_id=MARKET,
        minimum_tick=Decimal("0.1"),
    )
    assert importable.strategy_path == (
        "trader_assist_v0.nautilus_pilot.host:NautilusPilotStrategy"
    )
    assert importable.config_path == (
        "trader_assist_v0.nautilus_pilot.host:NautilusPilotStrategyConfig"
    )
    assert importable.config["manifest_hash"] == manifest.manifest_hash
    assert callable(BacktestNode.add_strategy_from_config)


def test_official_backtest_custom_data_dispatch_matches_direct_project_evaluator() -> None:
    events = tuple(map(_event, range(49)))
    direct_evaluator = PilotStrategyEvaluator(
        manifest=_manifest(),
        market_id=MARKET,
        minimum_tick=Decimal("0.1"),
    )
    direct_outputs = tuple(
        output for event in events if (output := direct_evaluator.evaluate(event))
    )

    strategy = NautilusPilotStrategy(_config())
    engine = BacktestEngine()
    try:
        engine.add_data([build_custom_data(event) for event in events])
        engine.add_strategy(strategy)
        engine.run()
    finally:
        engine.dispose()

    assert strategy.pilot_outputs
    assert strategy.pilot_outputs == direct_outputs
    assert tuple(item.kernel_result for item in strategy.pilot_outputs) == tuple(
        item.kernel_result for item in direct_outputs
    )


def test_host_has_no_order_account_execution_or_durable_state_surface() -> None:
    host_path = Path(inspect.getfile(NautilusPilotStrategy))
    tree = ast.parse(host_path.read_text(encoding="utf-8"))
    prohibited = {
        "submit_order",
        "submit_order_list",
        "cancel_order",
        "cancel_all_orders",
        "modify_order",
        "portfolio",
        "account",
        "on_save",
        "on_load",
    }
    referenced = {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    } | {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert prohibited.isdisjoint(referenced)
