# mypy: disable-error-code="import-not-found"
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


def build_native_node(
    root: Path,
    *,
    sandbox: bool = False,
    sandbox_fee_model: Any = None,
    venues: tuple[str, ...] = ("HYPERLIQUID",),
) -> Any:
    from importlib.metadata import version

    if (
        not venues
        or len(set(venues)) != len(venues)
        or not set(venues) <= {"HYPERLIQUID", "BINANCE", "OKX"}
    ):
        raise ValueError("unsupported native public venue selection")
    if sandbox and venues != ("HYPERLIQUID",):
        raise ValueError("reference capture is strictly public-only")
    if sandbox and sandbox_fee_model is None:
        raise ValueError("Sandbox requires an explicit native fee model; never infer account fees")

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

    data_clients: dict[str, Any] = {}
    data_factories: dict[str, Any] = {}
    if "HYPERLIQUID" in venues:
        data_clients["HYPERLIQUID"] = HyperliquidDataClientConfig(
            environment=HyperliquidEnvironment.MAINNET,
            stale_stream_recovery_enabled=True,
        )
        data_factories["HYPERLIQUID"] = HyperliquidDataClientFactory()
    if "BINANCE" in venues:
        from nautilus_trader.adapters.binance import (
            BinanceDataClientConfig,
            BinanceDataClientFactory,
            BinanceEnvironment,
            BinanceInstrumentProviderConfig,
            BinanceProductType,
            BinanceSpotMarketDataMode,
        )

        data_clients["BINANCE"] = BinanceDataClientConfig(
            product_type=BinanceProductType.SPOT,
            environment=BinanceEnvironment.LIVE,
            spot_market_data_mode=BinanceSpotMarketDataMode.Json,
            # Official read-only market-data hosts; neither supports account/order APIs.
            base_url_http="https://data-api.binance.vision",
            base_url_ws="wss://data-stream.binance.vision:443/ws",
            instrument_provider=BinanceInstrumentProviderConfig(
                load_all=True,
                query_commission_rates=False,
            ),
            api_key=None,
            api_secret=None,
        )
        data_factories["BINANCE"] = BinanceDataClientFactory()
    if "OKX" in venues:
        from nautilus_trader.adapters.okx import (
            OKXDataClientConfig,
            OKXDataClientFactory,
            OKXEnvironment,
            OKXInstrumentType,
        )

        data_clients["OKX"] = OKXDataClientConfig(
            instrument_types=[OKXInstrumentType.SWAP],
            environment=OKXEnvironment.LIVE,
            api_key=None,
            api_secret=None,
            api_passphrase=None,
            load_spreads=False,
        )
        data_factories["OKX"] = OKXDataClientFactory()
    config = LiveNodeConfig(
        environment=Environment.LIVE,
        trader_id=TraderId("TRADEOS-RC7-001"),
        streaming=streaming_config(root, continuous=True),
        shutdown_on_error=True,
        risk_engine=LiveRiskEngineConfig(bypass=False),
        exec_engine=LiveExecutionEngineConfig(reconciliation=True),
        data_clients=data_clients,
        exec_clients={},
    )
    builder = LiveNodeBuilder.from_config(
        "TRADEOS-RC7",
        config,
        data_factories=data_factories,
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
                # Official HL metadata uses USD quote and USDC ETH settlement.
                # Native fees/PnL debit USD: declare both simulated balances,
                # keeping them separate (no invented USD/USDC conversion rate).
                starting_balances=[Money.from_str("100000 USDC"), Money.from_str("100000 USD")],
                oms_type=OmsType.NETTING,
                account_type=AccountType.MARGIN,
                book_type=BookType.L1_MBP,
                reject_stop_orders=True,
                use_reduce_only=True,
                fee_model=sandbox_fee_model,
            ),
        )
    return builder.build()
