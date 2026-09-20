from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from scripts import nautilus_vnext_g4_representative_acquisition as acquisition

HEAD = "1" * 40
TREE = "2" * 40


def _mapper(coin: str) -> str:
    return f"{coin}-USD-PERP.HYPERLIQUID"


def _source(
    count: int = 22,
    *,
    volumes: dict[str, str] | None = None,
) -> dict[str, object]:
    universe: list[dict[str, object]] = []
    contexts: list[dict[str, object]] = []
    for index in range(count):
        coin = f"COIN{index:02d}"
        universe.append(
            {
                "name": coin,
                "szDecimals": 3,
                "maxLeverage": 20,
                "onlyIsolated": False,
            }
        )
        contexts.append(
            {
                "dayNtlVlm": (volumes or {}).get(coin, str(1_000 - index)),
                "midPx": str(100 + index),
                "markPx": str(100 + index),
            }
        )
    return {
        "schema_version": acquisition.SELECTION_SCHEMA,
        "venue": acquisition.VENUE,
        "dex": acquisition.DEX,
        "product_class": acquisition.PRODUCT_CLASS,
        "request": {"type": "metaAndAssetCtxs"},
        "observed_at_ns": 1_000_000,
        "response": [{"universe": universe}, contexts],
    }


def _markets() -> tuple[acquisition.FrozenMarket, ...]:
    return acquisition.freeze_market_selection(_source(), instrument_mapper=_mapper)


def _complete_probe(markets: tuple[acquisition.FrozenMarket, ...]) -> dict[str, object]:
    streams = sorted(
        f"{market.market_id}:{kind}"
        for market in markets
        for kind in ("BBO", "TRADE", "BAR")
    )
    return {
        "status": "PASS",
        "bounded_run_seconds": acquisition.RUN_SECONDS,
        "observation": {
            "expected_streams": streams,
            "observed_streams": streams,
            "missing_streams": [],
            "quote_observed": True,
            "trade_observed": True,
            "bar_subscription_registered": True,
            "finalized_bar_callback_observed": True,
            "finalized_bar_evidence_persisted": True,
            "provider_observation_pass": True,
        },
    }


def test_selection_uses_exactly_one_official_main_meta_asset_context_snapshot() -> None:
    class Client:
        def __init__(self) -> None:
            self.dexes: list[str] = []

        def metadata_and_context(self, dex: str) -> object:
            self.dexes.append(dex)
            return [{"universe": []}, []]

    client = Client()
    source = acquisition.fetch_selection_source(client, clock_ns=lambda: 123)
    assert client.dexes == [""]
    assert source["request"] == {"type": "metaAndAssetCtxs"}
    assert source["observed_at_ns"] == 123


def test_selection_orders_by_day_notional_volume_descending() -> None:
    source = _source(
        volumes={
            "COIN00": "1",
            "COIN01": "3000",
            "COIN02": "2000",
        }
    )
    selected = acquisition.freeze_market_selection(source, instrument_mapper=_mapper)
    assert [item.provider_coin for item in selected[:3]] == [
        "COIN01",
        "COIN02",
        "COIN03",
    ]
    assert [item.ordinal for item in selected] == list(range(1, 21))


def test_selection_uses_deterministic_provider_coin_tie_break() -> None:
    volumes = {f"COIN{index:02d}": "100" for index in range(22)}
    selected = acquisition.freeze_market_selection(
        _source(volumes=volumes),
        instrument_mapper=_mapper,
    )
    assert [item.provider_coin for item in selected] == [
        f"COIN{index:02d}" for index in range(20)
    ]


def test_selection_rejects_fewer_than_twenty_eligible_markets() -> None:
    with pytest.raises(acquisition.AcquisitionContractError, match="fewer than 20"):
        acquisition.freeze_market_selection(_source(19), instrument_mapper=_mapper)


