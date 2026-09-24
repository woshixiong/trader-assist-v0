import sqlite3
from dataclasses import replace
from decimal import Decimal

import pytest

from trader_assist_v0.multi_asset_shadow.l1_approval import (
    ApprovalState,
    AuthorityMode,
    EvidenceStream,
    HumanApprovalLedger,
    L1ContractError,
    PackageLeg,
    StrategyOrderPackage,
)


def _package(*, expires: int = 200) -> StrategyOrderPackage:
    return StrategyOrderPackage.create(
        parent_strategy_order_id="strategy-order-1",
        strategy_version="three-setup-1",
        parameter_version="params-1",
        created_server_ms=100,
        expires_server_ms=expires,
        activation_opportunity_id="activation-opportunity-1",
        authority_mode=AuthorityMode.ZERO_WRITE,
        legs=(PackageLeg("btc", "LONG", Decimal("0.1"), Decimal("20"), Decimal("5")),),
    )


def test_baseline_is_unconditional_and_post_activation_requires_a_human_action() -> None:
    package = _package()
    ledger = HumanApprovalLedger(sqlite3.connect(":memory:"))
    ledger.display(package)
    baseline = ledger.record_baseline(package, server_ms=101)
    assert baseline.stream is EvidenceStream.STRATEGY_BASELINE_SHADOW
    assert baseline.submission_status == "NOT_SUBMITTED"
    future = ledger.record_future_live_boundary(package, server_ms=102)
    assert future.stream is EvidenceStream.FUTURE_LIVE_EXECUTION
    assert future.submission_status == "NOT_SUBMITTED"
    assert (
        ledger.activate(
            package,
            action_key="activate",
            server_ms=110,
            activation_opportunity_id="activation-opportunity-1",
        )
        is ApprovalState.AWAITING_HUMAN_APPROVAL
    )
    assert (
        ledger.approve_post_activation(package, action_key="approve", server_ms=111)
        is ApprovalState.ACTIVATED
    )


def test_preauthorized_activation_is_single_use_idempotent_and_zero_write() -> None:
    package = _package()
    ledger = HumanApprovalLedger(sqlite3.connect(":memory:"))
    ledger.display(package)
    assert ledger.arm(package, action_key="arm", server_ms=105) is ApprovalState.PREAUTHORIZED_ARMED
    assert (
        ledger.activate(
            package,
            action_key="activate",
            server_ms=110,
            activation_opportunity_id="activation-opportunity-1",
        )
        is ApprovalState.ACTIVATED
    )
    assert (
        ledger.activate(
            package,
            action_key="activate",
            server_ms=110,
            activation_opportunity_id="activation-opportunity-1",
        )
        is ApprovalState.ACTIVATED
    )
    with pytest.raises(L1ContractError, match="requires an open activation"):
        ledger.approve_post_activation(package, action_key="second-click", server_ms=111)
    row = ledger._connection.execute(
        "SELECT submission_status FROM l1_workflow_evidence"
    ).fetchone()
    assert row[0] == "NOT_SUBMITTED"


def test_exact_displayed_hash_expiry_supersession_and_restart_gap_fail_closed(tmp_path) -> None:
    package = _package(expires=120)
    path = tmp_path / "approval.sqlite"
    ledger = HumanApprovalLedger(sqlite3.connect(path))
    ledger.display(package)
    with pytest.raises(L1ContractError, match="expired"):
        ledger.arm(package, action_key="late", server_ms=120)
    replacement = StrategyOrderPackage.create(
        parent_strategy_order_id="strategy-order-1",
        strategy_version="three-setup-2",
        parameter_version="params-2",
        created_server_ms=110,
        expires_server_ms=220,
        activation_opportunity_id="activation-opportunity-2",
        legs=(PackageLeg("btc", "LONG", Decimal("0.1"), Decimal("20"), Decimal("5")),),
    )
    ledger.supersede(package, replacement, server_ms=111)
    assert ledger.state(package, server_ms=112) is ApprovalState.SUPERSEDED
    ledger._connection.execute(
        "INSERT INTO l1_approval_events VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "gap",
            replacement.package_id,
            replacement.package_hash,
            "ACTIVATION_STARTED",
            None,
            115,
            "{}",
        ),
    )
    assert ledger.state(replacement, server_ms=116) is ApprovalState.AMBIGUOUS_RESTART


