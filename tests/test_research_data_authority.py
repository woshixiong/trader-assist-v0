"""Healthy external context cannot satisfy a Hyperliquid execution-truth gap."""

import ast
from pathlib import Path

import pytest
from test_research_data_admission import admission, event

from trader_assist_v0.nautilus_e4.contracts import SourceEvent
from trader_assist_v0.nautilus_e4.markettruth import Depth10PublicationGate, MarketTruthRef
from trader_assist_v0.research_data.admission import ExternalReferenceLedger


def test_external_contract_cannot_enter_execution_truth():
    external = event(admission())
    with pytest.raises(ValueError):
        SourceEvent.model_validate(external.model_dump(mode="json"))
    with pytest.raises(ValueError):
        MarketTruthRef.model_validate(external.model_dump(mode="json"))
    assert not isinstance(external, SourceEvent)


def test_hl_gap_stays_gapped_with_healthy_disagreeing_external_providers():
    gate = Depth10PublicationGate()
    args = dict(
        market_id="hl-only", ts_event=100, ts_init=100, admission_ts=100, continuity_complete=False
    )
    before = gate.admit(**args)
    for provider, price in (("BINANCE", "10"), ("OKX", "11")):
        bound = admission(provider=provider)
        ExternalReferenceLedger(bound).observe(event(bound, price=price), evaluated_at_ns=1001)
    assert gate.admit(**args) == before == "DEPTH10_CONTINUITY_NOT_COMPLETE"


def test_new_boundary_has_no_e4_strategy_or_transport_repair_imports():
    root = Path(__file__).resolve().parents[1] / "src/trader_assist_v0/research_data"
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text())
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        assert not any("nautilus_e4" in name or "multi_asset_shadow" in name for name in imports)
        names = {
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.ClassDef)
        }
        assert not names & {"submit_order", "repair_markettruth", "reconnect", "poll", "sign"}
