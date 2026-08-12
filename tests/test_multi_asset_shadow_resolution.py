from __future__ import annotations

from datetime import UTC, datetime

from trader_assist_v0.multi_asset_shadow.resolution import INITIAL_40, resolve_initial_40

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
