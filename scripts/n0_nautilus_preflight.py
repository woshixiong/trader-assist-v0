from __future__ import annotations

import argparse
import importlib.metadata as metadata
import inspect
import json
import platform
import sys
from pathlib import Path
from typing import Any

EXPECTED_VERSION = "2.0.0rc4"
EXPECTED_WHEEL = "nautilus_trader-2.0.0rc4-cp312-cp312-manylinux_2_34_x86_64.whl"
EXPECTED_WHEEL_SHA256 = "8d3591aa4d86c7133be2115b1037ffadafb36449214d9973d496bdc80e21ad93"


def signature_or_error(obj: Any) -> str:
    try:
        return str(inspect.signature(obj))
    except Exception as exc:
        return f"<unavailable:{type(exc).__name__}:{exc}>"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    assert sys.platform.startswith("linux"), sys.platform
    assert platform.machine() == "x86_64", platform.machine()
    assert sys.version_info[:2] == (3, 12), sys.version
    assert metadata.version("nautilus_trader") == EXPECTED_VERSION

    from nautilus_trader.backtest import BacktestEngine
    from nautilus_trader.backtest import BacktestEngineConfig
    from nautilus_trader.model import CustomData
    from nautilus_trader.model import DataType
    from nautilus_trader.model import InstrumentId
    from nautilus_trader.model import StrategyId
    from nautilus_trader.model import register_custom_data_class
    from nautilus_trader.persistence import RustTestCustomData
    from nautilus_trader.trading import Strategy
    from nautilus_trader.trading import StrategyConfig

    class ProbeStrategy(Strategy):
        def on_start(self) -> None:
            self.subscribe_data(self.data_type)

        def on_data(self, data: CustomData) -> None:
            self.received.append(data)

    register_custom_data_class(RustTestCustomData)
    instrument_id = InstrumentId.from_str("N0-PREFLIGHT.TEST")
    data_type = DataType(
        "RustTestCustomData",
        {"source": "trade-os-n0-preflight"},
        str(instrument_id),
    )
    events = [
        CustomData(data_type, RustTestCustomData(instrument_id, 1.25, True, 1, 1)),
        CustomData(data_type, RustTestCustomData(instrument_id, 2.50, False, 2, 2)),
    ]

    strategy = ProbeStrategy(
        StrategyConfig(
            strategy_id=StrategyId("N0-PREFLIGHT-STRATEGY"),
            log_events=False,
            log_commands=False,
        ),
    )
    strategy.data_type = data_type
    strategy.received = []

    engine = BacktestEngine(
        BacktestEngineConfig(
            bypass_logging=True,
            run_analysis=False,
        ),
    )
    try:
        engine.add_strategy(strategy)
        engine.add_data(list(reversed(events)), validate=True, sort=True)
        engine.run()
        result = engine.get_result()

        assert result.iterations == 2, result.iterations
        assert [item.data.value for item in strategy.received] == [1.25, 2.50]
        assert [item.ts_event for item in strategy.received] == [1, 2]
        assert [item.ts_init for item in strategy.received] == [1, 2]
        assert [item.data_type.identifier for item in strategy.received] == [
            str(instrument_id),
            str(instrument_id),
        ]

        witness = {
            "result": "PASS",
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "nautilus_version": metadata.version("nautilus_trader"),
            "expected_wheel": EXPECTED_WHEEL,
            "expected_wheel_sha256": EXPECTED_WHEEL_SHA256,
            "official_event_path_smoke": {
                "engine": type(engine).__name__,
                "strategy": type(strategy).__name__,
                "iterations": result.iterations,
                "received_values": [item.data.value for item in strategy.received],
                "received_ts_event": [item.ts_event for item in strategy.received],
                "received_ts_init": [item.ts_init for item in strategy.received],
                "data_type": {
                    "type_name": data_type.type_name,
                    "metadata": data_type.metadata,
                    "identifier": data_type.identifier,
                },
            },
            "api": {
                "BacktestEngine": signature_or_error(BacktestEngine),
                "BacktestEngineConfig": signature_or_error(BacktestEngineConfig),
                "DataType": signature_or_error(DataType),
                "CustomData": signature_or_error(CustomData),
                "StrategyConfig": signature_or_error(StrategyConfig),
                "BacktestEngine_public_members": sorted(
                    name for name in dir(BacktestEngine) if not name.startswith("_")
                ),
                "Strategy_public_members": sorted(
                    name for name in dir(Strategy) if not name.startswith("_")
                ),
            },
        }
        Path(args.output).write_text(json.dumps(witness, indent=2, sort_keys=True) + "\n")
    finally:
        engine.dispose()

    print("N0_PREWRITER_EVENT_PATH_SMOKE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
