from __future__ import annotations

import copy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trader_assist_v0.first_launch.market_data import context_from_websocket, evidence_from_raw
from trader_assist_v0.first_launch.signal_context import (
    ContextError,
    ContextObservation,
    ContextSeries,
    ContextSummary,
    PriceOiClassification,
    _build_summary,
    _hash,
    _validated_context_observation,
    _validated_context_summary,
)

BASE = datetime(2026, 7, 14, tzinfo=UTC)


def _observation(seconds: int, price: str, oi: str):
    received = BASE + timedelta(seconds=seconds)
    raw = (
        '{"channel":"activeAssetCtx","data":{"coin":"ETH","ctx":'
        f'{{"markPx":"{price}","openInterest":"{oi}","funding":"0"}}}}}}'
    )
    return context_from_websocket(
        raw,
        evidence_from_raw(
            raw,
            operation="WebSocket",
            received_at=received,
            receive_sequence=seconds,
            connection_id="context-test",
        ),
    )


def _ctx_obs(
    *,
    seconds: int = 0,
    price: str = "100",
    oi: str = "10",
    funding: str = "0",
    mid: str | None = None,
    seq: int | None = None,
) -> ContextObservation:
    received = BASE + timedelta(seconds=seconds)
    ctx_fields = f'"markPx":"{price}","openInterest":"{oi}","funding":"{funding}"'
    if mid is not None:
        ctx_fields += f',"midPx":"{mid}"'
    raw = (
        '{"channel":"activeAssetCtx","data":{"coin":"ETH","ctx":'
        f'{{{ctx_fields}}}}}}}'
    )
    return context_from_websocket(
        raw,
        evidence_from_raw(
            raw,
            operation="WebSocket",
            received_at=received,
            receive_sequence=seconds if seq is None else seq,
            connection_id="context-test",
        ),
    )


def _issued_observation(**kwargs) -> ContextObservation:
    series = ContextSeries()
    return series.accept(_ctx_obs(**kwargs))