def test_selection_rejects_duplicate_exact_rc5_mapping() -> None:
    def colliding_mapper(coin: str) -> str:
        if coin in {"COIN00", "COIN01"}:
            return "COLLISION-USD-PERP.HYPERLIQUID"
        return _mapper(coin)

    with pytest.raises(acquisition.AcquisitionContractError, match="duplicate exact-rc5"):
        acquisition.freeze_market_selection(
            _source(),
            instrument_mapper=colliding_mapper,
        )


def test_selection_rejects_invalid_instrument_mapping() -> None:
    def rejecting_mapper(coin: str) -> str:
        if coin == "COIN03":
            raise acquisition.AcquisitionContractError("invalid exact-rc5 instrument mapping")
        return _mapper(coin)

    with pytest.raises(acquisition.AcquisitionContractError, match="invalid exact-rc5"):
        acquisition.freeze_market_selection(
            _source(),
            instrument_mapper=rejecting_mapper,
        )


def test_selection_source_hash_is_stable_and_content_bound() -> None:
    source = _source()
    assert acquisition.selection_source_hash(source) == acquisition.selection_source_hash(
        dict(reversed(tuple(source.items())))
    )
    changed = _source()
    changed["observed_at_ns"] = 1_000_001
    assert acquisition.selection_source_hash(changed) != acquisition.selection_source_hash(
        source
    )


def test_ordered_market_set_hash_is_stable_and_order_bound() -> None:
    markets = _markets()
    first = acquisition.ordered_market_set_document(markets)
    second = acquisition.ordered_market_set_document(tuple(markets))
    reordered = acquisition.ordered_market_set_document(
        (markets[1], markets[0], *markets[2:])
    )
    assert first["ordered_market_set_hash"] == second["ordered_market_set_hash"]
    assert first["ordered_market_set_hash"] != reordered["ordered_market_set_hash"]


def test_no_manual_selection_or_duration_substitution_cli_exists() -> None:
    option_strings = {
        option
        for action in acquisition._parser()._actions
        for option in action.option_strings
    }
    assert "--market" not in option_strings
    assert "--watch-market-id" not in option_strings
    assert "--target-count" not in option_strings
    assert "--run-seconds" not in option_strings
    assert acquisition.TARGET_COUNT == 20
    assert acquisition.RUN_SECONDS == 180


