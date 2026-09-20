#!/usr/bin/env python3
# mypy: disable-error-code="import-not-found"
"""Bounded exact-rc5 Ordinary VNext G4 infrastructure qualification.

T0 controls qualify serializer/provider mechanics only. Formal causal claims
remain NOT_PROVEN unless a future accepted T2 artifact is explicitly consumed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_e4.contracts import (
    AdmittedEvent,
    DataKind,
    EvidenceState,
    SourceEvent,
)
from trader_assist_v0.nautilus_g4.catalog_bridge import build_replay_payload
from trader_assist_v0.nautilus_g4.runner import (
    RepresentativeMarketEvidence,
    assert_actual_representative_scale,
    assert_backtest_node_catalog_surface,
    assert_exact_nautilus_rc5,
    build_fill_model,
    candidate_state_isolation_plan,
    causal_claim_gate_states,
    formal_g4_acceptance,
    new_isolated_backtest_engine,
    project_provider_native_state,
)
from trader_assist_v0.nautilus_g4.t2_shadow import AcceptedRealT2Receipt
from trader_assist_v0.vnext_g4.contracts import (
    AttemptStop,
    CandidateConfig,
    CandidateManifest,
    EntryActivation,
    EvidenceArtifactHash,
    ExecutionModelConfig,
    ExitPolicy,
    G4RunManifest,
    OrderPrimitive,
    ReentryPolicy,
    WinnerConfirmation,
)

STRUCTURAL_HASH = "a" * 64
CONTROL_MARKET = "b" * 64
REPRESENTATIVE_MARKET_FLOOR = 20
CANONICAL_REPOSITORY = "woshixiong/trader-assist-v0"
CANONICAL_T2_READBACK_SCHEMA = "ROOTED_T2_CANONICAL_ACCEPTANCE_READBACK_V1"
CANONICAL_T2_READBACK_HEADING = "## ROOTED-T2 CANONICAL ACCEPTANCE READBACK V1"
CANONICAL_REPRESENTATIVE_READBACK_SCHEMA = (
    "G4_REPRESENTATIVE_SCALE_CANONICAL_ACCEPTANCE_READBACK_V1"
)
CANONICAL_REPRESENTATIVE_READBACK_HEADING = (
    "## G4 REPRESENTATIVE-SCALE CANONICAL ACCEPTANCE READBACK V1"
)
REPRESENTATIVE_ARTIFACT_SCHEMA = "G4_REPRESENTATIVE_SCALE_CANDIDATE_V1"
_CANONICAL_T2_AUTHORITY = object()
_CANONICAL_REPRESENTATIVE_AUTHORITY = object()


@dataclass(frozen=True)
class _CanonicalT2AcceptanceReadback:
    """Owner-authored GitHub readback; not constructible through the public CLI."""

    authority: object
    comment_id: int
    comment_url: str
    receipt: AcceptedRealT2Receipt


@dataclass(frozen=True)
class _CanonicalRepresentativeAcceptanceReadback:
    """Owner-authored representative-scale acceptance from the canonical repo."""

    authority: object
    comment_id: int
    comment_url: str
    receipt: dict[str, object]


def _not_proven_causal_gates() -> dict[str, str]:
    return causal_claim_gate_states(
        evidence_tier="T0_SYNTHETIC_CONTROL",
        synthetic=True,
        manual_substitution=False,
        deterministic_replay_proven=False,
        semantic_derivation_proven=False,
        validation_materialized=False,
        canonical_order_intent_proven=False,
        provider_outcome_cost_provenance_complete=False,
        restart_equivalence_proven=False,
    )


def _parse_canonical_t2_readback(
    raw_response: bytes,
    *,
    expected_comment_id: int,
) -> _CanonicalT2AcceptanceReadback:
    envelope: Any = json.loads(raw_response)
    if not isinstance(envelope, dict):
        raise ValueError("canonical T2 GitHub response must be an object")
    if envelope.get("id") != expected_comment_id:
        raise ValueError("canonical T2 comment identity mismatch")
    expected_url = re.compile(
        rf"https://github\.com/{re.escape(CANONICAL_REPOSITORY)}"
        rf"/issues/[1-9][0-9]*#issuecomment-{expected_comment_id}"
    )
    comment_url = envelope.get("html_url")
    if not isinstance(comment_url, str) or expected_url.fullmatch(comment_url) is None:
        raise ValueError("canonical T2 comment URL is outside the accepted repository")
    user = envelope.get("user")
    if (
        not isinstance(user, dict)
        or user.get("login") != CANONICAL_REPOSITORY.split("/", maxsplit=1)[0]
        or envelope.get("author_association") != "OWNER"
    ):
        raise ValueError("canonical T2 readback is not repository-owner authored")

    body = envelope.get("body")
    if not isinstance(body, str):
        raise ValueError("canonical T2 comment body must be text")
    body_match = re.fullmatch(
        re.escape(CANONICAL_T2_READBACK_HEADING)
        + r"\n\n```json\n(?P<payload>\{.*\})\n```\n?",
        body,
        flags=re.DOTALL,
    )
    if body_match is None:
        raise ValueError("canonical T2 comment does not match the readback envelope")
    payload: Any = json.loads(body_match.group("payload"))
    if not isinstance(payload, dict) or set(payload) != {
        "acceptance",
        "repository",
        "schema_version",
    }:
        raise ValueError("canonical T2 readback payload fields are not exact")
    if payload.get("schema_version") != CANONICAL_T2_READBACK_SCHEMA:
        raise ValueError("canonical T2 readback schema is not accepted")
    if payload.get("repository") != CANONICAL_REPOSITORY:
        raise ValueError("canonical T2 readback repository mismatch")
    receipt = AcceptedRealT2Receipt.model_validate(payload.get("acceptance"))
    if receipt.exact_reviewed_head != receipt.exact_implementation_head:
        raise ValueError("canonical T2 review does not bind the implementation head")
    ci_results = receipt.required_ci_run_ids_and_conclusions
    ci_bindings = tuple(result.rpartition(":") for result in ci_results)
    if (
        len(ci_results) != len(set(ci_results))
        or any(not run_id or separator != ":" for run_id, separator, _ in ci_bindings)
        or any(conclusion.lower() != "success" for _, _, conclusion in ci_bindings)
    ):
        raise ValueError("canonical T2 required CI is not uniquely successful")
    review_locator = re.compile(
        rf"https://github\.com/{re.escape(CANONICAL_REPOSITORY)}"
        r"/issues/[1-9][0-9]*#issuecomment-[1-9][0-9]*"
    )
    if review_locator.fullmatch(receipt.fresh_independent_review_locator) is None:
        raise ValueError("canonical T2 review locator is outside the accepted repository")
    return _CanonicalT2AcceptanceReadback(
        authority=_CANONICAL_T2_AUTHORITY,
        comment_id=expected_comment_id,
        comment_url=comment_url,
        receipt=receipt,
    )


def _fetch_canonical_t2_readback(
    comment_id: object,
) -> _CanonicalT2AcceptanceReadback:
    if type(comment_id) is not int or comment_id <= 0:
        raise ValueError("canonical T2 acceptance requires a positive comment ID")
    api_url = (
        f"https://api.github.com/repos/{CANONICAL_REPOSITORY}/issues/comments/"
        f"{comment_id}"
    )
    request = Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "trader-assist-vnext-g4-qualification",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=10.0) as response:
        if response.geturl() != api_url:
            raise ValueError("canonical T2 GitHub endpoint redirected")
        raw_response = response.read()
    return _parse_canonical_t2_readback(
        raw_response,
        expected_comment_id=comment_id,
    )


def _canonical_t2_state(
    comment_id: object | None,
) -> tuple[dict[str, str], dict[str, object]]:
    if comment_id is None:
        return _not_proven_causal_gates(), {
            "accepted": False,
            "reason": "NO_CANONICAL_ACCEPTED_T2_READBACK_SUPPLIED",
        }
    try:
        readback = _fetch_canonical_t2_readback(comment_id)
    except (OSError, URLError, ValueError) as exc:
        return _not_proven_causal_gates(), {
            "accepted": False,
            "reason": f"CANONICAL_T2_READBACK_REJECTED:{type(exc).__name__}",
        }
    if readback.authority is not _CANONICAL_T2_AUTHORITY:
        return _not_proven_causal_gates(), {
            "accepted": False,
            "reason": "CANONICAL_T2_READBACK_REJECTED:AUTHORITY",
        }
    receipt = readback.receipt
    return (
        causal_claim_gate_states(
            evidence_tier="T2_REAL_CAUSAL_G4_ARTIFACT",
            synthetic=False,
            manual_substitution=False,
            deterministic_replay_proven=True,
            semantic_derivation_proven=True,
            validation_materialized=True,
            canonical_order_intent_proven=True,
            provider_outcome_cost_provenance_complete=True,
            restart_equivalence_proven=True,
        ),
        {
            "accepted": True,
            "reason": None,
            "comment_id": readback.comment_id,
            "comment_url": readback.comment_url,
            "binding_identity_hash": receipt.evidence_hash,
            "source_root_hash": receipt.accepted_t2_source_root_hash,
            "artifact_candidate_hash": receipt.t2_artifact_candidate_hash,
            "implementation_head": receipt.exact_implementation_head,
            "implementation_tree": receipt.exact_implementation_tree,
            "required_ci": list(receipt.required_ci_run_ids_and_conclusions),
            "review_result_key": receipt.fresh_independent_review_result_key,
            "review_locator": receipt.fresh_independent_review_locator,
            "reviewed_head": receipt.exact_reviewed_head,
            "canonical_receipt_key": receipt.canonical_acceptance_receipt_key,
        },
    )


def _candidate(candidate_id: str = "qualification-reference") -> CandidateManifest:
    return CandidateManifest.create(
        candidate_id=candidate_id,
        structural_component_manifest_hash=STRUCTURAL_HASH,
        config=CandidateConfig(
            entry_activation=EntryActivation.EA1,
            attempt_stop=AttemptStop.AP0,
            room_to_cost_k=Decimal("2"),
            reentry_policy=ReentryPolicy.NO_REENTRY_REFERENCE,
            winner_confirmation=WinnerConfirmation.WC0,
            winner_progress_bps=Decimal("3"),
            exit_policy=ExitPolicy.X1,
            comparison_role=(
                "REFERENCE" if candidate_id.endswith("reference") else "CHALLENGER"
            ),
        ),
    )


def _execution() -> ExecutionModelConfig:
    return ExecutionModelConfig(
        book_type="L1_MBP",
        order_primitive=OrderPrimitive.MARKETABLE,
        prob_fill_on_limit=Decimal("0"),
        prob_slippage=Decimal("0"),
        trade_execution=True,
        queue_position=False,
        liquidity_consumption=True,
        fill_limit_at_price=False,
        fill_stop_at_price=False,
        random_seed=7,
        execution_model_limited=True,
    )


def _admitted(ordinal: int) -> AdmittedEvent:
    source = SourceEvent.create(
        market_id=CONTROL_MARKET,
        expression_id="formal-g4-control",
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id="ETH-USD-PERP.HYPERLIQUID",
        data_kind=DataKind.BAR,
        source_event_id=f"formal-g4-control-{ordinal}",
        native_trade_id=None,
        provider_aggressor_side=None,
        event_context="T0_SYNTHETIC_CONTROL",
        ts_event=ordinal * 10,
        ts_init=ordinal * 10 + 1,
        true_network_receive_ts=None,
        payload={"close": str(100 + ordinal)},
    )
    return AdmittedEvent.create(
        schema_version="E4_CAPTURE_V1",
        process_epoch="formal-g4-process",
        continuity_epoch="formal-g4-continuity",
        admission_epoch="formal-g4-admission",
        admission_ordinal=ordinal,
        admission_ts=ordinal * 10 + 2,
        source_identity=source.replay_identity,
        out_of_order=False,
        continuity_state=EvidenceState.COMPLETE,
        source=source,
    )


def _t0_serializer_probe() -> dict[str, object]:
    events = (_admitted(1), _admitted(2))
    payload = build_replay_payload(events)
    restarted = tuple(
        AdmittedEvent.model_validate_json(event.model_dump_json()) for event in events
    )
    restarted_payload = build_replay_payload(restarted)
    if payload != restarted_payload:
        raise AssertionError("T0 serializer restart changed the replay payload")
    return {
        "control_tier": "T0_SYNTHETIC_CONTROL",
        "control_only": True,
        "replay_payload_sha256": sha256_hex(payload),
        "event_count": len(events),
        "restart_replay_identical": True,
        "formal_causal_credit": False,
    }


def _controlled_backtest_node_probe(root: Path) -> dict[str, object]:
    """Run a non-promotional provider-native control and inspect Cache/Portfolio."""
    from nautilus_trader.backtest import BacktestNode
    from nautilus_trader.config import (
        BacktestDataConfig,
        BacktestEngineConfig,
        BacktestRunConfig,
        BacktestVenueConfig,
    )
    from nautilus_trader.model import (
        AccountType,
        BookType,
        Currency,
        OmsType,
        Price,
        Quantity,
        QuoteTick,
    )
    from nautilus_trader.persistence import ParquetDataCatalog
    from nautilus_trader.testkit.providers import TestInstrumentProvider
    from nautilus_trader.trading import EmaCrossConfig

    instrument = TestInstrumentProvider.default_fx_ccy("AUD/USD")
    catalog = ParquetDataCatalog(str(root))
    mids = tuple(
        Decimal(value)
        for value in (
            "1.00000",
            "1.00000",
            "1.00000",
            "1.00000",
            "1.00000",
            "1.00100",
            "1.00200",
            "1.00300",
            "1.00400",
            "1.00500",
            "1.00400",
            "1.00200",
            "1.00000",
            "0.99800",
            "0.99600",
            "0.99500",
            "0.99700",
            "1.00000",
            "1.00300",
            "1.00600",
        )
    )
    start_ns = 1_700_000_000_000_000_000
    ticks = [
        QuoteTick(
            instrument_id=instrument.id,
            bid_price=Price.from_str(f"{mid:.5f}"),
            ask_price=Price.from_str(f"{mid + Decimal('0.00010'):.5f}"),
            bid_size=Quantity.from_int(1_000_000),
            ask_size=Quantity.from_int(1_000_000),
            ts_event=start_ns + index * 1_000_000_000,
            ts_init=start_ns + index * 1_000_000_000,
        )
        for index, mid in enumerate(mids)
    ]
    catalog.write_instruments([instrument])
    catalog.write_quote_ticks(ticks)
    venue = BacktestVenueConfig(
        name=str(instrument.id.venue),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        book_type=BookType.L1_MBP,
        base_currency=Currency.from_str("USD"),
        starting_balances=["1_000_000 USD"],
    )
    data = BacktestDataConfig(
        data_type="QuoteTick",
        catalog_path=str(root),
        instrument_id=instrument.id,
        start_time=ticks[0].ts_init,
        end_time=ticks[-1].ts_init + 1,
    )
    config = BacktestRunConfig(
        venues=[venue],
        data=[data],
        engine=BacktestEngineConfig(),
        dispose_on_completion=False,
    )
    node = BacktestNode(configs=[config])
    try:
        node.build()
        node.add_builtin_strategy(
            config.id,
            "EmaCross",
            EmaCrossConfig(
                instrument_id=instrument.id,
                trade_size=Quantity.from_int(100_000),
                fast_period=2,
                slow_period=4,
            ),
        )
        results = node.run()
        cache = node.get_engine_cache(config.id)
        portfolio = node.get_engine_portfolio(config.id)
        if cache is None or portfolio is None:
            raise AssertionError("BacktestNode did not retain public Cache/Portfolio state")
        projection = project_provider_native_state(
            cache,
            portfolio,
            venue=instrument.id.venue,
        )
        if not projection.cache_type.startswith(
            "nautilus_trader."
        ) or not projection.portfolio_type.startswith("nautilus_trader."):
            raise AssertionError("provider state projection lacks Nautilus provenance")
        if projection.filled_order_count < 1:
            raise AssertionError("T0 provider control produced no provider-owned fill state")
        return {
            "control_tier": "T0_SYNTHETIC_CONTROL",
            "control_only": True,
            "formal_causal_credit": False,
            "backtest_result_count": len(results),
            "provider_state": projection.model_dump(mode="json"),
        }
    finally:
        node.dispose()


def _assert_sha256(value: object, *, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field} must be a SHA-256 hex string")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{field} must be a SHA-256 hex string") from exc
    return value


def _assert_git_oid(value: object, *, field: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError(f"{field} must be a lowercase Git commit/tree OID")
    return value


def _parse_canonical_representative_readback(
    raw_response: bytes,
    *,
    expected_comment_id: int,
) -> _CanonicalRepresentativeAcceptanceReadback:
    envelope: Any = json.loads(raw_response)
    if not isinstance(envelope, dict):
        raise ValueError("canonical representative GitHub response must be an object")
    if envelope.get("id") != expected_comment_id:
        raise ValueError("canonical representative comment identity mismatch")
    expected_url = re.compile(
        rf"https://github\.com/{re.escape(CANONICAL_REPOSITORY)}"
        rf"/issues/[1-9][0-9]*#issuecomment-{expected_comment_id}"
    )
    comment_url = envelope.get("html_url")
    if not isinstance(comment_url, str) or expected_url.fullmatch(comment_url) is None:
        raise ValueError("canonical representative comment URL is outside the repository")
    user = envelope.get("user")
    if (
        not isinstance(user, dict)
        or user.get("login") != CANONICAL_REPOSITORY.split("/", maxsplit=1)[0]
        or envelope.get("author_association") != "OWNER"
    ):
        raise ValueError("canonical representative readback is not owner authored")
    body = envelope.get("body")
    if not isinstance(body, str):
        raise ValueError("canonical representative comment body must be text")
    body_match = re.fullmatch(
        re.escape(CANONICAL_REPRESENTATIVE_READBACK_HEADING)
        + r"\n\n```json\n(?P<payload>\{.*\})\n```\n?",
        body,
        flags=re.DOTALL,
    )
    if body_match is None:
        raise ValueError("canonical representative comment envelope is not exact")
    payload: Any = json.loads(body_match.group("payload"))
    if not isinstance(payload, dict) or set(payload) != {
        "acceptance",
        "repository",
        "schema_version",
    }:
        raise ValueError("canonical representative payload fields are not exact")
    if payload.get("schema_version") != CANONICAL_REPRESENTATIVE_READBACK_SCHEMA:
        raise ValueError("canonical representative readback schema is not accepted")
    if payload.get("repository") != CANONICAL_REPOSITORY:
        raise ValueError("canonical representative readback repository mismatch")
    receipt = payload.get("acceptance")
    receipt_fields = {
        "acceptance_claim",
        "canonical_acceptance_receipt_key",
        "exact_implementation_head",
        "exact_implementation_tree",
        "exact_reviewed_head",
        "fresh_independent_review_locator",
        "fresh_independent_review_result_key",
        "fresh_independent_review_verdict",
        "receipt_hash",
        "representative_artifact_hash",
        "representative_market_count",
        "representative_market_set_hash",
        "required_ci_run_ids_and_conclusions",
        "source_e4_exact_head",
        "source_e4_exact_tree",
        "source_e4_manifest_hash",
        "task_id",
    }
    if not isinstance(receipt, dict) or set(receipt) != receipt_fields:
        raise ValueError("canonical representative acceptance fields are not exact")
    if receipt.get("acceptance_claim") != "ACCEPTED":
        raise ValueError("canonical representative acceptance claim is not accepted")
    task_id = receipt.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        raise ValueError("canonical representative acceptance task identity is missing")
    for field in (
        "representative_artifact_hash",
        "source_e4_manifest_hash",
        "representative_market_set_hash",
        "receipt_hash",
    ):
        _assert_sha256(receipt.get(field), field=field)
    for field in (
        "source_e4_exact_head",
        "source_e4_exact_tree",
        "exact_implementation_head",
        "exact_implementation_tree",
        "exact_reviewed_head",
    ):
        _assert_git_oid(receipt.get(field), field=field)
    market_count = receipt.get("representative_market_count")
    if type(market_count) is not int or market_count < REPRESENTATIVE_MARKET_FLOOR:
        raise ValueError("canonical representative market count is below the floor")
    ci_results = receipt.get("required_ci_run_ids_and_conclusions")
    if not isinstance(ci_results, list) or not ci_results:
        raise ValueError("canonical representative required CI is missing")
    ci_bindings = tuple(
        result.rpartition(":") for result in ci_results if isinstance(result, str)
    )
    if (
        len(ci_bindings) != len(ci_results)
        or len(ci_results) != len(set(ci_results))
        or any(not run_id or separator != ":" for run_id, separator, _ in ci_bindings)
        or any(conclusion.lower() != "success" for _, _, conclusion in ci_bindings)
    ):
        raise ValueError("canonical representative required CI is not uniquely successful")
    if receipt.get("fresh_independent_review_verdict") != "PASS":
        raise ValueError("canonical representative independent review did not pass")
    review_result_key = receipt.get("fresh_independent_review_result_key")
    if not isinstance(review_result_key, str) or not review_result_key:
        raise ValueError("canonical representative review result key is missing")
    review_locator = receipt.get("fresh_independent_review_locator")
    accepted_locator = re.compile(
        rf"https://github\.com/{re.escape(CANONICAL_REPOSITORY)}"
        r"/issues/[1-9][0-9]*#issuecomment-[1-9][0-9]*"
    )
    if not isinstance(review_locator, str) or accepted_locator.fullmatch(review_locator) is None:
        raise ValueError("canonical representative review locator is outside the repository")
    receipt_key = receipt.get("canonical_acceptance_receipt_key")
    if not isinstance(receipt_key, str) or not receipt_key:
        raise ValueError("canonical representative receipt key is missing")
    if receipt["exact_reviewed_head"] != receipt["exact_implementation_head"]:
        raise ValueError("canonical representative review does not bind implementation head")
    receipt_identity = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    if sha256_hex(canonical_json_bytes(receipt_identity)) != receipt["receipt_hash"]:
        raise ValueError("canonical representative receipt hash does not bind its contents")
    return _CanonicalRepresentativeAcceptanceReadback(
        authority=_CANONICAL_REPRESENTATIVE_AUTHORITY,
        comment_id=expected_comment_id,
        comment_url=comment_url,
        receipt=receipt,
    )


def _fetch_canonical_representative_readback(
    comment_id: object,
) -> _CanonicalRepresentativeAcceptanceReadback:
    if type(comment_id) is not int or comment_id <= 0:
        raise ValueError("canonical representative acceptance requires a positive comment ID")
    api_url = (
        f"https://api.github.com/repos/{CANONICAL_REPOSITORY}/issues/comments/"
        f"{comment_id}"
    )
    request = Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "trader-assist-vnext-g4-qualification",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=10.0) as response:
        if response.geturl() != api_url:
            raise ValueError("canonical representative GitHub endpoint redirected")
        raw_response = response.read()
    return _parse_canonical_representative_readback(
        raw_response,
        expected_comment_id=comment_id,
    )


def _validate_representative_artifact(raw: Any) -> tuple[dict[str, object], tuple[str, ...]]:
    if not isinstance(raw, dict):
        raise ValueError("representative evidence must be an object")
    if raw.get("synthetic") is not False or raw.get("manual_substitution") is not False:
        raise ValueError("synthetic/manual evidence cannot count for G4E8")
    expected_fields = {
        "artifact_hash",
        "candidate_only",
        "canonical_acceptance_required",
        "evidence_tier",
        "manual_substitution",
        "markets",
        "public_data_only",
        "repository",
        "representative_market_count",
        "representative_market_set_hash",
        "schema_version",
        "source_artifact_hashes",
        "source_e4_exact_head",
        "source_e4_exact_tree",
        "source_e4_manifest_hash",
        "source_e4_snapshot_hash",
        "synthetic",
        "unique_retained_event_identity_count",
        "zero_credentials",
        "zero_exchange_write",
        "zero_execution_client",
        "zero_signing",
    }
    if set(raw) != expected_fields:
        raise ValueError("representative evidence fields are not exact")
    artifact_hash = _assert_sha256(raw.get("artifact_hash"), field="artifact_hash")
    identity = {key: value for key, value in raw.items() if key != "artifact_hash"}
    if sha256_hex(canonical_json_bytes(identity)) != artifact_hash:
        raise ValueError("representative evidence artifact hash does not bind its contents")
    required_identity = (
        raw.get("schema_version") == REPRESENTATIVE_ARTIFACT_SCHEMA,
        raw.get("repository") == CANONICAL_REPOSITORY,
        raw.get("candidate_only") is True,
        raw.get("canonical_acceptance_required") is True,
        raw.get("evidence_tier")
        == "E4_PUBLIC_PROVIDER_REPRESENTATIVE_SCALE_CANDIDATE",
        raw.get("synthetic") is False,
        raw.get("manual_substitution") is False,
        raw.get("public_data_only") is True,
        raw.get("zero_credentials") is True,
        raw.get("zero_execution_client") is True,
        raw.get("zero_signing") is True,
        raw.get("zero_exchange_write") is True,
    )
    if not all(required_identity):
        raise ValueError("representative evidence violates the public candidate boundary")
    source_manifest_hash = _assert_sha256(
        raw.get("source_e4_manifest_hash"), field="source_e4_manifest_hash"
    )
    _assert_sha256(raw.get("source_e4_snapshot_hash"), field="source_e4_snapshot_hash")
    _assert_git_oid(raw.get("source_e4_exact_head"), field="source_e4_exact_head")
    _assert_git_oid(raw.get("source_e4_exact_tree"), field="source_e4_exact_tree")
    source_artifact_hashes = raw.get("source_artifact_hashes")
    if not isinstance(source_artifact_hashes, dict) or not source_artifact_hashes:
        raise ValueError("representative evidence source artifact hashes are missing")
    for name, digest in source_artifact_hashes.items():
        if not isinstance(name, str) or not name:
            raise ValueError("representative evidence source artifact name is invalid")
        _assert_sha256(digest, field=f"source_artifact_hashes[{name}]")
    records_raw = raw.get("markets")
    if not isinstance(records_raw, list):
        raise ValueError("representative evidence requires source-bound market records")
    records = tuple(RepresentativeMarketEvidence.model_validate(item) for item in records_raw)
    if any(item.source_e4_manifest_hash != source_manifest_hash for item in records):
        raise ValueError("representative market record source manifest mismatch")
    if any(item.event_count != len(item.source_event_hashes) for item in records):
        raise ValueError("representative market event count is not source-identity bound")
    markets = assert_actual_representative_scale(records)
    market_set_hash = _assert_sha256(
        raw.get("representative_market_set_hash"),
        field="representative_market_set_hash",
    )
    if sha256_hex(canonical_json_bytes(list(markets))) != market_set_hash:
        raise ValueError("representative market-set hash does not bind the market set")
    if raw.get("representative_market_count") != len(markets):
        raise ValueError("representative market count does not bind the market set")
    event_count = sum(len(item.source_event_hashes) for item in records)
    if raw.get("unique_retained_event_identity_count") != event_count:
        raise ValueError("representative retained-event count does not bind identities")
    return raw, markets


def _representative_scale_probe(
    path: Path | None,
    canonical_acceptance_comment_id: int | None = None,
    *,
    expected_head: str = "0" * 40,
    expected_tree: str = "0" * 40,
) -> dict[str, object]:
    if path is None:
        return {
            "status": "NOT_PROVEN",
            "representative_evidence_supplied": False,
            "actual_representative_market_count": 0,
            "reason": "NO_ACCEPTED_T2_REPRESENTATIVE_EVIDENCE_SUPPLIED",
        }
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    artifact, markets = _validate_representative_artifact(raw)
    not_proven = {
        "status": "NOT_PROVEN",
        "representative_evidence_supplied": True,
        "actual_representative_market_count": len(markets),
        "canonical_acceptance_comment_id": canonical_acceptance_comment_id,
    }
    if canonical_acceptance_comment_id is None:
        return {
            **not_proven,
            "reason": "NO_CANONICAL_REPRESENTATIVE_ACCEPTANCE_READBACK_SUPPLIED",
        }
    try:
        readback = _fetch_canonical_representative_readback(
            canonical_acceptance_comment_id
        )
    except (OSError, URLError, ValueError) as exc:
        return {
            **not_proven,
            "reason": (
                "CANONICAL_REPRESENTATIVE_READBACK_REJECTED:"
                f"{type(exc).__name__}"
            ),
        }
    receipt = readback.receipt
    binding_matches = (
        readback.authority is _CANONICAL_REPRESENTATIVE_AUTHORITY,
        receipt["representative_artifact_hash"] == artifact["artifact_hash"],
        receipt["source_e4_manifest_hash"] == artifact["source_e4_manifest_hash"],
        receipt["source_e4_exact_head"] == artifact["source_e4_exact_head"],
        receipt["source_e4_exact_tree"] == artifact["source_e4_exact_tree"],
        receipt["representative_market_set_hash"]
        == artifact["representative_market_set_hash"],
        receipt["representative_market_count"]
        == artifact["representative_market_count"],
        receipt["exact_implementation_head"] == expected_head,
        receipt["exact_implementation_tree"] == expected_tree,
    )
    if not all(binding_matches):
        return {
            **not_proven,
            "reason": "CANONICAL_REPRESENTATIVE_READBACK_REJECTED:BINDING",
        }
    return {
        "status": "PASS",
        "representative_evidence_supplied": True,
        "actual_representative_market_count": len(markets),
        "reason": None,
        "canonical_acceptance_comment_id": readback.comment_id,
        "canonical_acceptance_comment_url": readback.comment_url,
        "canonical_acceptance_receipt_key": receipt[
            "canonical_acceptance_receipt_key"
        ],
        "canonical_acceptance_receipt_hash": receipt["receipt_hash"],
        "representative_artifact_hash": artifact["artifact_hash"],
        "representative_market_set_hash": artifact[
            "representative_market_set_hash"
        ],
        "source_e4_manifest_hash": artifact["source_e4_manifest_hash"],
        "accepted_required_ci": receipt["required_ci_run_ids_and_conclusions"],
        "accepted_review_locator": receipt["fresh_independent_review_locator"],
    }


def _e4_probe_state(
    path: Path | None,
    *,
    expected_head: str,
    expected_tree: str,
) -> dict[str, object]:
    if path is None:
        return {"status": "NOT_PROVEN", "source_hash": None}
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("same-job E4 probe result must be an object")
    observation = raw.get("observation")
    required = (
        raw.get("status") == "PASS",
        raw.get("exact_head") == expected_head,
        raw.get("exact_tree") == expected_tree,
        raw.get("public_data_only") is True,
        raw.get("zero_credentials") is True,
        raw.get("zero_execution_client") is True,
        raw.get("zero_signing") is True,
        raw.get("zero_exchange_write") is True,
        isinstance(observation, dict),
        isinstance(observation, dict) and observation.get("quote_observed") is True,
        isinstance(observation, dict) and observation.get("trade_observed") is True,
        isinstance(observation, dict)
        and observation.get("finalized_bar_callback_observed") is True,
        isinstance(observation, dict)
        and observation.get("finalized_bar_evidence_persisted") is True,
    )
    if not all(required):
        return {
            "status": "NOT_PROVEN",
            "source_hash": sha256_hex(canonical_json_bytes(raw)),
        }
    return {
        "status": "PASS_REQUIRES_EXACT_HEAD_E4_CI",
        "source_hash": sha256_hex(canonical_json_bytes(raw)),
    }


def qualify(
    representative_evidence: Path | None,
    e4_probe_result: Path | None,
    canonical_t2_acceptance_comment_id: int | None = None,
    canonical_representative_acceptance_comment_id: int | None = None,
) -> dict[str, object]:
    from nautilus_trader.backtest import BacktestEngine
    from nautilus_trader.execution import ProbabilisticFillModel

    assert_exact_nautilus_rc5()
    assert_backtest_node_catalog_surface()
    reference = _candidate()
    challenger = _candidate("qualification-challenger")
    if len(candidate_state_isolation_plan((reference, challenger))) != 2:
        raise AssertionError("candidate isolation plan did not retain both identities")
    fill_model = build_fill_model(_execution())
    if not isinstance(fill_model, ProbabilisticFillModel):
        raise AssertionError("provider-native ProbabilisticFillModel was not consumed")

    first_engine = new_isolated_backtest_engine(reference)
    second_engine = new_isolated_backtest_engine(challenger)
    try:
        if not isinstance(first_engine, BacktestEngine) or not isinstance(
            second_engine, BacktestEngine
        ):
            raise AssertionError("provider-native BacktestEngine was not consumed")
        if first_engine is second_engine:
            raise AssertionError("candidate execution state leaked into one shared engine")
    finally:
        first_engine.dispose()
        second_engine.dispose()

    serializer = _t0_serializer_probe()
    with TemporaryDirectory(prefix="trade-os-formal-g4-") as directory:
        provider = _controlled_backtest_node_probe(Path(directory))
    git_sha = os.environ.get("G4_EXACT_HEAD", "0" * 40)
    git_tree = os.environ.get("G4_EXACT_TREE", "0" * 40)
    if len(git_sha) != 40 or len(git_tree) != 40:
        raise AssertionError("exact-head and exact-tree identity must be supplied by the harness")
    scale = _representative_scale_probe(
        representative_evidence,
        canonical_representative_acceptance_comment_id,
        expected_head=git_sha,
        expected_tree=git_tree,
    )
    e4_probe = _e4_probe_state(
        e4_probe_result,
        expected_head=git_sha,
        expected_tree=git_tree,
    )
    manifest = G4RunManifest.create(
        run_id=f"formal-g4-control-{git_sha[:12]}",
        git_sha=git_sha,
        git_tree=git_tree,
        source_e4_manifest_hash="c" * 64,
        source_pit_snapshot_hash="d" * 64,
        source_evidence_artifact_hashes=(
            EvidenceArtifactHash(
                name="t0-serializer-control",
                sha256=str(serializer["replay_payload_sha256"]),
            ),
        ),
        structural_component_manifest_hash=STRUCTURAL_HASH,
        execution_model=_execution(),
        candidates=(reference, challenger),
        trial_adaptivity_id="formal-g4-control-trial-v1",
        cutoff_id="formal-g4-control-cutoff-v1",
    )

    provider_state = provider["provider_state"]
    assert isinstance(provider_state, dict)
    causal_gates, t2_state = _canonical_t2_state(
        canonical_t2_acceptance_comment_id
    )
    ladder = {
        "G4E0": "PASS",
        "G4E1": causal_gates["G4E1"],
        "G4E2": causal_gates["G4E2"],
        "G4E3": "PASS",
        "G4E4": "PASS",
        "G4E5": causal_gates["G4E5"],
        "G4E6": str(e4_probe["status"]),
        "G4E7": causal_gates["G4E7"],
        "G4E8": str(scale["status"]),
    }
    return {
        "schema_version": "VNEXT_FORMAL_G4_TECHNICAL_QUALIFICATION_RESULT_V2R2",
        "status": "TECHNICAL_G4_PARTIAL",
        "nautilus_version": "2.0.0rc5",
        "exact_head": git_sha,
        "exact_tree": git_tree,
        "g4_manifest_hash": manifest.manifest_hash,
        "g4e0_contract_identity": "PASS",
        "g4e1_deterministic_causal_replay": causal_gates["G4E1"],
        "g4e2_vnext_decision_parity": causal_gates["G4E2"],
        "g4e3_explicit_execution_model": "PASS",
        "g4e4_candidate_state_isolation": "PASS",
        "g4e5_fill_fee_outcome_report_parity": causal_gates["G4E5"],
        "g4e6_zero_write_live_path_composition": e4_probe["status"],
        "g4e7_reconnect_restart_nonregression": causal_gates["G4E7"],
        "g4e8_representative_scale_runtime": scale["status"],
        "formal_g4_technical_acceptance": formal_g4_acceptance(ladder),
        "representative_scale_boundary": REPRESENTATIVE_MARKET_FLOOR,
        "representative_evidence_supplied": scale["representative_evidence_supplied"],
        "actual_representative_market_count": scale[
            "actual_representative_market_count"
        ],
        "g4e8_reason": scale["reason"],
        "g4e8_canonical_acceptance_comment_id": scale.get(
            "canonical_acceptance_comment_id"
        ),
        "g4e8_canonical_acceptance_comment_url": scale.get(
            "canonical_acceptance_comment_url"
        ),
        "g4e8_canonical_acceptance_receipt_key": scale.get(
            "canonical_acceptance_receipt_key"
        ),
        "g4e8_canonical_acceptance_receipt_hash": scale.get(
            "canonical_acceptance_receipt_hash"
        ),
        "g4e8_representative_artifact_hash": scale.get(
            "representative_artifact_hash"
        ),
        "g4e8_representative_market_set_hash": scale.get(
            "representative_market_set_hash"
        ),
        "g4e8_source_e4_manifest_hash": scale.get("source_e4_manifest_hash"),
        "g4e8_accepted_required_ci": scale.get("accepted_required_ci"),
        "g4e8_accepted_review_locator": scale.get("accepted_review_locator"),
        "t2_real_causal_artifact_supplied": t2_state["accepted"],
        "t2_absence_reason": t2_state["reason"],
        "t2_canonical_acceptance_comment_id": t2_state.get("comment_id"),
        "t2_canonical_acceptance_comment_url": t2_state.get("comment_url"),
        "t2_binding_identity_hash": t2_state.get("binding_identity_hash"),
        "t2_accepted_source_root_hash": t2_state.get("source_root_hash"),
        "t2_accepted_artifact_candidate_hash": t2_state.get(
            "artifact_candidate_hash"
        ),
        "t2_accepted_implementation_head": t2_state.get("implementation_head"),
        "t2_accepted_implementation_tree": t2_state.get("implementation_tree"),
        "t2_accepted_required_ci": t2_state.get("required_ci"),
        "t2_accepted_review_result_key": t2_state.get("review_result_key"),
        "t2_accepted_review_locator": t2_state.get("review_locator"),
        "t2_accepted_reviewed_head": t2_state.get("reviewed_head"),
        "t2_canonical_receipt_key": t2_state.get("canonical_receipt_key"),
        "provider_native_backtest_engine": True,
        "provider_native_fill_model": True,
        "backtest_node_catalog_surface": True,
        "provider_state_source_api": provider_state["source_api"],
        "controlled_provider_order_count": provider_state["order_count"],
        "controlled_provider_filled_order_count": provider_state["filled_order_count"],
        "controlled_provider_position_count": provider_state["position_count"],
        "controlled_provider_account_count": provider_state["account_count"],
        "controlled_provider_state_hash": provider_state["state_hash"],
        "controlled_replay_is_representative_evidence": False,
        "t0_controls_are_formal_causal_proof": False,
        "t0_serializer_restart_identical": serializer["restart_replay_identical"],
        "same_job_e4_probe_result_hash": e4_probe["source_hash"],
        "derived_cache_is_authoritative_market_truth": False,
        "strategy_edge_proven": False,
        "confirmatory_e5_open": False,
        "private_api": False,
        "signing": False,
        "exchange_write": False,
        "venue_submitted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-path", type=Path, required=True)
    parser.add_argument("--representative-evidence", type=Path)
    parser.add_argument("--e4-probe-result", type=Path)
    parser.add_argument("--canonical-t2-acceptance-comment-id", type=int)
    parser.add_argument("--canonical-representative-acceptance-comment-id", type=int)
    args = parser.parse_args()
    result = qualify(
        args.representative_evidence,
        args.e4_probe_result,
        args.canonical_t2_acceptance_comment_id,
        args.canonical_representative_acceptance_comment_id,
    )
    args.result_path.parent.mkdir(parents=True, exist_ok=True)
    args.result_path.write_text(
        json.dumps(result, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
