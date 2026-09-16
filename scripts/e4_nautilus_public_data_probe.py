# mypy: disable-error-code="import-not-found"
"""Bounded exact-version public-data-only E4 probe; never configures execution."""

from __future__ import annotations

import argparse
import os
import threading
import time
from pathlib import Path
from typing import Any

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_e4.capture import SubscriptionPolicy
from trader_assist_v0.nautilus_e4.contracts import (
    NAUTILUS_VERSION,
    MarketExpression,
    PitUniverseSnapshot,
    RunManifest,
)
from trader_assist_v0.nautilus_e4.host import (
    NautilusE4CaptureStrategy,
    assert_exact_nautilus_version,
    build_capture_strategy,
    build_public_data_node,
)
from trader_assist_v0.nautilus_e4.safety import assert_public_only

PASS = 0
PROVIDER_DATA_INCOMPLETE = 2
APPLICATION_FAILURE = 3


def _external_minute_bar_type(instrument_id: str) -> str:
    """Build the shortest provider-supported external BarType via public APIs."""
    from nautilus_trader.model import (
        AggregationSource,
        BarAggregation,
        BarSpecification,
        BarType,
        InstrumentId,
        PriceType,
    )

    return str(
        BarType(
            InstrumentId.from_str(instrument_id),
            BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST),
            AggregationSource.EXTERNAL,
        )
    )


def _write_result(path: Path | None, payload: dict[str, Any]) -> None:
    encoded = canonical_json_bytes(payload) + b"\n"
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(encoded)
        temporary.replace(path)
    print(encoded.decode().strip())


def _ci_identity(
    instrument_id: str, provider_coin: str
) -> tuple[PitUniverseSnapshot, RunManifest]:
    market_id = sha256_hex(f"HYPERLIQUID|MAIN|{provider_coin}".encode())
    expression = MarketExpression(
        market_id=market_id,
        dex="MAIN",
        provider_coin=provider_coin,
        instrument_id=instrument_id,
        expression_id=f"ci-public-{provider_coin.lower()}",
        instrument_metadata_version="PUBLIC_PROVIDER_PROBE_V1",
        instrument_metadata_hash=sha256_hex(
            f"PUBLIC_PROVIDER_PROBE_V1|{instrument_id}".encode()
        ),
    )
    snapshot = PitUniverseSnapshot.create(
        observed_at_ns=time.time_ns(), expressions=(expression,)
    )
    raw_sha = os.environ.get("E4_EXACT_HEAD", "0" * 40)
    git_sha = raw_sha if len(raw_sha) == 40 else "0" * 40
    raw_tree = os.environ.get("E4_EXACT_TREE", "0" * 40)
    git_tree = raw_tree if len(raw_tree) == 40 else "0" * 40
    manifest = RunManifest.create(
        run_id=f"e4-public-provider-{git_sha[:12]}",
        git_sha=git_sha,
        git_tree=git_tree,
        snapshot=snapshot,
        process_epoch=f"process-{git_sha[:12]}",
        continuity_epoch=f"continuity-{git_sha[:12]}",
        admission_epoch=f"admission-{git_sha[:12]}",
        capture_configuration={
            "expressions": [expression.model_dump(mode="json")],
            "probe": "BOUNDED_PUBLIC_PROVIDER_V1",
        },
        subscription_policy={
            "discovery": [market_id],
            "watch": [market_id],
            "actionable": [],
        },
        trial_ledger_id="public-provider-probe-v1",
    )
    return snapshot, manifest


