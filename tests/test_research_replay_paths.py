"""Outcome labels never enter causal decisions; uncertainty is conservative."""

from decimal import Decimal

import pytest
from test_research_replay_contracts import H, changed, cost, opportunity, raw

from trader_assist_v0.research_replay.contracts import Attempt, CashFlow, DecisionSnapshot, Fill
from trader_assist_v0.research_replay.paths import measure_path, net_cash, thesis_state


def decision(op=None, **updates):
    op = op or opportunity()
    args = dict(
        version="B_DECISION_V1",
        opportunity_hash=op.record_hash,
        policy_hash=H,
        decision="PASS",
        reasons=("R0_REJECTED",),
        decision_ns=100,
        prefix_hashes=op.prefix_hashes,
        feature_hashes=(),
        cost_hash=cost().record_hash,
        horizon_end=200,
    )
    args.update(updates)
    return DecisionSnapshot.create(**args)


def test_suppressed_path_snapshot_firsttouch_trigger_fill_and_missing():
    op, snapshot = opportunity(), decision()
    before_hash = snapshot.record_hash
    rows = (
        raw(110, values={"bid": "97", "ask": "99"}),
        raw(120, values={"bid": "101", "ask": "103"}),
        raw(150, values={"bid": "106", "ask": "108"}),
    )
    path = measure_path(snapshot, op, rows, as_of=200)
    assert path.status == "RECONSTRUCTABLE" and path.primary == "TARGET_FIRST"
    assert path.market_mfe == 7 and path.market_mae == -2
    assert path.exec_mfe == 6 and path.exec_mae == -3
    assert path.first_adverse_ns == 110 and path.recovery_ns == 120
    fill = Fill(
        ts=120, price=Decimal(103), size=Decimal(1), direction="BUY", fee=Decimal(0), source_hash=H
    )
    assert measure_path(snapshot, op, rows, as_of=200, fill=fill).basis == "FILL"
    assert snapshot.record_hash == before_hash and snapshot.decision == "PASS"
    empty = measure_path(snapshot, op, (), as_of=200)
    assert empty.status == "NOT_RECONSTRUCTABLE" and empty.market_mfe is None
    assert measure_path(snapshot, op, rows, as_of=130).censored
    external = raw(150, provider="OKX", values={"bid": "200", "ask": "202"})
    assert measure_path(snapshot, op, (*rows, external), as_of=200).market_mfe == 7
    assert (
        measure_path(snapshot, op, (changed(rows[0], quality=("GAPPED",)),), as_of=200).market_mae
        is None
    )


def test_bar_and_equal_time_collision_never_optimistic():
    bar = raw(150, kind="BAR", values={"start_ns": "100", "high": "106", "low": "94"})
    path = measure_path(decision(), opportunity(), (bar,), as_of=200)
    assert path.same_bar_ambiguous and path.primary == "STOP_FIRST" and path.bounds_only
    partial = changed(bar, values=(("start_ns", "90"), ("high", "106"), ("low", "94")))
    assert measure_path(decision(), opportunity(), (partial,), as_of=200).market_mfe is None
    low = raw(150, values={"bid": "94", "ask": "96"})
    high = raw(150, values={"bid": "106", "ask": "108"}, ordinal=151)
    assert measure_path(decision(), opportunity(), (high, low), as_of=200).primary == "STOP_FIRST"


def test_funding_credits_and_debits_use_native_exposure_at_settlement():
    from trader_assist_v0.research_replay.paths import funding_settlement

    fill = Fill(
        ts=101, price=Decimal(100), size=Decimal(2), direction="BUY", fee=Decimal(0), source_hash=H
    )
    rate = raw(
        110,
        kind="CONTEXT",
        values={
            "field": "FUNDING",
            "value": "-0.01",
            "unit": "FRACTION_PER_SETTLEMENT",
            "settlement_ns": "120",
        },
    )
    mark = raw(119, values={"bid": "99", "ask": "101"})
    flow = funding_settlement((fill,), rate, mark, as_of=120, profile_hash=H)
    assert flow.amount == 2 and flow.input_hashes == (rate.record_hash, mark.record_hash)
    closed = Fill(
        ts=115, price=Decimal(100), size=Decimal(2), direction="SELL", fee=Decimal(0), source_hash=H
    )
    assert funding_settlement((fill, closed), rate, mark, as_of=120, profile_hash=H).amount == 0
    with pytest.raises(ValueError, match="matured"):
        funding_settlement((fill,), rate, mark, as_of=119, profile_hash=H)
    with pytest.raises(ValueError, match="external funding"):
        funding_settlement(
            (fill,),
            changed(rate, evidence=raw(provider="OKX").evidence),
            mark,
            as_of=120,
            profile_hash=H,
        )


def test_attempt_failure_not_thesis_invalidation_and_signed_costs():
    fill = Fill(
        ts=101, price=Decimal(101), size=Decimal(1), direction="BUY", fee=Decimal(1), source_hash=H
    )
    exit_fill = Fill(
        ts=110, price=Decimal(99), size=Decimal(1), direction="SELL", fee=Decimal(1), source_hash=H
    )
    attempt = Attempt.create(
        version="B_ATTEMPT_V1",
        thesis_id="T",
        policy_hash=H,
        index=1,
        trigger_ns=100,
        fill=fill,
        exit_fill=exit_fill,
        state="SCRATCHED",
        fresh_condition_hash=H,
        reason="FAST_LOSS",
    )
    assert (
        thesis_state((attempt,), thesis_id="T", at=111, invalidation_ns=None, max_attempts=2)
        == "WAITING_FOR_REENTRY"
    )
    assert (
        thesis_state((attempt,), thesis_id="T", at=120, invalidation_ns=120, max_attempts=2)
        == "THESIS_INVALIDATED"
    )
    with pytest.raises(ValueError, match="invalidation"):
        thesis_state(
            (
                attempt,
                changed(
                    attempt, index=2, trigger_ns=121, fill=None, exit_fill=None, state="NONFILL"
                ),
            ),
            thesis_id="T",
            at=122,
            invalidation_ns=120,
            max_attempts=2,
        )
    credit = CashFlow(ts=105, amount=Decimal(3), source_hash=H, kind="FUNDING")
    assert (
        net_cash((fill, exit_fill), (credit,), funding_complete=True, funding_applicable=True) == -1
    )
    assert net_cash((fill, exit_fill), (), funding_complete=False, funding_applicable=True) is None
    assert net_cash((fill, exit_fill), (), funding_complete=False, funding_applicable=False) == -4