def _issued_summary_with_history() -> tuple[ContextSummary, ContextSeries]:
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10", funding="0"))
    series.accept(_ctx_obs(seconds=300, price="101", oi="11", funding="1"))
    series.accept(_ctx_obs(seconds=600, price="102", oi="12", funding="2"))
    series.accept(_ctx_obs(seconds=900, price="103", oi="13", funding="3"))
    current = series.accept(_ctx_obs(seconds=1200, price="104", oi="14", funding="4"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    return summary, series


def _reconstruct(cls: type, original: object) -> object:
    forged = object.__new__(cls)
    for field_name in original.__dict__:
        object.__setattr__(forged, field_name, getattr(original, field_name))
    return forged


def _coherently_rehash_observation(
    original: ContextObservation, **updates: object
) -> ContextObservation:
    forged = copy.copy(original)
    for field_name, value in updates.items():
        object.__setattr__(forged, field_name, value)
    object.__setattr__(forged, "canonical_hash", _hash(forged.payload()))
    return forged


def _coherently_rehash_summary(original: ContextSummary, **updates: object) -> ContextSummary:
    forged = copy.copy(original)
    for field_name, value in updates.items():
        object.__setattr__(forged, field_name, value)
    body = {
        "current": forged.current.payload(),
        "current_hash": forged.current.canonical_hash,
        "baseline_5m": None if forged.baseline_5m is None else forged.baseline_5m.payload(),
        "baseline_5m_hash": (
            None if forged.baseline_5m is None else forged.baseline_5m.canonical_hash
        ),
        "baseline_15m": None if forged.baseline_15m is None else forged.baseline_15m.payload(),
        "baseline_15m_hash": (
            None
            if forged.baseline_15m is None
            else forged.baseline_15m.canonical_hash
        ),
        "summary_cutoff": forged.summary_cutoff.isoformat(),
        "oi_delta_5m": forged.oi_delta_5m,
        "oi_pct_delta_5m": forged.oi_pct_delta_5m,
        "oi_delta_15m": forged.oi_delta_15m,
        "oi_pct_delta_15m": forged.oi_pct_delta_15m,
        "funding_delta_5m": forged.funding_delta_5m,
        "funding_delta_15m": forged.funding_delta_15m,
        "classification_5m": forged.classification_5m,
        "classification_15m": forged.classification_15m,
        "selection_proof": [item.payload() for item in forged.selection_proof],
        "selection_proof_hashes": [item.canonical_hash for item in forged.selection_proof],
    }
    object.__setattr__(forged, "canonical_hash", _hash(body))
    return forged


def test_context_summary_is_causal_and_classifies_price_oi() -> None:
    series = ContextSeries()
    series.accept(_observation(0, "100", "10"))
    series.accept(_observation(300, "101", "11"))
    summary = series.summary_at(datetime(2026, 7, 14, tzinfo=UTC) + timedelta(seconds=300))
    assert summary is not None
    assert summary.oi_delta_5m == Decimal("1")
    assert summary.classification_5m is PriceOiClassification.PRICE_UP_OI_UP


def test_retention_uses_the_latest_retained_observation_not_a_late_arrival() -> None:
    series = ContextSeries()
    series.accept(_observation(1, "100", "10"))
    series.accept(_observation(7_201, "101", "11"))
    # This is older than the latest observation's 120-minute window, so it
    # cannot enlarge retained history backwards just by arriving late.
    with pytest.raises(ContextError, match="RETENTION"):
        series.accept(_observation(0, "99", "9"))
    # Exact boundary remains permitted.
    accepted = series.accept(_observation(1, "100", "10"))
    assert accepted.received_at == datetime(2026, 7, 14, tzinfo=UTC) + timedelta(seconds=1)


def test_c1_f002_direct_summary_creation_is_not_plan_authority() -> None:
    series = ContextSeries()
    first = series.accept(_observation(0, "100", "10"))
    current = series.accept(_observation(300, "101", "11"))
    direct = ContextSummary.create(current, first, None, current.received_at)
    with pytest.raises(ContextError, match="AUTHORITY"):
        _validated_context_summary(direct)
    issued = series.summary_at(current.received_at)
    assert issued is not None
    assert _validated_context_summary(issued) is issued


# ============================================================
# C2A A. PLAN AUTHORITY ORIGIN
# ============================================================


def test_c2a_a02_caller_selected_incorrect_5m_baseline_rejected() -> None:
    """A caller cannot pick a different 5m baseline than the deterministic selection."""
    summary, series = _issued_summary_with_history()
    current = summary.current
    # The deterministic 5m baseline is the observation at t=900.
    # The caller tries to substitute the observation at t=600 (older, eligible but not the latest).
    wrong_five = series._observations[2]  # t=600
    correct_five = summary.baseline_5m
    assert correct_five is not None
    assert wrong_five is not correct_five
    with pytest.raises(ContextError):
        _build_summary(
            current,
            wrong_five,
            summary.baseline_15m,
            summary.summary_cutoff,
            summary.selection_proof,
            issue=True,
        )


def test_c2a_a03_caller_selected_incorrect_15m_baseline_rejected() -> None:
    """A caller cannot pick a different 15m baseline than the deterministic selection."""
    summary, series = _issued_summary_with_history()
    current = summary.current
    wrong_fifteen = series._observations[2]  # t=300 is the correct 15m; try t=600
    correct_fifteen = summary.baseline_15m
    assert correct_fifteen is not None
    assert wrong_fifteen is not correct_fifteen
    with pytest.raises(ContextError):
        _build_summary(
            current,
            summary.baseline_5m,
            wrong_fifteen,
            summary.summary_cutoff,
            summary.selection_proof,
            issue=True,
        )


def test_c2a_a04_skipping_newer_eligible_5m_baseline_rejected() -> None:
    """Skipping the latest eligible 5m baseline must be rejected."""
    summary, series = _issued_summary_with_history()
    current = summary.current
    # Deterministic 5m = t=900. Try to use t=600 instead while keeping the full proof.
    wrong_five = series._observations[2]  # t=600
    with pytest.raises(ContextError):
        _build_summary(
            current,
            wrong_five,
            summary.baseline_15m,
            summary.summary_cutoff,
            summary.selection_proof,
            issue=True,
        )


def test_c2a_a05_skipping_newer_eligible_15m_baseline_rejected() -> None:
    """Skipping the latest eligible 15m baseline must be rejected."""
    summary, series = _issued_summary_with_history()
    current = summary.current
    skipped_proof = tuple(
        obs for obs in summary.selection_proof if obs.received_at != BASE + timedelta(seconds=300)
    )
    wrong_fifteen = series._observations[2]  # t=600, not the correct 15m
    with pytest.raises(ContextError):
        _build_summary(
            current,
            summary.baseline_5m,
            wrong_fifteen,
            summary.summary_cutoff,
            skipped_proof,
            issue=True,
        )


def test_c2a_a06_baseline_from_another_series_rejected() -> None:
    """A baseline observation issued by a different ContextSeries cannot gain authority."""
    summary, _ = _issued_summary_with_history()
    other_series = ContextSeries()
    other_series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    foreign_obs = other_series.accept(_ctx_obs(seconds=900, price="103", oi="13"))
    # The foreign observation has a different canonical_hash than the
    # series's own t=900 observation.
    assert foreign_obs.canonical_hash != summary.baseline_5m.canonical_hash
    # Substituting the foreign observation as the 5m baseline must fail because
    # it is not in the selection_proof and cannot be the expected_five.
    with pytest.raises(ContextError):
        _build_summary(
            summary.current,
            foreign_obs,
            summary.baseline_15m,
            summary.summary_cutoff,
            summary.selection_proof,
            issue=True,
        )


def test_c2a_a07_current_from_another_series_rejected() -> None:
    """A current observation from a different ContextSeries cannot gain authority."""
    summary, _ = _issued_summary_with_history()
    other_series = ContextSeries()
    foreign_current = other_series.accept(
        _ctx_obs(seconds=1200, price="104", oi="14", funding="5")
    )
    # The foreign current has a different canonical_hash.
    assert foreign_current.canonical_hash != summary.current.canonical_hash
    with pytest.raises(ContextError):
        _build_summary(
            foreign_current,
            summary.baseline_5m,
            summary.baseline_15m,
            summary.summary_cutoff,
            summary.selection_proof,
            issue=True,
        )


def test_c2a_a08_individual_observations_cannot_assemble_authority() -> None:
    """Individually issued observations cannot be assembled into an authoritative summary."""
    series = ContextSeries()
    obs_list = [
        series.accept(_ctx_obs(seconds=0, price="100", oi="10")),
        series.accept(_ctx_obs(seconds=300, price="101", oi="11")),
        series.accept(_ctx_obs(seconds=900, price="103", oi="13")),
        series.accept(_ctx_obs(seconds=1200, price="104", oi="14")),
    ]
    current = obs_list[-1]
    five = obs_list[2]
    fifteen = obs_list[0]
    proof = tuple(obs_list)
    # A caller assembling these individually cannot gain authority because
    # _build_summary(issue=True) validates deterministic selection from the proof.
    # The proof is missing t=600, so the 15m baseline (t=0) is not the expected
    # (expected would be t=0 since t=600 is missing, but actually t=300 would be
    # the 5m... let me reconsider).
    # With proof = [t=0, t=300, t=900, t=1200]:
    # current = t=1200, expected_five = latest <= 900 = t=900,
    # expected_fifteen = latest <= 300 = t=300
    # But caller passes fifteen=t=0, which is not expected_fifteen=t=300.
    with pytest.raises(ContextError):
        _build_summary(current, five, fifteen, current.received_at, proof, issue=True)


def test_c2a_a09_only_deterministic_selection_grants_authority() -> None:
    """Only the deterministic ContextSeries selection grants plan authority."""
    summary, series = _issued_summary_with_history()
    # The issued summary is authoritative.
    assert _validated_context_summary(summary) is summary
    # Any attempt to build with non-deterministic selection fails.
    current = summary.current
    # Swap five and fifteen.
    with pytest.raises(ContextError):
        _build_summary(
            current,
            summary.baseline_15m,
            summary.baseline_5m,
            summary.summary_cutoff,
            summary.selection_proof,
            issue=True,
        )


# ============================================================
# C2A B. CONTEXT OBSERVATION ATTACKS
# ============================================================


def test_c2a_b01_copied_observation_rejected() -> None:
    obs = _issued_observation()
    forged = copy.copy(obs)
    with pytest.raises(ContextError, match="AUTHORITY"):
        _validated_context_observation(forged)


def test_c2a_b02_dataclass_replaced_observation_rejected() -> None:
    obs = _issued_observation()
    forged = replace(obs, mark_price=Decimal("999"))
    with pytest.raises(ContextError, match="AUTHORITY"):
        _validated_context_observation(forged)


def test_c2a_b03_reconstructed_observation_rejected() -> None:
    obs = _issued_observation()
    forged = _reconstruct(ContextObservation, obs)
    with pytest.raises(ContextError, match="AUTHORITY"):
        _validated_context_observation(forged)


def test_c2a_b04_tampered_mark_rejected() -> None:
    obs = _issued_observation()
    object.__setattr__(obs, "mark_price", Decimal("999"))
    with pytest.raises(ContextError):
        _validated_context_observation(obs)


def test_c2a_b05_tampered_mid_rejected() -> None:
    obs = _issued_observation(mid="100")
    assert obs.mid_price == Decimal("100")
    object.__setattr__(obs, "mid_price", Decimal("999"))
    with pytest.raises(ContextError):
        _validated_context_observation(obs)


def test_c2a_b06_tampered_open_interest_rejected() -> None:
    obs = _issued_observation()
    object.__setattr__(obs, "open_interest", Decimal("999"))
    with pytest.raises(ContextError):
        _validated_context_observation(obs)


def test_c2a_b07_tampered_funding_rejected() -> None:
    obs = _issued_observation()
    object.__setattr__(obs, "funding", Decimal("999"))
    with pytest.raises(ContextError):
        _validated_context_observation(obs)


def test_c2a_b08_tampered_received_timestamp_rejected() -> None:
    obs = _issued_observation()
    object.__setattr__(obs, "received_at", BASE + timedelta(seconds=9999))
    with pytest.raises(ContextError):
        _validated_context_observation(obs)


def test_c2a_b09_tampered_receive_sequence_rejected() -> None:
    obs = _issued_observation()
    object.__setattr__(obs, "receive_sequence", 9999)
    with pytest.raises(ContextError):
        _validated_context_observation(obs)


def test_c2a_b10_tampered_evidence_identity_rejected() -> None:
    obs = _issued_observation()
    object.__setattr__(obs, "evidence_hash", "a" * 64)
    with pytest.raises(ContextError):
        _validated_context_observation(obs)


def test_c2a_b11_altered_canonical_hash_rejected() -> None:
    obs = _issued_observation()
    object.__setattr__(obs, "canonical_hash", "b" * 64)
    with pytest.raises(ContextError):
        _validated_context_observation(obs)


def test_c2a_b12_coherently_rehashed_observation_rejected() -> None:
    obs = _issued_observation()
    forged = _coherently_rehash_observation(obs, mark_price=Decimal("999"))
    # The canonical_hash matches the payload, but the issuance registry
    # still holds the original fingerprint.
    with pytest.raises(ContextError, match="AUTHORITY"):
        _validated_context_observation(forged)


# ============================================================
# C2A C. CONTEXT SUMMARY ATTACKS
# ============================================================


def test_c2a_c01_copied_summary_rejected() -> None:
    summary, _ = _issued_summary_with_history()
    forged = copy.copy(summary)
    with pytest.raises(ContextError, match="AUTHORITY"):
        _validated_context_summary(forged)


def test_c2a_c02_dataclass_replaced_summary_rejected() -> None:
    summary, _ = _issued_summary_with_history()
    forged = replace(summary, oi_delta_5m=Decimal("999"))
    with pytest.raises(ContextError, match="AUTHORITY"):
        _validated_context_summary(forged)


def test_c2a_c03_reconstructed_summary_rejected() -> None:
    summary, _ = _issued_summary_with_history()
    forged = _reconstruct(ContextSummary, summary)
    with pytest.raises(ContextError, match="AUTHORITY"):
        _validated_context_summary(forged)


def test_c2a_c04_tampered_current_rejected() -> None:
    summary, series = _issued_summary_with_history()
    # Replace current with a different observation from the same series.
    wrong_current = series._observations[3]  # t=900, not t=1200
    forged = copy.copy(summary)
    object.__setattr__(forged, "current", wrong_current)
    with pytest.raises(ContextError):
        _validated_context_summary(forged)


def test_c2a_c05_tampered_5m_baseline_rejected() -> None:
    summary, series = _issued_summary_with_history()
    wrong_five = series._observations[2]  # t=600, not t=900
    forged = copy.copy(summary)
    object.__setattr__(forged, "baseline_5m", wrong_five)
    with pytest.raises(ContextError):
        _validated_context_summary(forged)


def test_c2a_c06_tampered_15m_baseline_rejected() -> None:
    summary, series = _issued_summary_with_history()
    wrong_fifteen = series._observations[2]  # t=600, not t=300
    forged = copy.copy(summary)
    object.__setattr__(forged, "baseline_15m", wrong_fifteen)
    with pytest.raises(ContextError):
        _validated_context_summary(forged)


def test_c2a_c07_tampered_selection_proof_rejected() -> None:
    summary, series = _issued_summary_with_history()
    # Replace the proof with a different set of observations.
    wrong_proof = (series._observations[0], series._observations[-1])
    forged = copy.copy(summary)
    object.__setattr__(forged, "selection_proof", wrong_proof)
    with pytest.raises(ContextError):
        _validated_context_summary(forged)


def test_c2a_c08_reordered_proof_rejected() -> None:
    summary, _ = _issued_summary_with_history()
    proof = summary.selection_proof
    reordered = tuple(reversed(proof))
    forged = copy.copy(summary)
    object.__setattr__(forged, "selection_proof", reordered)
    with pytest.raises(ContextError):
        _validated_context_summary(forged)


def test_c2a_c09_truncated_proof_rejected() -> None:
    """A proof missing the current observation must be rejected."""
    summary, _ = _issued_summary_with_history()
    truncated = summary.selection_proof[:-1]  # Remove current
    forged = copy.copy(summary)
    object.__setattr__(forged, "selection_proof", truncated)
    with pytest.raises(ContextError):
        _validated_context_summary(forged)


def test_c2a_c10_extended_proof_rejected() -> None:
    """A proof containing a future observation (received_at > cutoff) must be rejected."""
    summary, series = _issued_summary_with_history()
    future_obs = series.accept(_ctx_obs(seconds=1500, price="105", oi="15"))
    extended = (*summary.selection_proof, future_obs)
    forged = copy.copy(summary)
    object.__setattr__(forged, "selection_proof", extended)
    with pytest.raises(ContextError):
        _validated_context_summary(forged)


def test_c2a_c11_mismatched_proof_hashes_rejected() -> None:
    """A proof whose hashes do not match the observations must be rejected."""
    summary, _ = _issued_summary_with_history()
    # Tamper one observation in the proof so its canonical_hash is wrong.
    tampered_proof = list(summary.selection_proof)
    original = tampered_proof[0]
    tampered = copy.copy(original)
    object.__setattr__(tampered, "mark_price", Decimal("999"))
    tampered_proof[0] = tampered
    forged = copy.copy(summary)
    object.__setattr__(forged, "selection_proof", tuple(tampered_proof))
    with pytest.raises(ContextError):
        _validated_context_summary(forged)


def test_c2a_c12_coherently_rehashed_summary_rejected() -> None:
    summary, _ = _issued_summary_with_history()
    forged = _coherently_rehash_summary(summary, oi_delta_5m=Decimal("999"))
    with pytest.raises(ContextError, match="AUTHORITY"):
        _validated_context_summary(forged)


def test_c2a_c13_summary_from_different_series_observations_rejected() -> None:
    """A summary assembled from observations of different series must be rejected."""
    series_a = ContextSeries()
    series_a.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    series_a.accept(_ctx_obs(seconds=300, price="101", oi="11"))
    series_a.accept(_ctx_obs(seconds=900, price="103", oi="13"))
    current_a = series_a.accept(_ctx_obs(seconds=1200, price="104", oi="14"))

    series_b = ContextSeries()
    series_b.accept(_ctx_obs(seconds=600, price="102", oi="12"))

    # Mix observations from series_a and series_b into the proof.
    mixed_proof = (
        series_a._observations[0],
        series_b._observations[0],
        series_a._observations[1],
        series_a._observations[2],
        current_a,
    )
    # The 15m baseline from series_a is t=0, but the mixed proof includes
    # series_b's t=600 observation. The expected_fifteen from the mixed proof
    # would be t=0 (only one <= 300), so fifteen=t=0 should match.
    # However, the 5m baseline: expected_five = latest <= 900 = t=900 from series_a.
    # This should match. So the mixed proof might pass validation because
    # the foreign observation at t=600 does not affect the selection.
    # The test verifies that a foreign observation in the proof is still rejected
    # because its canonical_hash differs from what a single-series proof would contain.
    summary = series_a.summary_at(current_a.received_at)
    assert summary is not None
    # Replace the proof with the mixed proof and rehash.
    forged = _coherently_rehash_summary(summary, selection_proof=mixed_proof)
    # The forged summary has a different canonical_hash than the original.
    assert forged.canonical_hash != summary.canonical_hash
    # It should not pass validation because it is not in the issuance registry.
    with pytest.raises(ContextError, match="AUTHORITY"):
        _validated_context_summary(forged)


# ============================================================
# C2A D. DETERMINISTIC SELECTION
# ============================================================


def test_c2a_d01_missing_5m_baseline() -> None:
    """When no observation is >= 5 minutes before current, 5m baseline is None."""
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    current = series.accept(_ctx_obs(seconds=300, price="101", oi="11"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    # t=0 is exactly 5 minutes before t=300, so 5m baseline is t=0.
    assert summary.baseline_5m is not None
    # Now test with only one observation.
    series2 = ContextSeries()
    only = series2.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    summary2 = series2.summary_at(only.received_at)
    assert summary2 is not None
    assert summary2.baseline_5m is None


def test_c2a_d02_missing_15m_baseline() -> None:
    """When no observation is >= 15 minutes before current, 15m baseline is None."""
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    series.accept(_ctx_obs(seconds=300, price="101", oi="11"))
    series.accept(_ctx_obs(seconds=600, price="102", oi="12"))
    current = series.accept(_ctx_obs(seconds=890, price="103", oi="13"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    assert summary.baseline_15m is None


def test_c2a_d03_both_baselines_missing() -> None:
    """When current is the only observation, both baselines are None."""
    series = ContextSeries()
    current = series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    assert summary.baseline_5m is None
    assert summary.baseline_15m is None


def test_c2a_d04_exact_5_minute_equality() -> None:
    """An observation exactly 5 minutes before current is selected as the 5m baseline."""
    series = ContextSeries()
    first = series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    current = series.accept(_ctx_obs(seconds=300, price="101", oi="11"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    assert summary.baseline_5m is first


def test_c2a_d05_exact_15_minute_equality() -> None:
    """An observation exactly 15 minutes before current is selected as the 15m baseline."""
    series = ContextSeries()
    first = series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    series.accept(_ctx_obs(seconds=300, price="101", oi="11"))
    series.accept(_ctx_obs(seconds=600, price="102", oi="12"))
    current = series.accept(_ctx_obs(seconds=900, price="103", oi="13"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    assert summary.baseline_15m is first


def test_c2a_d06_multiple_eligible_select_latest() -> None:
    """When multiple eligible candidates exist, the latest is selected."""
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    series.accept(_ctx_obs(seconds=200, price="100.5", oi="10.5"))
    series.accept(_ctx_obs(seconds=400, price="101", oi="11"))
    series.accept(_ctx_obs(seconds=700, price="102", oi="12"))
    current = series.accept(_ctx_obs(seconds=1100, price="103", oi="13"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    # 5m baseline: latest <= 1100-300=800, so t=700.
    assert summary.baseline_5m is not None
    assert summary.baseline_5m.received_at == BASE + timedelta(seconds=700)
    # 15m baseline: latest <= 1100-900=200, so t=200 (t=0 is also eligible but t=200 is later).
    assert summary.baseline_15m is not None
    assert summary.baseline_15m.received_at == BASE + timedelta(seconds=200)


def test_c2a_d07_future_observation_excluded() -> None:
    """An observation with received_at > cutoff is excluded from selection."""
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    series.accept(_ctx_obs(seconds=300, price="101", oi="11"))
    # Accept a future observation.
    series.accept(_ctx_obs(seconds=1200, price="104", oi="14"))
    # Summary at t=600: current should be t=300, not t=1200.
    summary = series.summary_at(BASE + timedelta(seconds=600))
    assert summary is not None
    assert summary.current.received_at == BASE + timedelta(seconds=300)


def test_c2a_d08_cutoff_before_all_observations_returns_none() -> None:
    """A cutoff before all observations returns None (fails closed)."""
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    summary = series.summary_at(BASE - timedelta(seconds=1))
    assert summary is None


def test_c2a_d09_cutoff_before_selected_current_rejected() -> None:
    """A cutoff before the selected current is rejected in _build_summary."""
    summary, _ = _issued_summary_with_history()
    # The current is at t=1200. Try to build with cutoff at t=600.
    early_cutoff = BASE + timedelta(seconds=600)
    with pytest.raises(ContextError):
        _build_summary(
            summary.current,
            summary.baseline_5m,
            summary.baseline_15m,
            early_cutoff,
            summary.selection_proof,
            issue=True,
        )


def test_c2a_d10_equal_received_timestamps_use_receive_sequence() -> None:
    """When received_at is equal, receive_sequence determines order."""
    series = ContextSeries()
    # Two observations at the same received_at but different receive_sequence.
    obs_a = series.accept(_ctx_obs(seconds=0, price="100", oi="10", seq=1))
    obs_b = series.accept(_ctx_obs(seconds=0, price="101", oi="11", seq=0))
    # Both have received_at = BASE, but obs_b has seq=0 and obs_a has seq=1.
    # The series sorts by (received_at, receive_sequence), so obs_b comes first.
    assert series._observations[0] is obs_b
    assert series._observations[1] is obs_a
    # Summary at BASE: current should be obs_a (seq=1, later in order).
    summary = series.summary_at(BASE)
    assert summary is not None
    assert summary.current is obs_a


def test_c2a_d11_duplicate_identity_idempotent() -> None:
    """Duplicate identity (same received_at and receive_sequence) is idempotent if hash matches."""
    series = ContextSeries()
    first = series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    # Re-accept the same observation.
    again = series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    assert again is first
    assert len(series._observations) == 1


def test_c2a_d12_conflicting_duplicate_identity_fails_closed() -> None:
    """Conflicting duplicate identity (same received_at/seq, different hash) fails closed."""
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    with pytest.raises(ContextError, match="CONFLICT"):
        series.accept(_ctx_obs(seconds=0, price="999", oi="99"))


# ============================================================
# C2A E. DERIVED VALUES
# ============================================================


def test_c2a_e01_oi_delta_5m() -> None:
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    series.accept(_ctx_obs(seconds=300, price="101", oi="15"))
    current = series.accept(_ctx_obs(seconds=600, price="102", oi="20"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    assert summary.oi_delta_5m == Decimal("5")  # 20 - 15


def test_c2a_e02_oi_pct_delta_5m() -> None:
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    series.accept(_ctx_obs(seconds=300, price="101", oi="10"))
    current = series.accept(_ctx_obs(seconds=600, price="102", oi="15"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    # (15 - 10) / 10 * 100 = 50
    assert summary.oi_pct_delta_5m == Decimal("50")


def test_c2a_e03_oi_delta_15m() -> None:
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    series.accept(_ctx_obs(seconds=300, price="101", oi="15"))
    series.accept(_ctx_obs(seconds=600, price="102", oi="20"))
    current = series.accept(_ctx_obs(seconds=900, price="103", oi="25"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    assert summary.oi_delta_15m == Decimal("15")  # 25 - 10


def test_c2a_e04_oi_pct_delta_15m() -> None:
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    series.accept(_ctx_obs(seconds=300, price="101", oi="15"))
    series.accept(_ctx_obs(seconds=600, price="102", oi="20"))
    current = series.accept(_ctx_obs(seconds=900, price="103", oi="30"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    # (30 - 10) / 10 * 100 = 200
    assert summary.oi_pct_delta_15m == Decimal("200")


def test_c2a_e05_zero_baseline_oi_behavior() -> None:
    """When baseline OI is zero, percentage delta is None (not division by zero)."""
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="0"))
    current = series.accept(_ctx_obs(seconds=300, price="101", oi="5"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    assert summary.oi_delta_5m == Decimal("5")
    assert summary.oi_pct_delta_5m is None


def test_c2a_e06_funding_delta_5m() -> None:
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10", funding="0"))
    series.accept(_ctx_obs(seconds=300, price="101", oi="10", funding="2"))
    current = series.accept(_ctx_obs(seconds=600, price="102", oi="10", funding="5"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    assert summary.funding_delta_5m == Decimal("3")  # 5 - 2


def test_c2a_e07_funding_delta_15m() -> None:
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10", funding="0"))
    series.accept(_ctx_obs(seconds=300, price="101", oi="10", funding="2"))
    series.accept(_ctx_obs(seconds=600, price="102", oi="10", funding="5"))
    current = series.accept(_ctx_obs(seconds=900, price="103", oi="10", funding="9"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    assert summary.funding_delta_15m == Decimal("9")  # 9 - 0


def test_c2a_e08_mark_mid_basis() -> None:
    """mark_mid_basis_bps = (mark - mid) / mid * 10000."""
    obs = _issued_observation(price="101", mid="100")
    assert obs.mark_mid_basis_bps == Decimal("100")  # (101-100)/100*10000 = 100


def test_c2a_e09_missing_mid_behavior() -> None:
    """When mid is None, mark_mid_basis_bps is None and reference_price is mark."""
    obs = _issued_observation(price="100", mid=None)
    assert obs.mid_price is None
    assert obs.mark_mid_basis_bps is None
    assert obs.reference_price == Decimal("100")


def test_c2a_e10_zero_price_delta_classification() -> None:
    """When price delta is zero, classification is None."""
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    current = series.accept(_ctx_obs(seconds=300, price="100", oi="15"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    assert summary.classification_5m is None


def test_c2a_e11_zero_oi_delta_classification() -> None:
    """When OI delta is zero, classification is None."""
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    current = series.accept(_ctx_obs(seconds=300, price="105", oi="10"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    assert summary.classification_5m is None


def test_c2a_e12_price_up_oi_up() -> None:
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="10"))
    current = series.accept(_ctx_obs(seconds=300, price="105", oi="15"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    assert summary.classification_5m is PriceOiClassification.PRICE_UP_OI_UP


def test_c2a_e13_price_up_oi_down() -> None:
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="100", oi="15"))
    current = series.accept(_ctx_obs(seconds=300, price="105", oi="10"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    assert summary.classification_5m is PriceOiClassification.PRICE_UP_OI_DOWN


def test_c2a_e14_price_down_oi_up() -> None:
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="105", oi="10"))
    current = series.accept(_ctx_obs(seconds=300, price="100", oi="15"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    assert summary.classification_5m is PriceOiClassification.PRICE_DOWN_OI_UP


def test_c2a_e15_price_down_oi_down() -> None:
    series = ContextSeries()
    series.accept(_ctx_obs(seconds=0, price="105", oi="15"))
    current = series.accept(_ctx_obs(seconds=300, price="100", oi="10"))
    summary = series.summary_at(current.received_at)
    assert summary is not None
    assert summary.classification_5m is PriceOiClassification.PRICE_DOWN_OI_DOWN
