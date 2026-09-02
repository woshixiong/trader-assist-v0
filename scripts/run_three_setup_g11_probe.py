#!/usr/bin/env python3
"""Default-off public-only G11 qualification probe for Three Setup production."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from trader_assist_v0.multi_asset_shadow.bootstrap import BoundaryReport
from trader_assist_v0.multi_asset_shadow.models import ClosedBar, MarketLifecycle
from trader_assist_v0.multi_asset_shadow.notification_engine import (
    WebhookConfig,
    WebhookDeliveryAdapter,
    WebhookResponse,
)
from trader_assist_v0.multi_asset_shadow.production import (
    THREE_SETUP_CONFIG_PATH,
    ThreeSetupProductionApplication,
    compose_three_setup_application,
    load_three_setup_config,
)
from trader_assist_v0.multi_asset_shadow.runtime import BoundaryMode

G11_PROBE_MODE = "THREE_SETUP_G11_PUBLIC_QUALIFICATION"
G11_RESULT_SCHEMA = "trader-assist-v0/three-setup-g11-result/v1"
DEFAULT_QUALIFICATION_TIMEOUT_SECONDS = 1_800.0
DEFAULT_DUPLICATE_OBSERVATION_SECONDS = 6.0
_SHUTDOWN_TIMEOUT_SECONDS = 15.0


class NoNetworkNotificationClient:
    """Production delivery-adapter sink that performs no network operation."""

    def __init__(self) -> None:
        self.calls = 0

    def post(self, **_: object) -> WebhookResponse:
        self.calls += 1
        return WebhookResponse(204)


def _result(
    *,
    status: str,
    reason: str,
    reports: list[BoundaryReport],
    application: Any,
) -> dict[str, object]:
    live = [report for report in reports if report.evaluation_mode is BoundaryMode.LIVE_ACTIONABLE]
    latest = live[-1] if live else None
    duplicates = 0
    if latest is not None:
        duplicates = sum(
            report.boundary_open_time_ms == latest.boundary_open_time_ms
            for report in live
        ) - 1
    diagnostics = getattr(application.bootstrap.runtime.health, "boundary_diagnostics", ())
    return {
        "schema": G11_RESULT_SCHEMA,
        "status": status,
        "reason": reason,
        "callback_report_count": len(reports),
        "live_callback_count": len(live),
        "scanner_run_count": 0 if latest is None else latest.scanner_run_count,
        "strategy_market_count": 0 if latest is None else len(latest.evaluated_market_ids),
        "evaluated_market_ids": [] if latest is None else list(latest.evaluated_market_ids),
        "duplicate_callback_count": max(0, duplicates),
        "runtime_diagnostics": [asdict(item) for item in diagnostics[-20:]],
        "public_data_only": True,
        "notification_network_disabled": True,
        "shadow_order_submitted": False,
    }


async def qualify_application(
    application: ThreeSetupProductionApplication,
    *,
    qualification_timeout_seconds: float,
    duplicate_observation_seconds: float = DEFAULT_DUPLICATE_OBSERVATION_SECONDS,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> dict[str, object]:
    """Observe the real production callback and return one semantic result."""
    if qualification_timeout_seconds <= 0 or duplicate_observation_seconds < 0:
        raise ValueError("G11 probe bounds are invalid")
    reports: list[BoundaryReport] = []
    report_changed = asyncio.Event()
    runtime = application.bootstrap.runtime
    production_callback = runtime.on_finalized_5m
    if production_callback is None:
        raise ValueError("production finalized callback is not composed")

    async def observing_callback(bar: ClosedBar, mode: BoundaryMode) -> object:
        value = production_callback(bar, mode)
        report = await value if isinstance(value, Awaitable) else value
        if not isinstance(report, BoundaryReport):
            raise TypeError("production finalized callback did not return BoundaryReport")
        reports.append(report)
        report_changed.set()
        return report

    runtime.on_finalized_5m = observing_callback
    shutdown = asyncio.Event()
    application_task = asyncio.create_task(application.run(shutdown), name="g11-production")
    result: dict[str, object] | None = None
    try:
        try:
            async with asyncio.timeout(qualification_timeout_seconds):
                while result is None:
                    changed = asyncio.create_task(report_changed.wait())
                    try:
                        await asyncio.wait(
                            (changed, application_task),
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                    finally:
                        if not changed.done():
                            changed.cancel()
                            await asyncio.gather(changed, return_exceptions=True)
                    if application_task.done():
                        await application_task
                        raise RuntimeError("production application exited before G11 proof")
                    report_changed.clear()
                    active = application.bootstrap.registry.active()
                    if active is None:
                        continue
                    target_ids = tuple(
                        market.identity.market_id
                        for market in active.markets
                        if market.lifecycle is MarketLifecycle.ACTIVE
                    )
                    candidates = [
                        report
                        for report in reports
                        if report.evaluation_mode is BoundaryMode.LIVE_ACTIONABLE
                        and report.scanner_run_count == 1
                        and report.evaluated_market_ids == target_ids
                        and len(target_ids) == 20
                        and not report.failures
                    ]
                    if not candidates:
                        continue
                    proven = candidates[-1]
                    await sleep(duplicate_observation_seconds)
                    same_boundary = [
                        report
                        for report in reports
                        if report.boundary_open_time_ms == proven.boundary_open_time_ms
                    ]
                    if len(same_boundary) != 1:
                        result = _result(
                            status="FAIL",
                            reason="DUPLICATE_LIVE_ACTIONABLE_CALLBACK",
                            reports=reports,
                            application=application,
                        )
                    else:
                        result = _result(
                            status="PASS",
                            reason="FULL_TARGET20_LIVE_ACTIONABLE_COHORT_OBSERVED",
                            reports=reports,
                            application=application,
                        )
        except TimeoutError:
            result = _result(
                status="FAIL",
                reason="NO_LIVE_ACTIONABLE_COHORT_WITHIN_BOUNDED_WINDOW",
                reports=reports,
                application=application,
            )
        except Exception as exc:
            result = _result(
                status="FAIL",
                reason=f"PRODUCTION_PROBE_FAILURE:{type(exc).__name__}",
                reports=reports,
                application=application,
            )
    finally:
        shutdown.set()
        try:
            await asyncio.wait_for(application_task, timeout=_SHUTDOWN_TIMEOUT_SECONDS)
        except TimeoutError:
            application_task.cancel()
            await asyncio.gather(application_task, return_exceptions=True)
            if result is None or result.get("status") == "PASS":
                result = _result(
                    status="FAIL",
                    reason="BOUNDED_SHUTDOWN_TIMEOUT",
                    reports=reports,
                    application=application,
                )
        except Exception as exc:
            if result is None or result.get("status") == "PASS":
                result = _result(
                    status="FAIL",
                    reason=f"PRODUCTION_SHUTDOWN_FAILURE:{type(exc).__name__}",
                    reports=reports,
                    application=application,
                )
    assert result is not None
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable-three-setup-g11-probe", action="store_true")
    parser.add_argument("--mode", default="")
    parser.add_argument("--config-path", type=Path, default=THREE_SETUP_CONFIG_PATH)
    parser.add_argument(
        "--qualification-timeout-seconds",
        type=float,
        default=DEFAULT_QUALIFICATION_TIMEOUT_SECONDS,
    )
    return parser


async def _run(arguments: argparse.Namespace) -> dict[str, object]:
    config = load_three_setup_config(arguments.config_path)
    sink = NoNetworkNotificationClient()
    notification = WebhookDeliveryAdapter(
        client=sink,
        config=WebhookConfig(url="https://example.invalid/no-network"),
    )
    application = compose_three_setup_application(
        config=config,
        notification_adapter=notification,
    )
    return await qualify_application(
        application,
        qualification_timeout_seconds=arguments.qualification_timeout_seconds,
    )


def main(argv: tuple[str, ...] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if (
            not arguments.enable_three_setup_g11_probe
            or arguments.mode != G11_PROBE_MODE
        ):
            raise ValueError("G11 probe activation is default-off")
        if arguments.qualification_timeout_seconds <= 0:
            raise ValueError("qualification timeout must be positive")
        result = asyncio.run(_run(arguments))
    except Exception as exc:
        result = {
            "schema": G11_RESULT_SCHEMA,
            "status": "FAIL",
            "reason": f"G11_PROBE_CONFIGURATION_FAILURE:{type(exc).__name__}",
            "callback_report_count": 0,
            "live_callback_count": 0,
            "scanner_run_count": 0,
            "strategy_market_count": 0,
            "evaluated_market_ids": [],
            "duplicate_callback_count": 0,
            "runtime_diagnostics": [],
            "public_data_only": True,
            "notification_network_disabled": True,
            "shadow_order_submitted": False,
        }
    print("G11_RESULT=" + json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())