def test_file_backed_public_mutations_survive_close_and_reopen(tmp_path) -> None:
    path = tmp_path / "durable.sqlite"
    package = _package()
    ledger = HumanApprovalLedger(sqlite3.connect(path))
    ledger.display(package)
    ledger.record_baseline(package, server_ms=101)
    ledger.record_future_live_boundary(package, server_ms=102)
    ledger.arm(package, action_key="arm", server_ms=105)
    ledger._connection.close()

    reopened = HumanApprovalLedger(sqlite3.connect(path))
    assert reopened.state(package, server_ms=106) is ApprovalState.PREAUTHORIZED_ARMED
    assert (
        reopened._connection.execute("SELECT COUNT(*) FROM l1_workflow_evidence").fetchone()[0] == 2
    )
    assert (
        reopened.activate(
            package,
            action_key="activate",
            server_ms=110,
            activation_opportunity_id=package.activation_opportunity_id,
        )
        is ApprovalState.ACTIVATED
    )
    reopened._connection.close()

    final = HumanApprovalLedger(sqlite3.connect(path))
    assert final.state(package, server_ms=111) is ApprovalState.ACTIVATED
    assert final._connection.execute("SELECT COUNT(*) FROM l1_workflow_evidence").fetchone()[0] == 3


def test_post_activation_and_idempotency_are_durable_across_restart(tmp_path) -> None:
    path = tmp_path / "post-activation.sqlite"
    package = _package()
    ledger = HumanApprovalLedger(sqlite3.connect(path))
    ledger.display(package)
    ledger.activate(
        package,
        action_key="open",
        server_ms=110,
        activation_opportunity_id=package.activation_opportunity_id,
    )
    ledger._connection.close()

    reopened = HumanApprovalLedger(sqlite3.connect(path))
    assert reopened.state(package, server_ms=110) is ApprovalState.AWAITING_HUMAN_APPROVAL
    assert (
        reopened.approve_post_activation(package, action_key="approve", server_ms=111)
        is ApprovalState.ACTIVATED
    )
    reopened._connection.close()

    final = HumanApprovalLedger(sqlite3.connect(path))
    assert (
        final.approve_post_activation(package, action_key="approve", server_ms=111)
        is ApprovalState.ACTIVATED
    )
    with pytest.raises(L1ContractError, match="conflicts"):
        final.approve_post_activation(package, action_key="approve", server_ms=112)


