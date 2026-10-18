"""One rc7 native public transport/catalog owner with optional native Sandbox.

No credentialed execution node can be started through this entry point. The
inert real-execution construction contract lives in native_execution.py.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .native_catalog import RC7_VERSION, streaming_config
from .safety import assert_public_only


def build_native_node(root: Path, *, sandbox: bool = False) -> Any:
    from importlib.metadata import version

    assert_public_only(env=os.environ)
    if version("nautilus-trader") != RC7_VERSION:
        raise RuntimeError("exact rc7 required")
    from nautilus_trader.adapters.hyperliquid import (
        HyperliquidDataClientConfig,
        HyperliquidDataClientFactory,
        HyperliquidEnvironment,
    )
    from nautilus_trader.common import Environment
    from nautilus_trader.live import (
        LiveExecutionEngineConfig,
        LiveNodeBuilder,
        LiveNodeConfig,
        LiveRiskEngineConfig,
    )
    from nautilus_trader.model import TraderId

    config = LiveNodeConfig(
        environment=Environment.LIVE,
        trader_id=TraderId("TRADEOS-RC7-001"),
        streaming=streaming_config(root),
        shutdown_on_error=True,
        risk_engine=LiveRiskEngineConfig(bypass=False),
        exec_engine=LiveExecutionEngineConfig(reconciliation=True),
        data_clients={
            "HYPERLIQUID": HyperliquidDataClientConfig(
                environment=HyperliquidEnvironment.MAINNET,
                stale_stream_recovery_enabled=True,
            )
        },
        exec_clients={},
    )
    builder = LiveNodeBuilder.from_config(
        "TRADEOS-RC7",
        config,
        data_factories={"HYPERLIQUID": HyperliquidDataClientFactory()},
    )
    if sandbox:
        from nautilus_trader.adapters.sandbox import (
            SandboxExecutionClientConfig,
            SandboxExecutionClientFactory,
        )
        from nautilus_trader.model import AccountType, BookType, Money, OmsType, Venue

        builder.add_simulated_exec_client(
            "HYPERLIQUID",
            SandboxExecutionClientFactory(),
            SandboxExecutionClientConfig(
                venue=Venue("HYPERLIQUID"),
                starting_balances=[Money.from_str("100000 USDC")],
                oms_type=OmsType.NETTING,
                account_type=AccountType.MARGIN,
                book_type=BookType.L1_MBP,
                reject_stop_orders=True,
                use_reduce_only=True,
            ),
        )
    return builder.build()