def _run_live(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    if args.ci_instrument_id:
        snapshot, manifest = _ci_identity(args.ci_instrument_id, args.provider_coin)
        watch_market_ids = [snapshot.expressions[0].market_id]
    else:
        if args.manifest is None or args.snapshot is None or args.evidence_path is None:
            raise ValueError(
                "live probe requires --manifest, --snapshot, and --evidence-path"
            )
        manifest = RunManifest.model_validate_json(args.manifest.read_bytes())
        snapshot = PitUniverseSnapshot.model_validate_json(args.snapshot.read_bytes())
        watch_market_ids = args.watch_market_id
    if args.evidence_path is None:
        raise ValueError("live probe requires --evidence-path")
    discovery = frozenset(item.market_id for item in snapshot.expressions)
    policy = SubscriptionPolicy(
        discovery=discovery,
        watch=frozenset(watch_market_ids),
        actionable=frozenset(args.actionable_market_id),
    )
    bar_types = tuple(args.bar_type)
    if args.ci_instrument_id and not bar_types:
        bar_types = (_external_minute_bar_type(args.ci_instrument_id),)
    if not bar_types:
        raise ValueError("live public-provider proof requires a finalized Bar subscription")
    node = build_public_data_node()
    strategy: NautilusE4CaptureStrategy | None = None
    timer: threading.Timer | None = None
    try:
        strategy = build_capture_strategy(
            manifest=manifest,
            snapshot=snapshot,
            policy=policy,
            bar_types=bar_types,
            evidence_root=args.evidence_path,
        )
        node.add_strategy(strategy)
        handle = node.handle()
        timer = threading.Timer(args.run_seconds, handle.stop)
        timer.start()
        node.run()
    finally:
        if timer is not None:
            timer.cancel()
        node.dispose()
    assert strategy is not None
    observation = strategy.public_provider_observation
    passed = bool(observation["provider_observation_pass"])
    return (
        PASS if passed else PROVIDER_DATA_INCOMPLETE,
        {
            "schema_version": "E4_PUBLIC_PROVIDER_PROBE_RESULT_V1",
            "status": "PASS" if passed else "PROVIDER_DATA_INCOMPLETE",
            "failure_class": None if passed else "PROVIDER_OR_DATA_INCOMPLETENESS",
            "claim": "FRESH_PUBLIC_DATA_OBSERVED_FOR_EVERY_REQUESTED_SUBSCRIPTION_KIND",
            "bounded_run_seconds": args.run_seconds,
            "nautilus_version": NAUTILUS_VERSION,
            "exact_head": manifest.git_sha,
            "exact_tree": manifest.git_tree,
            "public_data_only": True,
            "zero_credentials": True,
            "zero_execution_client": True,
            "zero_signing": True,
            "zero_exchange_write": True,
            "PUBLIC_HYPERLIQUID_DATA_ONLY": True,
            "QUOTE_OBSERVED": observation["quote_observed"],
            "TRADE_OBSERVED": observation["trade_observed"],
            "BAR_SUBSCRIPTION_REGISTERED": observation[
                "bar_subscription_registered"
            ],
            "FINALIZED_BAR_CALLBACK_OBSERVED": observation[
                "finalized_bar_callback_observed"
            ],
            "FINALIZED_BAR_EVIDENCE_PERSISTED": observation[
                "finalized_bar_evidence_persisted"
            ],
            "observation": observation,
            "capture_health": strategy.capture_health,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-path", type=Path)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--watch-market-id", action="append", default=[])
    parser.add_argument("--actionable-market-id", action="append", default=[])
    parser.add_argument("--bar-type", action="append", default=[])
    parser.add_argument("--ci-instrument-id")
    parser.add_argument("--provider-coin", default="ETH")
    parser.add_argument("--run-seconds", type=int, default=0)
    args = parser.parse_args()
    if args.run_seconds < 0 or args.run_seconds > 300:
        raise SystemExit("--run-seconds must be between 0 and 300")
    proof = assert_public_only(env=os.environ)
    assert_exact_nautilus_version()
    if args.run_seconds == 0:
        _write_result(
            args.result_path,
            {
                "schema_version": "E4_PUBLIC_PROVIDER_PROBE_RESULT_V1",
                "status": "NOT_RUN_CONFIG_CHECK_ONLY",
                "failure_class": None,
                "zero_write_proof": proof.model_dump(mode="json"),
            },
        )
        return PASS
    try:
        exit_code, result = _run_live(args)
    except Exception as exc:
        _write_result(
            args.result_path,
            {
                "schema_version": "E4_PUBLIC_PROVIDER_PROBE_RESULT_V1",
                "status": "APPLICATION_FAILURE",
                "failure_class": "APPLICATION_OR_PROVIDER_RUNTIME_FAILURE",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "bounded_run_seconds": args.run_seconds,
                "public_data_only": True,
                "zero_credentials": True,
                "zero_execution_client": True,
                "zero_signing": True,
                "zero_exchange_write": True,
            },
        )
        return APPLICATION_FAILURE
    _write_result(args.result_path, result)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
