#!/usr/bin/env python3
# mypy: disable-error-code="import-not-found"
"""Prospective, fixed-size public acquisition for a G4E8 candidate.

This orchestrator does not own provider transport or Capture semantics.  It
freezes one deterministic market set from one official public snapshot, then
invokes the existing E4 probe and (only after complete provider evidence) the
existing representative-scale candidate builder.  Its output never grants
canonical G4E8 credit.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Protocol

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_e4.contracts import (
    MarketExpression,
    PitUniverseSnapshot,
    RunManifest,
)
from trader_assist_v0.nautilus_e4.safety import assert_public_only
from trader_assist_v0.nautilus_e4.storage import EvidenceStore

TARGET_COUNT = 20
RUN_SECONDS = 180
VENUE = "HYPERLIQUID_MAINNET"
DEX = "MAIN"
PRODUCT_CLASS = "STANDARD_PERPETUALS"
SELECTION_SCHEMA = "G4_REPRESENTATIVE_SELECTION_SOURCE_V1"
MARKET_SET_SCHEMA = "G4_REPRESENTATIVE_FROZEN_MARKET_SET_V1"
PLAN_SCHEMA = "G4_REPRESENTATIVE_ACQUISITION_PLAN_V1"
RESULT_SCHEMA = "G4_REPRESENTATIVE_ACQUISITION_RESULT_V1"
INSTRUMENT_METADATA_VERSION = "NAUTILUS_HYPERLIQUID_2.0.0rc5_META_CTX_V1"
TASK_PACKET_SHA256 = "5cca1016a638e3fa1ddb21910db13ba5f1b0719ebdd4a7e82bee402c2dd8b1a2"

PASS = 0
PROVIDER_DATA_INCOMPLETE = 2
APPLICATION_OR_PROVIDER_RUNTIME_FAILURE = 3

_GIT_OID = re.compile(r"^[0-9a-f]{40}$")
_COIN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,78}$")


class SelectionClient(Protocol):
    def metadata_and_context(self, dex: str) -> object: ...


class CompletedProcessLike(Protocol):
    returncode: int


@dataclass(frozen=True)
class FrozenMarket:
    """One exact provider expression frozen before subscription begins."""

    ordinal: int
    provider_coin: str
    instrument_id: str
    market_id: str
    day_notional_volume: str
    source_universe_index: int
    instrument_metadata_hash: str

    def identity_payload(self) -> dict[str, object]:
        return {
            "ordinal": self.ordinal,
            "provider_coin": self.provider_coin,
            "instrument_id": self.instrument_id,
            "market_id": self.market_id,
            "day_notional_volume": self.day_notional_volume,
            "source_universe_index": self.source_universe_index,
            "instrument_metadata_hash": self.instrument_metadata_hash,
        }


class AcquisitionContractError(RuntimeError):
    """The prospective plan cannot safely satisfy the frozen contract."""


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    encoded = canonical_json_bytes(dict(payload)) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)


def _git_identity() -> tuple[str, str]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not _GIT_OID.fullmatch(head) or not _GIT_OID.fullmatch(tree):
        raise AcquisitionContractError("git exact-head identity is not canonical")
    return head, tree


def bind_exact_git_identity(expected_head: str) -> tuple[str, str]:
    if not _GIT_OID.fullmatch(expected_head):
        raise AcquisitionContractError("expected exact head must be one full Git commit OID")
    head, tree = _git_identity()
    if head != expected_head:
        raise AcquisitionContractError(
            f"checked-out HEAD does not match expected exact head: {head} != {expected_head}"
        )
    return head, tree


def fetch_selection_source(
    client: SelectionClient,
    *,
    clock_ns: Callable[[], int] = time.time_ns,
) -> dict[str, object]:
    """Perform exactly one official MAIN meta/asset-context request."""
    response = client.metadata_and_context("")
    return {
        "schema_version": SELECTION_SCHEMA,
        "venue": VENUE,
        "dex": DEX,
        "product_class": PRODUCT_CLASS,
        "request": {"type": "metaAndAssetCtxs"},
        "observed_at_ns": clock_ns(),
        "response": response,
    }


def selection_source_hash(source: Mapping[str, object]) -> str:
    return sha256_hex(canonical_json_bytes(dict(source)))


def _canonical_positive_decimal(value: object) -> tuple[Decimal, str] | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not parsed.is_finite() or parsed <= 0:
        return None
    canonical = format(parsed, "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    return parsed, canonical


def _exact_rc5_instrument_id(provider_coin: str) -> str:
    if not _COIN.fullmatch(provider_coin) or ":" in provider_coin:
        raise AcquisitionContractError(
            f"invalid exact-rc5 standard MAIN provider coin mapping: {provider_coin!r}"
        )
    instrument_id = f"{provider_coin}-USD-PERP.HYPERLIQUID"
    from nautilus_trader.model import InstrumentId

    try:
        parsed = InstrumentId.from_str(instrument_id)
    except Exception as exc:
        raise AcquisitionContractError(
            f"invalid exact-rc5 instrument mapping for {provider_coin!r}"
        ) from exc
    if str(parsed) != instrument_id:
        raise AcquisitionContractError(
            f"non-exact rc5 instrument mapping for {provider_coin!r}"
        )
    return instrument_id


def freeze_market_selection(
    source: Mapping[str, object],
    *,
    instrument_mapper: Callable[[str], str] = _exact_rc5_instrument_id,
) -> tuple[FrozenMarket, ...]:
    """Select the first 20 eligible MAIN perps under the frozen total order."""
    if source.get("schema_version") != SELECTION_SCHEMA:
        raise AcquisitionContractError("selection source schema is not exact")
    response = source.get("response")
    if not isinstance(response, list) or len(response) != 2:
        raise AcquisitionContractError("metaAndAssetCtxs response must contain meta and contexts")
    meta, contexts = response
    if not isinstance(meta, dict) or not isinstance(contexts, list):
        raise AcquisitionContractError("metaAndAssetCtxs response shape is invalid")
    universe = meta.get("universe")
    if not isinstance(universe, list) or len(universe) != len(contexts):
        raise AcquisitionContractError("meta universe and asset contexts are not position-bound")

    eligible: list[tuple[Decimal, str, str, int, str, str, str]] = []
    mapped_ids: dict[str, str] = {}
    seen_coins: set[str] = set()
    for index, (asset, context) in enumerate(zip(universe, contexts, strict=True)):
        if not isinstance(asset, dict) or not isinstance(context, dict):
            raise AcquisitionContractError("meta universe entry or asset context is invalid")
        coin = asset.get("name")
        if not isinstance(coin, str) or not coin:
            raise AcquisitionContractError("standard MAIN asset lacks a provider coin")
        if ":" in coin:
            continue
        instrument_id = instrument_mapper(coin)
        if coin in seen_coins:
            raise AcquisitionContractError("duplicate provider coin in MAIN universe")
        seen_coins.add(coin)
        prior = mapped_ids.setdefault(instrument_id, coin)
        if prior != coin:
            raise AcquisitionContractError("duplicate exact-rc5 instrument mapping")
        if asset.get("isDelisted") is True:
            continue
        volume = _canonical_positive_decimal(context.get("dayNtlVlm"))
        mid_or_mark = _canonical_positive_decimal(context.get("midPx")) or (
            _canonical_positive_decimal(context.get("markPx"))
        )
        if volume is None or mid_or_mark is None:
            continue
        volume_value, volume_wire = volume
        market_id = sha256_hex(f"HYPERLIQUID|MAIN|{coin}".encode())
        metadata_hash = sha256_hex(
            canonical_json_bytes(
                {
                    "source_universe_index": index,
                    "asset": asset,
                    "context": context,
                    "instrument_id": instrument_id,
                }
            )
        )
        eligible.append(
            (
                volume_value,
                coin,
                instrument_id,
                index,
                market_id,
                volume_wire,
                metadata_hash,
            )
        )

    eligible.sort(key=lambda item: (-item[0], item[1], item[2]))
    if len(eligible) < TARGET_COUNT:
        raise AcquisitionContractError(
            f"fewer than {TARGET_COUNT} eligible standard MAIN perpetuals: {len(eligible)}"
        )
    selected = eligible[:TARGET_COUNT]
    markets = tuple(
        FrozenMarket(
            ordinal=ordinal,
            provider_coin=item[1],
            instrument_id=item[2],
            source_universe_index=item[3],
            market_id=item[4],
            day_notional_volume=item[5],
            instrument_metadata_hash=item[6],
        )
        for ordinal, item in enumerate(selected, start=1)
    )
    if len({item.market_id for item in markets}) != TARGET_COUNT:
        raise AcquisitionContractError("frozen market set contains duplicate market identity")
    if len({item.instrument_id for item in markets}) != TARGET_COUNT:
        raise AcquisitionContractError("frozen market set contains duplicate instrument mapping")
    return markets


def ordered_market_set_document(markets: Sequence[FrozenMarket]) -> dict[str, object]:
    if len(markets) != TARGET_COUNT:
        raise AcquisitionContractError(f"frozen market set must contain exactly {TARGET_COUNT}")
    identity: dict[str, object] = {
        "schema_version": MARKET_SET_SCHEMA,
        "venue": VENUE,
        "dex": DEX,
        "product_class": PRODUCT_CLASS,
        "target_count": TARGET_COUNT,
        "manual_selection": False,
        "post_hoc_substitution": False,
        "markets": [item.identity_payload() for item in markets],
    }
    return {
        **identity,
        "ordered_market_set_hash": sha256_hex(canonical_json_bytes(identity)),
    }


def _expression(market: FrozenMarket) -> MarketExpression:
    return MarketExpression(
        market_id=market.market_id,
        dex=DEX,
        provider_coin=market.provider_coin,
        instrument_id=market.instrument_id,
        expression_id=f"task5b-{market.ordinal:02d}-{market.market_id[:16]}",
        listing_state="ACTIVE_STANDARD_MAIN_PERPETUAL",
        instrument_metadata_version=INSTRUMENT_METADATA_VERSION,
        instrument_metadata_hash=market.instrument_metadata_hash,
    )


def build_acquisition_plan(
    *,
    source: Mapping[str, object],
    markets: Sequence[FrozenMarket],
    exact_head: str,
    exact_tree: str,
    github_run_id: str,
    github_run_attempt: int,
) -> tuple[dict[str, object], PitUniverseSnapshot, RunManifest]:
    if not github_run_id.isdigit() or int(github_run_id) <= 0:
        raise AcquisitionContractError("GitHub run_id must be a positive integer identity")
    if github_run_attempt <= 0:
        raise AcquisitionContractError("GitHub run_attempt must be positive")
    if not _GIT_OID.fullmatch(exact_head) or not _GIT_OID.fullmatch(exact_tree):
        raise AcquisitionContractError("acquisition exact head/tree identity is invalid")

    source_hash = selection_source_hash(source)
    market_set = ordered_market_set_document(markets)
    market_set_hash = str(market_set["ordered_market_set_hash"])
    attempt_identity: dict[str, object] = {
        "task_packet_sha256": TASK_PACKET_SHA256,
        "github_run_id": github_run_id,
        "github_run_attempt": github_run_attempt,
        "exact_head": exact_head,
        "exact_tree": exact_tree,
        "selection_source_snapshot_hash": source_hash,
        "ordered_market_set_hash": market_set_hash,
        "target_count": TARGET_COUNT,
        "run_seconds": RUN_SECONDS,
    }
    attempt_hash = sha256_hex(canonical_json_bytes(attempt_identity))
    expressions = tuple(_expression(item) for item in markets)
    observed_at_ns = source.get("observed_at_ns")
    if not isinstance(observed_at_ns, int) or isinstance(observed_at_ns, bool):
        raise AcquisitionContractError("selection source observed_at_ns is invalid")
    snapshot = PitUniverseSnapshot.create(
        observed_at_ns=observed_at_ns,
        expressions=expressions,
    )
    ordered_market_ids = [item.market_id for item in markets]
    manifest = RunManifest.create(
        run_id=f"task5b-{attempt_hash[:32]}",
        git_sha=exact_head,
        git_tree=exact_tree,
        snapshot=snapshot,
        process_epoch=f"process-{attempt_hash[:24]}",
        continuity_epoch=f"continuity-{attempt_hash[:24]}",
        admission_epoch=f"admission-{attempt_hash[:24]}",
        capture_configuration={
            "probe": "BOUNDED_PUBLIC_PROVIDER_REPRESENTATIVE_SCALE_V1",
            "selection_source_snapshot_hash": source_hash,
            "ordered_market_set_hash": market_set_hash,
            "ordered_frozen_markets": market_set["markets"],
            "acquisition_attempt_identity": attempt_identity,
            "acquisition_attempt_identity_hash": attempt_hash,
            "watch_market_count": TARGET_COUNT,
            "external_one_minute_bar_type_count": TARGET_COUNT,
            "run_seconds": RUN_SECONDS,
            "one_livenode": True,
            "one_hyperliquid_data_client": True,
        },
        subscription_policy={
            "discovery": ordered_market_ids,
            "watch": ordered_market_ids,
            "actionable": [],
        },
        trial_ledger_id="task5b-representative-public-capture-v1",
    )
    plan: dict[str, object] = {
        "schema_version": PLAN_SCHEMA,
        "status": "FROZEN_BEFORE_SUBSCRIPTION",
        "venue": VENUE,
        "dex": DEX,
        "product_class": PRODUCT_CLASS,
        "target_count": TARGET_COUNT,
        "run_seconds": RUN_SECONDS,
        "watch_market_count": TARGET_COUNT,
        "actionable_market_count": 0,
        "external_one_minute_bar_type_count": TARGET_COUNT,
        "manual_market_input": False,
        "post_hoc_market_substitution": False,
        "automatic_retry": False,
        "selection_source_snapshot_hash": source_hash,
        "ordered_market_set_hash": market_set_hash,
        "pit_snapshot_hash": snapshot.snapshot_hash,
        "run_manifest_hash": manifest.manifest_hash,
        "acquisition_attempt_identity": attempt_identity,
        "acquisition_attempt_identity_hash": attempt_hash,
        "ordered_frozen_markets": market_set["markets"],
    }
    return plan, snapshot, manifest


def build_probe_command(
    *,
    python_executable: str,
    evidence_root: Path,
    manifest_path: Path,
    snapshot_path: Path,
    probe_result_path: Path,
    markets: Sequence[FrozenMarket],
    bar_type_builder: Callable[[str], str],
) -> list[str]:
    if len(markets) != TARGET_COUNT:
        raise AcquisitionContractError("probe requires exactly 20 frozen watch markets")
    bar_types = tuple(bar_type_builder(item.instrument_id) for item in markets)
    if len(bar_types) != TARGET_COUNT or len(set(bar_types)) != TARGET_COUNT:
        raise AcquisitionContractError("probe requires exactly 20 unique external 1m BarTypes")
    command = [
        python_executable,
        "scripts/e4_nautilus_public_data_probe.py",
        "--evidence-path",
        str(evidence_root),
        "--result-path",
        str(probe_result_path),
        "--manifest",
        str(manifest_path),
        "--snapshot",
        str(snapshot_path),
    ]
    for market in markets:
        command.extend(("--watch-market-id", market.market_id))
    for bar_type in bar_types:
        command.extend(("--bar-type", bar_type))
    command.extend(("--run-seconds", str(RUN_SECONDS)))
    return command


def _expected_streams(markets: Sequence[FrozenMarket]) -> set[str]:
    return {
        f"{market.market_id}:{kind}"
        for market in markets
        for kind in ("BBO", "TRADE", "BAR")
    }


def provider_capture_complete(
    probe_result: Mapping[str, object],
    markets: Sequence[FrozenMarket],
) -> bool:
    observation = probe_result.get("observation")
    if not isinstance(observation, dict):
        return False
    raw_expected = observation.get("expected_streams")
    raw_observed = observation.get("observed_streams")
    raw_missing = observation.get("missing_streams")
    if (
        not isinstance(raw_expected, list)
        or not all(isinstance(item, str) for item in raw_expected)
        or not isinstance(raw_observed, list)
        or not all(isinstance(item, str) for item in raw_observed)
        or not isinstance(raw_missing, list)
    ):
        return False
    expected = _expected_streams(markets)
    return all(
        (
            probe_result.get("status") == "PASS",
            probe_result.get("bounded_run_seconds") == RUN_SECONDS,
            observation.get("provider_observation_pass") is True,
            observation.get("quote_observed") is True,
            observation.get("trade_observed") is True,
            observation.get("bar_subscription_registered") is True,
            observation.get("finalized_bar_callback_observed") is True,
            observation.get("finalized_bar_evidence_persisted") is True,
            set(raw_expected) == expected,
            set(raw_observed) == expected,
            raw_missing == [],
        )
    )


def classify_probe_result(
    return_code: int,
    probe_result: Mapping[str, object],
    markets: Sequence[FrozenMarket],
) -> str:
    if return_code == PASS and provider_capture_complete(probe_result, markets):
        return "COMPLETE"
    if return_code == APPLICATION_OR_PROVIDER_RUNTIME_FAILURE or probe_result.get(
        "status"
    ) == "APPLICATION_FAILURE":
        return "APPLICATION_OR_PROVIDER_RUNTIME_FAILURE"
    if return_code == PROVIDER_DATA_INCOMPLETE or probe_result.get("status") == (
        "PROVIDER_DATA_INCOMPLETE"
    ):
        return "PROVIDER_DATA_INCOMPLETE"
    if return_code == PASS:
        return "PROVIDER_DATA_INCOMPLETE"
    return "APPLICATION_OR_PROVIDER_RUNTIME_FAILURE"


def _result_base(
    *,
    exact_head: str | None,
    exact_tree: str | None,
    github_run_id: str,
    github_run_attempt: int,
) -> dict[str, object]:
    return {
        "schema_version": RESULT_SCHEMA,
        "exact_head": exact_head,
        "exact_tree": exact_tree,
        "github_run_id": github_run_id,
        "github_run_attempt": github_run_attempt,
        "target_count": TARGET_COUNT,
        "run_seconds": RUN_SECONDS,
        "G4E8": "NOT_PROVEN",
        "candidate_only": True,
        "canonical_acceptance_required": True,
        "public_data_only": True,
        "zero_credentials": True,
        "zero_execution_client": True,
        "zero_signing": True,
        "zero_exchange_write": True,
        "automatic_retry": False,
        "manual_market_input": False,
        "post_hoc_market_substitution": False,
    }


def run_acquisition(
    *,
    evidence_root: Path,
    result_path: Path,
    expected_head: str,
    github_run_id: str,
    github_run_attempt: int,
    selection_client: SelectionClient,
    probe_runner: Callable[..., CompletedProcessLike] = subprocess.run,
    candidate_builder: Callable[[Path], dict[str, object]] | None = None,
    instrument_mapper: Callable[[str], str] = _exact_rc5_instrument_id,
    bar_type_builder: Callable[[str], str] | None = None,
    clock_ns: Callable[[], int] = time.time_ns,
) -> int:
    """Execute one fixed attempt with no retries, extension, or substitution."""
    exact_head: str | None = None
    exact_tree: str | None = None
    try:
        assert_public_only(env=os.environ)
        from trader_assist_v0.nautilus_e4.host import assert_exact_nautilus_version

        assert_exact_nautilus_version()
        exact_head, exact_tree = bind_exact_git_identity(expected_head)
        source = fetch_selection_source(selection_client, clock_ns=clock_ns)
        source_path = evidence_root / "selection-source-snapshot.json"
        _write_json(source_path, source)
        markets = freeze_market_selection(source, instrument_mapper=instrument_mapper)
        market_set = ordered_market_set_document(markets)
        _write_json(evidence_root / "ordered-frozen-market-set.json", market_set)
        plan, snapshot, manifest = build_acquisition_plan(
            source=source,
            markets=markets,
            exact_head=exact_head,
            exact_tree=exact_tree,
            github_run_id=github_run_id,
            github_run_attempt=github_run_attempt,
        )
        _write_json(evidence_root / "acquisition-plan.json", plan)
        store = EvidenceStore(evidence_root)
        store.initialize(manifest, snapshot)

        if bar_type_builder is None:
            from scripts.e4_nautilus_public_data_probe import _external_minute_bar_type

            bar_type_builder = _external_minute_bar_type
        probe_result_path = evidence_root / "e4-probe-result.json"
        command = build_probe_command(
            python_executable=sys.executable,
            evidence_root=evidence_root,
            manifest_path=store.manifest_path,
            snapshot_path=store.snapshot_path,
            probe_result_path=probe_result_path,
            markets=markets,
            bar_type_builder=bar_type_builder,
        )
        completed = probe_runner(command, check=False)
        if not probe_result_path.is_file():
            raise AcquisitionContractError("E4 probe did not persist its result")
        import json

        raw_probe = json.loads(probe_result_path.read_text(encoding="utf-8"))
        if not isinstance(raw_probe, dict):
            raise AcquisitionContractError("E4 probe result is not an object")
        classification = classify_probe_result(completed.returncode, raw_probe, markets)
        observation = raw_probe.get("observation")
        missing_streams = (
            observation.get("missing_streams", []) if isinstance(observation, dict) else []
        )
        result = {
            **_result_base(
                exact_head=exact_head,
                exact_tree=exact_tree,
                github_run_id=github_run_id,
                github_run_attempt=github_run_attempt,
            ),
            "selection_source_snapshot_hash": plan["selection_source_snapshot_hash"],
            "ordered_market_set_hash": plan["ordered_market_set_hash"],
            "run_manifest_hash": manifest.manifest_hash,
            "pit_snapshot_hash": snapshot.snapshot_hash,
            "acquisition_attempt_identity_hash": plan[
                "acquisition_attempt_identity_hash"
            ],
            "watch_market_count": len(markets),
            "external_one_minute_bar_type_count": len(markets),
            "probe_exit_code": completed.returncode,
            "e4_probe_result": raw_probe,
            "capture_health": raw_probe.get("capture_health"),
            "missing_streams": missing_streams,
        }
        if classification == "PROVIDER_DATA_INCOMPLETE":
            result["RESULT"] = "PROVIDER_DATA_INCOMPLETE"
            result["failure_class"] = "PROVIDER_OR_DATA_INCOMPLETENESS"
            _write_json(result_path, result)
            return PROVIDER_DATA_INCOMPLETE
        if classification == "APPLICATION_OR_PROVIDER_RUNTIME_FAILURE":
            result["RESULT"] = "APPLICATION_OR_PROVIDER_RUNTIME_FAILURE"
            result["failure_class"] = "APPLICATION_OR_PROVIDER_RUNTIME_FAILURE"
            _write_json(result_path, result)
            return APPLICATION_OR_PROVIDER_RUNTIME_FAILURE

        if candidate_builder is None:
            from scripts.nautilus_vnext_g4_representative_scale import (
                build_from_evidence_root,
            )

            candidate_builder = build_from_evidence_root
        candidate = candidate_builder(evidence_root)
        candidate_path = evidence_root / "representative-scale-candidate.json"
        _write_json(candidate_path, candidate)
        result.update(
            {
                "RESULT": "COMPLETE_REPRESENTATIVE_CANDIDATE_BUILT",
                "failure_class": None,
                "representative_candidate_path": candidate_path.name,
                "representative_candidate_hash": candidate.get("artifact_hash"),
            }
        )
        _write_json(result_path, result)
        return PASS
    except Exception as exc:
        failure = {
            **_result_base(
                exact_head=exact_head,
                exact_tree=exact_tree,
                github_run_id=github_run_id,
                github_run_attempt=github_run_attempt,
            ),
            "RESULT": "APPLICATION_OR_PROVIDER_RUNTIME_FAILURE",
            "failure_class": "APPLICATION_OR_PROVIDER_RUNTIME_FAILURE",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        _write_json(result_path, failure)
        return APPLICATION_OR_PROVIDER_RUNTIME_FAILURE


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--github-run-id", required=True)
    parser.add_argument("--github-run-attempt", type=int, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    from trader_assist_v0.multi_asset_shadow.hyperliquid_public import (
        HyperliquidPublicClient,
    )

    return run_acquisition(
        evidence_root=args.evidence_root,
        result_path=args.result_path,
        expected_head=args.expected_head,
        github_run_id=args.github_run_id,
        github_run_attempt=args.github_run_attempt,
        selection_client=HyperliquidPublicClient(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