def test_exact_head_and_tree_binding(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(acquisition, "_git_identity", lambda: (HEAD, TREE))
    assert acquisition.bind_exact_git_identity(HEAD) == (HEAD, TREE)
    with pytest.raises(acquisition.AcquisitionContractError, match="does not match"):
        acquisition.bind_exact_git_identity("3" * 40)


def test_attempt_identity_binds_run_attempt_source_market_set_head_and_tree() -> None:
    source = _source()
    markets = acquisition.freeze_market_selection(source, instrument_mapper=_mapper)
    first, snapshot, manifest = acquisition.build_acquisition_plan(
        source=source,
        markets=markets,
        exact_head=HEAD,
        exact_tree=TREE,
        github_run_id="12345",
        github_run_attempt=1,
    )
    second, _, _ = acquisition.build_acquisition_plan(
        source=source,
        markets=markets,
        exact_head=HEAD,
        exact_tree=TREE,
        github_run_id="12345",
        github_run_attempt=2,
    )
    identity = first["acquisition_attempt_identity"]
    assert isinstance(identity, dict)
    assert identity["exact_head"] == HEAD
    assert identity["exact_tree"] == TREE
    assert identity["github_run_id"] == "12345"
    assert identity["github_run_attempt"] == 1
    assert identity["selection_source_snapshot_hash"] == (
        first["selection_source_snapshot_hash"]
    )
    assert identity["ordered_market_set_hash"] == first["ordered_market_set_hash"]
    assert first["acquisition_attempt_identity_hash"] != second[
        "acquisition_attempt_identity_hash"
    ]
    assert manifest.git_sha == HEAD
    assert manifest.git_tree == TREE
    assert manifest.pit_snapshot_hash == snapshot.snapshot_hash
    assert manifest.capture_configuration["acquisition_attempt_identity"] == identity


def test_probe_command_has_exactly_twenty_watch_market_arguments() -> None:
    markets = _markets()
    command = acquisition.build_probe_command(
        python_executable="python",
        evidence_root=Path("evidence"),
        manifest_path=Path("evidence/run-manifest.json"),
        snapshot_path=Path("evidence/pit-universe-snapshot.json"),
        probe_result_path=Path("evidence/e4-probe-result.json"),
        markets=markets,
        bar_type_builder=lambda instrument: f"{instrument}-1-MINUTE-LAST-EXTERNAL",
    )
    assert command.count("--watch-market-id") == 20
    assert [
        command[index + 1]
        for index, item in enumerate(command)
        if item == "--watch-market-id"
    ] == [item.market_id for item in markets]
    assert "--actionable-market-id" not in command


def test_probe_command_has_twenty_external_1m_bars_and_fixed_duration() -> None:
    command = acquisition.build_probe_command(
        python_executable="python",
        evidence_root=Path("evidence"),
        manifest_path=Path("manifest.json"),
        snapshot_path=Path("snapshot.json"),
        probe_result_path=Path("probe.json"),
        markets=_markets(),
        bar_type_builder=lambda instrument: f"{instrument}-1-MINUTE-LAST-EXTERNAL",
    )
    assert command.count("--bar-type") == 20
    assert command.count("--run-seconds") == 1
    assert command[command.index("--run-seconds") + 1] == "180"


def test_complete_twenty_market_three_stream_capture_classification() -> None:
    markets = _markets()
    result = _complete_probe(markets)
    assert acquisition.provider_capture_complete(result, markets) is True
    assert acquisition.classify_probe_result(0, result, markets) == "COMPLETE"


def test_provider_data_incomplete_stays_typed_and_fail_closed() -> None:
    markets = _markets()
    result = _complete_probe(markets)
    observation = result["observation"]
    assert isinstance(observation, dict)
    missing = observation["observed_streams"].pop()  # type: ignore[union-attr]
    observation["missing_streams"] = [missing]
    observation["provider_observation_pass"] = False
    result["status"] = "PROVIDER_DATA_INCOMPLETE"
    assert acquisition.provider_capture_complete(result, markets) is False
    assert acquisition.classify_probe_result(2, result, markets) == (
        "PROVIDER_DATA_INCOMPLETE"
    )


def test_application_or_provider_runtime_failure_stays_distinct() -> None:
    result = {
        "status": "APPLICATION_FAILURE",
        "failure_class": "APPLICATION_OR_PROVIDER_RUNTIME_FAILURE",
    }
    assert acquisition.classify_probe_result(3, result, _markets()) == (
        "APPLICATION_OR_PROVIDER_RUNTIME_FAILURE"
    )


def test_workflow_pr_and_default_dispatch_do_not_run_representative_capture() -> None:
    workflow = Path(".github/workflows/nautilus-vnext-g4-ci.yml").read_text()
    assert "representative_capture:" in workflow
    assert "default: false" in workflow
    capture_guard = (
        "github.event_name == 'workflow_dispatch' && inputs.representative_capture"
    )
    assert capture_guard in workflow
    assert "github.event_name == 'pull_request'" not in capture_guard


def test_public_only_zero_write_safety_non_regression() -> None:
    base = acquisition._result_base(
        exact_head=HEAD,
        exact_tree=TREE,
        github_run_id="123",
        github_run_attempt=1,
    )
    assert base["public_data_only"] is True
    assert base["zero_credentials"] is True
    assert base["zero_execution_client"] is True
    assert base["zero_signing"] is True
    assert base["zero_exchange_write"] is True
    source = inspect.getsource(acquisition.run_acquisition)
    assert "submit_order(" not in source
    assert "cancel_order(" not in source
    assert "modify_order(" not in source