def test_supersede_is_one_durable_transaction_and_rolls_back_on_failure(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "supersede.sqlite"
    old = _package()
    new = StrategyOrderPackage.create(
        parent_strategy_order_id="strategy-order-1",
        strategy_version="three-setup-2",
        parameter_version="params-2",
        created_server_ms=110,
        expires_server_ms=220,
        activation_opportunity_id="activation-opportunity-2",
        legs=(PackageLeg("btc", "LONG", Decimal("0.1"), Decimal("20"), Decimal("5")),),
    )
    ledger = HumanApprovalLedger(sqlite3.connect(path))
    ledger.display(old)
    original_event = ledger._event

    def fail_supersede(*args, **kwargs):
        if args[2] == "SUPERSEDED":
            raise L1ContractError("injected supersede failure")
        return original_event(*args, **kwargs)

    monkeypatch.setattr(ledger, "_event", fail_supersede)
    with pytest.raises(L1ContractError, match="injected"):
        ledger.supersede(old, new, server_ms=111)
    assert ledger._mutation_depth == 0
    ledger._connection.close()

    reopened = HumanApprovalLedger(sqlite3.connect(path))
    assert reopened.state(old, server_ms=112) is ApprovalState.DRAFT
    with pytest.raises(L1ContractError, match="displayed"):
        reopened.state(new, server_ms=112)
    reopened.supersede(old, new, server_ms=111)
    assert reopened._mutation_depth == 0
    reopened._connection.close()

    final = HumanApprovalLedger(sqlite3.connect(path))
    assert final.state(old, server_ms=112) is ApprovalState.SUPERSEDED
    assert final.state(new, server_ms=112) is ApprovalState.DRAFT


@pytest.mark.parametrize(
    ("prepare", "mutation"),
    [
        (
            lambda ledger, package: None,
            lambda ledger, package: ledger.display(package),
        ),
        (
            lambda ledger, package: ledger.display(package),
            lambda ledger, package: ledger.record_baseline(package, server_ms=101),
        ),
        (
            lambda ledger, package: ledger.display(package),
            lambda ledger, package: ledger.record_future_live_boundary(package, server_ms=101),
        ),
        (
            lambda ledger, package: ledger.display(package),
            lambda ledger, package: ledger.arm(package, action_key="arm", server_ms=101),
        ),
        (
            lambda ledger, package: ledger.display(package),
            lambda ledger, package: ledger.activate(
                package,
                action_key="activate",
                server_ms=101,
                activation_opportunity_id=package.activation_opportunity_id,
            ),
        ),
        (
            lambda ledger, package: (
                ledger.display(package),
                ledger.activate(
                    package,
                    action_key="open",
                    server_ms=101,
                    activation_opportunity_id=package.activation_opportunity_id,
                ),
            ),
            lambda ledger, package: ledger.approve_post_activation(
                package, action_key="approve", server_ms=102
            ),
        ),
        (
            lambda ledger, package: ledger.display(package),
            lambda ledger, package: ledger.supersede(
                package,
                StrategyOrderPackage.create(
                    parent_strategy_order_id="strategy-order-1",
                    strategy_version="three-setup-2",
                    parameter_version="params-2",
                    created_server_ms=110,
                    expires_server_ms=220,
                    activation_opportunity_id="activation-opportunity-2",
                    legs=(
                        PackageLeg("btc", "LONG", Decimal("0.1"), Decimal("20"), Decimal("5")),
                    ),
                ),
                server_ms=111,
            ),
        ),
    ],
    ids=(
        "display",
        "record-baseline",
        "record-future-live-boundary",
        "arm",
        "activate",
        "approve-post-activation",
        "supersede",
    ),
)
@pytest.mark.parametrize("finish", ("commit", "rollback"))
def test_public_mutations_reject_caller_owned_transactions_before_writing(
    prepare, mutation, finish
) -> None:
    """Ledger writes never borrow, commit, or roll back a caller transaction."""
    connection = sqlite3.connect(":memory:")
    ledger = HumanApprovalLedger(connection)
    package = _package()
    prepare(ledger, package)
    before = tuple(
        connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("l1_packages", "l1_approval_events", "l1_workflow_evidence")
    )
    connection.execute("CREATE TABLE caller_sentinel (value TEXT NOT NULL)")
    connection.execute("BEGIN")
    connection.execute("INSERT INTO caller_sentinel VALUES ('caller-owned')")

    with pytest.raises(L1ContractError, match="caller-owned SQLite transaction"):
        mutation(ledger, package)

    assert connection.in_transaction
    assert connection.execute("SELECT value FROM caller_sentinel").fetchone()[0] == "caller-owned"
    after = tuple(
        connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("l1_packages", "l1_approval_events", "l1_workflow_evidence")
    )
    assert after == before
    assert ledger._mutation_depth == 0
    getattr(connection, finish)()
    assert not connection.in_transaction


def test_construction_rejects_a_caller_owned_transaction_without_committing_it() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE caller_sentinel (value TEXT NOT NULL)")
    connection.execute("BEGIN")
    connection.execute("INSERT INTO caller_sentinel VALUES ('caller-owned')")

    with pytest.raises(L1ContractError, match="caller-owned SQLite transaction"):
        HumanApprovalLedger(connection)

    assert connection.in_transaction
    assert connection.execute("SELECT value FROM caller_sentinel").fetchone()[0] == "caller-owned"
    connection.rollback()
    assert connection.execute("SELECT COUNT(*) FROM caller_sentinel").fetchone()[0] == 0


def test_forged_package_payload_cannot_reuse_a_displayed_id_or_hash() -> None:
    package = _package()
    ledger = HumanApprovalLedger(sqlite3.connect(":memory:"))
    ledger.display(package)
    for forged in (
        replace(package, expires_server_ms=999),
        replace(package, strategy_version="forged"),
        replace(
            package,
            legs=(PackageLeg("btc", "LONG", Decimal("0.2"), Decimal("20"), Decimal("5")),),
        ),
    ):
        with pytest.raises(L1ContractError, match="id/hash"):
            ledger.record_baseline(forged, server_ms=101)
    assert ledger.record_baseline(package, server_ms=101).submission_status == "NOT_SUBMITTED"


def test_preauthorization_binds_one_exact_activation_opportunity() -> None:
    package = _package()
    ledger = HumanApprovalLedger(sqlite3.connect(":memory:"))
    ledger.display(package)
    ledger.arm(package, action_key="arm", server_ms=105)
    for opportunity in (None, "wrong-opportunity"):
        with pytest.raises(L1ContractError, match="exact activation"):
            ledger.activate(
                package,
                action_key="activate-" + str(opportunity),
                server_ms=110,
                activation_opportunity_id=opportunity,
            )
    assert (
        ledger.activate(
            package,
            action_key="activate-exact",
            server_ms=110,
            activation_opportunity_id=package.activation_opportunity_id,
        )
        is ApprovalState.ACTIVATED
    )


def test_post_activation_retry_is_idempotent_but_conflicting_key_reuse_fails_closed() -> None:
    package = _package()
    ledger = HumanApprovalLedger(sqlite3.connect(":memory:"))
    ledger.display(package)
    ledger.activate(
        package,
        action_key="open",
        server_ms=110,
        activation_opportunity_id="activation-opportunity-1",
    )
    assert (
        ledger.approve_post_activation(package, action_key="approve", server_ms=111)
        is ApprovalState.ACTIVATED
    )
    assert (
        ledger.approve_post_activation(package, action_key="approve", server_ms=111)
        is ApprovalState.ACTIVATED
    )
    with pytest.raises(L1ContractError, match="conflicts"):
        ledger.approve_post_activation(package, action_key="approve", server_ms=112)
