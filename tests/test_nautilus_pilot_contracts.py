from __future__ import annotations

import sys
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.models import ClosedBar
from trader_assist_v0.multi_asset_shadow.strategy_kernel import (
    PARAMETER_VERSION,
    SCANNER_VERSION,
    SCHEMA_VERSION,
    STRATEGY_VERSION,
    ScannerLinkage,
    ScannerState,
)
from trader_assist_v0.nautilus_pilot import strategy_package
from trader_assist_v0.nautilus_pilot.contracts import (
    E3_AUTHORITY_MARKER,
    StrategyInputEvent,
    close_boundary_ns,
    revalidate_strategy_input_event,
)
from trader_assist_v0.nautilus_pilot.strategy_package import (
    STRATEGY_PACKAGE_VERSION,
    PilotStrategyEvaluator,
    StrategyPackageManifest,
    select_strategy_package,
)

BASE_SHA = "3bf7f4e1c1a852b780da599147e39b109392385c"
MARKET = "2" * 64
FIVE_MINUTES_MS = 300_000


def _closed_bar(index: int) -> ClosedBar:
    center = Decimal(100 + index % 9)
    close_time_ms = (index + 1) * FIVE_MINUTES_MS
    return ClosedBar.create(
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


def _manifest() -> StrategyPackageManifest:
    return StrategyPackageManifest.create(trade_os_release_sha=BASE_SHA)


def _event(index: int) -> StrategyInputEvent:
    scanner = (
        ScannerLinkage("e3-candidate", ScannerState.WATCH_NEAR_LEVEL)
        if index == 48
        else None
    )
    return StrategyInputEvent.create(
        strategy_package_hash=_manifest().manifest_hash,
        closed_bar=_closed_bar(index),
        scanner_linkage=scanner,
    )


def test_package_root_does_not_eagerly_import_optional_host() -> None:
    assert "trader_assist_v0.nautilus_pilot.host" not in sys.modules


def test_input_revalidates_closed_bar_and_preserves_exact_projection() -> None:
    bar = _closed_bar(7)
    event = StrategyInputEvent.create(
        strategy_package_hash=_manifest().manifest_hash,
        closed_bar=bar,
        scanner_linkage=ScannerLinkage("candidate-7", ScannerState.WATCH_MOMENTUM),
    )

    assert event.closed_bar is not bar
    assert event.market_id == bar.market_id
    assert event.interval == bar.interval
    assert event.open_time_ms == bar.open_time_ms
    assert event.close_time_ms == bar.close_time_ms
    assert event.ts_event == event.ts_init == close_boundary_ns(bar.close_time_ms)
    assert event.source_id == bar.source_id
    assert event.provenance_hash == bar.provenance_hash
    assert event.source_canonical_hash == bar.canonical_hash
    for name in ("open", "high", "low", "close", "volume"):
        assert getattr(event.closed_bar, name).as_tuple() == getattr(bar, name).as_tuple()
    assert revalidate_strategy_input_event(event) == event


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("market_id", "3" * 64, "identity contradicts"),
        ("close_time_ms", FIVE_MINUTES_MS, "identity contradicts"),
        ("source_id", "OTHER_SOURCE", "identity contradicts"),
        ("source_canonical_hash", "4" * 64, "identity contradicts"),
        ("ts_event", 1, "timestamps must equal"),
        ("ts_init", 1, "timestamps must equal"),
    ),
)
def test_input_identity_and_timestamp_contradictions_fail_closed(
    field: str, value: object, message: str
) -> None:
    tampered = _event(8).model_copy(update={field: value})
    with pytest.raises(ValidationError, match=message):
        revalidate_strategy_input_event(tampered)


def test_mutated_closed_bar_instance_is_independently_revalidated() -> None:
    bar = _closed_bar(9)
    object.__setattr__(bar, "close", Decimal("101.25"))
    with pytest.raises(ValidationError, match="canonical_hash does not bind"):
        StrategyInputEvent.create(
            strategy_package_hash=_manifest().manifest_hash,
            closed_bar=bar,
        )


def test_manifest_binds_exact_current_versions_and_selector_fails_closed() -> None:
    manifest = _manifest()
    assert (
        manifest.package_version,
        manifest.strategy_version,
        manifest.parameter_version,
        manifest.scanner_version,
        manifest.kernel_schema_version,
        manifest.trade_os_release_sha,
    ) == (
        STRATEGY_PACKAGE_VERSION,
        STRATEGY_VERSION,
        PARAMETER_VERSION,
        SCANNER_VERSION,
        SCHEMA_VERSION,
        BASE_SHA,
    )
    selected = select_strategy_package(
        package_version=manifest.package_version,
        strategy_version=manifest.strategy_version,
        parameter_version=manifest.parameter_version,
        scanner_version=manifest.scanner_version,
        kernel_schema_version=manifest.kernel_schema_version,
        trade_os_release_sha=manifest.trade_os_release_sha,
        manifest_hash=manifest.manifest_hash,
    )
    assert selected == manifest
    with pytest.raises(ValueError, match="not the exact current package"):
        select_strategy_package(
            package_version=manifest.package_version,
            strategy_version="UNAUTHORIZED_STRATEGY_VERSION",
            parameter_version=manifest.parameter_version,
            scanner_version=manifest.scanner_version,
            kernel_schema_version=manifest.kernel_schema_version,
            trade_os_release_sha=manifest.trade_os_release_sha,
            manifest_hash=manifest.manifest_hash,
        )


def test_evaluator_uses_unchanged_kernel_and_outputs_rebuildable_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest()
    original = strategy_package.evaluate_strategy
    calls = 0

    def observed(*args: object, **kwargs: object):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(strategy_package, "evaluate_strategy", observed)
    first = PilotStrategyEvaluator(
        manifest=manifest,
        market_id=MARKET,
        minimum_tick=Decimal("0.1"),
    )
    second = PilotStrategyEvaluator(
        manifest=manifest,
        market_id=MARKET,
        minimum_tick=Decimal("0.1"),
    )
    first_outputs = tuple(
        output for event in map(_event, range(49)) if (output := first.evaluate(event))
    )
    second_outputs = tuple(
        output for event in map(_event, range(49)) if (output := second.evaluate(event))
    )

    assert calls > 0
    assert first_outputs
    assert first_outputs == second_outputs
    assert first.source_history_commitment == second.source_history_commitment
    final = first_outputs[-1]
    assert final.authority_marker == E3_AUTHORITY_MARKER
    assert final.rebuildable is True
    assert final.strategy_package_hash == manifest.manifest_hash
    assert final.source_canonical_hash == _event(48).source_canonical_hash


def test_evaluator_rejects_market_package_and_chronology_contradictions() -> None:
    manifest = _manifest()
    evaluator = PilotStrategyEvaluator(
        manifest=manifest,
        market_id=MARKET,
        minimum_tick=Decimal("0.1"),
    )
    wrong_package = _event(0).model_copy(update={"strategy_package_hash": "5" * 64})
    with pytest.raises(ValidationError, match="canonical_hash does not bind"):
        evaluator.evaluate(wrong_package)
    evaluator.evaluate(_event(0))
    with pytest.raises(ValueError, match="not chronological"):
        evaluator.evaluate(_event(2))
