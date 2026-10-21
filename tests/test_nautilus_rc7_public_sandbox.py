"""Opt-in finite official ExecTester protocol proof; never forward strategy research."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import time
from decimal import Decimal
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RC7_PUBLIC_SANDBOX_PROBE") != "true"
    or importlib.util.find_spec("nautilus_trader") is None,
    reason="explicit isolated native public Sandbox qualification only",
)


def test_public_quotes_to_existing_native_sandbox_fixture(tmp_path: Path) -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        pytest.skip("isolated GitHub Linux runner only")
    asyncio.run(_public_sandbox(tmp_path))


async def _public_sandbox(tmp_path: Path) -> None:
    from nautilus_trader.common import Environment
    from nautilus_trader.execution import MakerTakerFeeModel
    from nautilus_trader.model import InstrumentId, NautilusDataType, QuoteTick
    from nautilus_trader.persistence import ParquetDataCatalog

    from trader_assist_v0.nautilus_e4.native_runtime import build_native_node
    from trader_assist_v0.nautilus_e4.native_sandbox import (
        attach_sandbox_probe,
        record_sandbox_state,
    )
    from trader_assist_v0.nautilus_e4.shadow_ledger import ShadowLedger

    output = os.environ.get("RC7_SANDBOX_PROOF_OUTPUT")
    root = Path(output).parent / "native" if output else tmp_path
    root.mkdir(parents=True, exist_ok=True)
    assert not any(root.iterdir()), "fresh isolated dev-only source required"
    ledger = ShadowLedger(
        root / "protocol.dev-only.sqlite",
        strategy_id="OFFICIAL_EXEC_TESTER_PROTOCOL_ONLY",
        strategy_version="2.0.0rc7",
    )
    ledger.append(
        event_id="dev-profile",
        kind="DEV_PROFILE",
        ts_ns=time.time_ns(),
        payload={
            "classification": "DEV_ONLY_NOT_A_FORWARD_RESEARCH_PROFILE",
            "fixture": "EXISTING_OFFICIAL_EXEC_TESTER_PROTOCOL_ONLY",
            "source": "ACTUAL_PUBLIC_HYPERLIQUID_NO_SYNTHETIC_QUOTES_OR_SIGNALS",
            "fees": "EXPLICIT_SIMULATED_0.000432_PER_SIDE_NOT_ACCOUNT_FEES",
            "balances": "EXISTING_FAKE_USD_AND_USDC_NO_CONVERSION",
        },
    )
    node = build_native_node(
        root,
        sandbox=True,
        sandbox_fee_model=MakerTakerFeeModel(Decimal("0.000432"), Decimal("0.000432")),
    )
    attach_sandbox_probe(node)  # Existing opt-in built-in, not a new strategy/order mapping.
    handle, run_id = node.handle(), str(node.instance_id)
    run = asyncio.create_task(node.run_async())
    disposed = False
    try:
        await asyncio.sleep(30)  # One finite public window; no provider polling/retry loop.
        handle.stop()  # Official tester cancels/closes simulated orders on stop.
        await asyncio.wait_for(run, timeout=60)
        result = record_sandbox_state(node.cache, node.portfolio, ledger, now_ns=time.time_ns())
        fills = [
            e
            for order in node.cache.orders()
            for e in order.events()
            if type(e).__name__ == "OrderFilled"
        ]
        assert len(fills) >= 2, "NO_NATIVE_ENTRY_EXIT_FILLS_OBSERVED"
        assert all(e.commission.as_decimal() > 0 for e in fills)
        assert not node.cache.positions_open(), "VIRTUAL_POSITIONS_NOT_CLOSED"
        assert not node.cache.orders_open(), "VIRTUAL_ORDERS_NOT_CANCELED"
        assert result["snapshot"]["realized_pnl"]
        assert ledger.verify() > 0
        node.dispose()  # Official live sink seals only on dispose, not on stop/flush.
        disposed = True
        catalog = ParquetDataCatalog(str(root))
        quotes = [x for x in catalog.read_live_run(run_id) if isinstance(x, QuoteTick)]
        identity = InstrumentId.from_str("ETH-USD-PERP.HYPERLIQUID")
        quotes = [x for x in quotes if x.instrument_id == identity]
        assert quotes, "PUBLIC_QUOTES_NOT_OBSERVED_NO_SANDBOX_QUALIFICATION"
        assert all(e.ts_init >= min(q.ts_init for q in quotes) for e in fills)
        sources = list((root / "live" / run_id).rglob("*.feather"))
        catalog.convert_stream_to_data(
            run_id, NautilusDataType.QuoteTick, environment=Environment.LIVE
        )
        restored = catalog.query_quote_ticks(identifiers=[str(identity)])
        assert [q.to_dict() for q in restored] == [q.to_dict() for q in quotes]
        catalog.convert_stream_to_data(
            run_id, NautilusDataType.QuoteTick, environment=Environment.LIVE
        )
        assert len(catalog.query_quote_ticks(identifiers=[str(identity)])) == len(quotes)
        assert sources and all(p.exists() for p in sources)
        result.update(
            classification="DEV_ONLY_NOT_A_FORWARD_RESEARCH_PROFILE",
            public_quote_count=len(quotes),
            first_public_ts_init=min(q.ts_init for q in quotes),
            last_public_ts_init=max(q.ts_init for q in quotes),
            native_run_id=run_id,
            native_fill_count=len(fills),
            source="OFFICIAL_HYPERLIQUID_PUBLIC_DATA_CLIENT",
            archive="CLOSED_NATIVE_FEATHER_TO_TYPED_PARQUET_QUOTES_ONLY",
            rolling_catalog="NOT_QUALIFIED",
            repeated_native_conversion="NO_DUPLICATE_ROWS_SOURCE_RETAINED",
            approved_strategy_shadow="NOT_QUALIFIED_NO_APPROVED_ORDER_PROFILE",
            causal_scope="PROTOCOL_QUOTE_BEFORE_FILL_NOT_APPROVED_STRATEGY_SIGNAL_PROOF",
            risk_engine="EXISTING_NATIVE_BYPASS_FALSE",
            external_order_writes=0,
        )
        if output:
            Path(output).write_text(json.dumps(result, indent=2) + "\n")
    finally:
        if not run.done():
            handle.stop()
            await asyncio.wait_for(run, timeout=60)
        if not disposed:
            node.dispose()
        ledger.close()
