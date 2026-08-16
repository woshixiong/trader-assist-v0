from __future__ import annotations

from datetime import UTC, datetime

from trader_assist_v0.multi_asset_shadow.resolution import (
    FIRST_LAUNCH_20,
    FIRST_LAUNCH_20_DISPLAYS,
    INITIAL_40,
    resolve_first_launch_20,
    resolve_initial_40,
)

NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def _metadata() -> tuple[list[object], list[object]]:
    native = []
    hip3 = []
    for request in INITIAL_40:
        raw = {"name": request.coin, "szDecimals": 2, "maxLeverage": 10}
        (native if request.dex == "MAIN" else hip3).append(raw)
    return [{"name": "main"}, {"name": "xyz"}], [{"universe": native}, {"universe": hip3}]


def test_manual_40_is_exact_with_one_skhx_and_fixture_verified_wtioil_cl() -> None:
    dexes, metas = _metadata()
    resolved = resolve_initial_40(perp_dexes=dexes, all_perp_metas=metas, observed_at=NOW)
    assert len(INITIAL_40) == len(resolved) == 40
    assert [item.request.display for item in resolved].count("SKHX") == 1
    assert all(item.request.display != "TAO" for item in resolved)
    wti = next(item for item in resolved if item.request.display == "WTIOIL")
    assert wti.status == "RESOLVED"
    assert wti.market is not None and wti.market.identity.coin == "xyz:CL"


def test_first_launch_20_exact_strategy_selection_reuses_manual_40_identity() -> None:
    expected = (
        "BTC",
        "ETH",
        "HYPE",
        "SOL",
        "SKHX",
        "MU",
        "SNDK",
        "XYZ100",
        "SP500",
        "WTIOIL",
        "DRAM",
        "SPCX",
        "SILVER",
        "NVDA",
        "SMSN",
        "EWY",
        "GOLD",
        "XRP",
        "TSLA",
        "GOOGL",
    )
    assert FIRST_LAUNCH_20_DISPLAYS == expected
    assert tuple(request.display for request in FIRST_LAUNCH_20) == expected
    assert len(FIRST_LAUNCH_20) == len({request.display for request in FIRST_LAUNCH_20}) == 20

    manual_by_display = {request.display: request for request in INITIAL_40}
    for request in FIRST_LAUNCH_20:
        assert request == manual_by_display[request.display]

    skhx = next(request for request in FIRST_LAUNCH_20 if request.display == "SKHX")
    assert skhx.coin == "xyz:SKHX"
    assert skhx.aliases == ("SKHYNIX",)
    wti = next(request for request in FIRST_LAUNCH_20 if request.display == "WTIOIL")
    assert wti.coin == "xyz:CL"
    assert wti.aliases == ("CL",)
    assert all(request.display != "TAO" for request in FIRST_LAUNCH_20)

    dexes, metas = _metadata()
    resolved = resolve_first_launch_20(
        perp_dexes=dexes,
        all_perp_metas=metas,
        observed_at=NOW,
    )
    assert len(resolved) == 20
    assert tuple(item.request.display for item in resolved) == expected
    assert all(item.status == "RESOLVED" and item.market is not None for item in resolved)
    resolved_wti = next(item for item in resolved if item.request.display == "WTIOIL")
    assert resolved_wti.market is not None
    assert resolved_wti.market.identity.coin == "xyz:CL"
