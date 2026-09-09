"""Thin public-surface Nautilus 2.0.0rc4 host for the E3 pilot."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Self

from trader_assist_v0.contracts.common import decimal_to_canonical_string

from .contracts import (
    E3_CONTRACT_SCHEMA_VERSION,
    PilotEvaluationEnvelope,
    StrategyInputEvent,
    revalidate_strategy_input_event,
)
from .strategy_package import (
    PilotStrategyEvaluator,
    StrategyPackageManifest,
    select_strategy_package,
)

_PROJECT_DATA_TYPE_NAME = "TradeOsStrategyInputEventV1"
_PROJECT_DATA_TYPE_IDENTIFIER = "TRADE-OS.E3-STRATEGY-INPUT"

if TYPE_CHECKING:

    class StrategyConfig:
        def __new__(cls, *args: object, **kwargs: object) -> Self: ...

        def __init__(self, *args: object, **kwargs: object) -> None: ...

    class DataType:
        def __init__(
            self,
            type_name: str,
            metadata: dict[str, str] | None = None,
            identifier: str | None = None,
        ) -> None: ...

    class CustomData:
        data_type: DataType
        data: object
        ts_event: int
        ts_init: int

        def __init__(self, data_type: DataType, data: object) -> None: ...

    class ImportableStrategyConfig:
        def __init__(
            self,
            strategy_path: str,
            config_path: str,
            config: dict[str, object],
        ) -> None: ...

    class Strategy:
        def __init__(self, config: StrategyConfig | None = None) -> None: ...

        def subscribe_data(self, data_type: DataType) -> None: ...

else:
    from nautilus_trader.model import CustomData, DataType
    from nautilus_trader.trading import ImportableStrategyConfig, Strategy, StrategyConfig


class NautilusPilotStrategyConfig(StrategyConfig):
    """Serializable identity/configuration only; no callbacks or runtime objects."""

    _CUSTOM_FIELDS = (
        "package_version",
        "strategy_version",
        "parameter_version",
        "scanner_version",
        "kernel_schema_version",
        "trade_os_release_sha",
        "manifest_hash",
        "market_id",
        "minimum_tick",
    )

    package_version: str
    strategy_version: str
    parameter_version: str
    scanner_version: str
    kernel_schema_version: str
    trade_os_release_sha: str
    manifest_hash: str
    market_id: str
    minimum_tick: str

    def __new__(cls, *args: object, **kwargs: object) -> Self:
        for key in cls._CUSTOM_FIELDS:
            kwargs.pop(key, None)
        return super().__new__(cls, *args, **kwargs)

    def __init__(
        self,
        package_version: str,
        strategy_version: str,
        parameter_version: str,
        scanner_version: str,
        kernel_schema_version: str,
        trade_os_release_sha: str,
        manifest_hash: str,
        market_id: str,
        minimum_tick: str,
        **_kwargs: object,
    ) -> None:
        super().__init__()
        self.package_version = package_version
        self.strategy_version = strategy_version
        self.parameter_version = parameter_version
        self.scanner_version = scanner_version
        self.kernel_schema_version = kernel_schema_version
        self.trade_os_release_sha = trade_os_release_sha
        self.manifest_hash = manifest_hash
        self.market_id = market_id
        self.minimum_tick = minimum_tick


def _minimum_tick(value: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("minimum_tick is not a canonical Decimal string") from exc
    if (
        not parsed.is_finite()
        or parsed <= 0
        or decimal_to_canonical_string(parsed) != value
    ):
        raise ValueError("minimum_tick is not a canonical positive Decimal string")
    return parsed


def _validate_market_id(value: str) -> str:
    if len(value) != 64:
        raise ValueError("market_id must be a canonical SHA-256 identity")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError("market_id must be a canonical SHA-256 identity") from exc
    if value != value.lower():
        raise ValueError("market_id must be lowercase canonical hex")
    return value


def _project_data_type() -> DataType:
    return DataType(
        _PROJECT_DATA_TYPE_NAME,
        metadata={"schema_version": E3_CONTRACT_SCHEMA_VERSION},
        identifier=_PROJECT_DATA_TYPE_IDENTIFIER,
    )


def build_custom_data(event: StrategyInputEvent) -> CustomData:
    """Wrap an exact project input event in the public rc4 custom-data type."""
    validated = revalidate_strategy_input_event(event)
    return CustomData(_project_data_type(), validated)


def build_importable_strategy_config(
    *,
    manifest: StrategyPackageManifest,
    market_id: str,
    minimum_tick: Decimal,
) -> ImportableStrategyConfig:
    """Construct the exact public rc4 importable Strategy boundary."""
    selected = select_strategy_package(
        package_version=manifest.package_version,
        strategy_version=manifest.strategy_version,
        parameter_version=manifest.parameter_version,
        scanner_version=manifest.scanner_version,
        kernel_schema_version=manifest.kernel_schema_version,
        trade_os_release_sha=manifest.trade_os_release_sha,
        manifest_hash=manifest.manifest_hash,
    )
    canonical_tick = decimal_to_canonical_string(minimum_tick)
    _minimum_tick(canonical_tick)
    canonical_market = _validate_market_id(market_id)
    config: dict[str, object] = {
        "package_version": selected.package_version,
        "strategy_version": selected.strategy_version,
        "parameter_version": selected.parameter_version,
        "scanner_version": selected.scanner_version,
        "kernel_schema_version": selected.kernel_schema_version,
        "trade_os_release_sha": selected.trade_os_release_sha,
        "manifest_hash": selected.manifest_hash,
        "market_id": canonical_market,
        "minimum_tick": canonical_tick,
    }
    return ImportableStrategyConfig(
        strategy_path="trader_assist_v0.nautilus_pilot.host:NautilusPilotStrategy",
        config_path="trader_assist_v0.nautilus_pilot.host:NautilusPilotStrategyConfig",
        config=config,
    )


class NautilusPilotStrategy(Strategy):
    """Nautilus lifecycle shell around the project-owned pure evaluator."""

    def __init__(self, config: NautilusPilotStrategyConfig) -> None:
        super().__init__(config)
        manifest = select_strategy_package(
            package_version=config.package_version,
            strategy_version=config.strategy_version,
            parameter_version=config.parameter_version,
            scanner_version=config.scanner_version,
            kernel_schema_version=config.kernel_schema_version,
            trade_os_release_sha=config.trade_os_release_sha,
            manifest_hash=config.manifest_hash,
        )
        market_id = _validate_market_id(config.market_id)
        self._project_data_type = _project_data_type()
        self._evaluator = PilotStrategyEvaluator(
            manifest=manifest,
            market_id=market_id,
            minimum_tick=_minimum_tick(config.minimum_tick),
        )
        self._pilot_outputs: list[PilotEvaluationEnvelope] = []

    @property
    def pilot_outputs(self) -> tuple[PilotEvaluationEnvelope, ...]:
        """Ephemeral proof output; loss never removes authoritative project truth."""
        return tuple(self._pilot_outputs)

    def on_start(self) -> None:
        self.subscribe_data(self._project_data_type)

    def on_data(self, data: CustomData | StrategyInputEvent) -> None:
        if type(data) is StrategyInputEvent:
            event = revalidate_strategy_input_event(data)
        elif isinstance(data, CustomData) and data.data_type == self._project_data_type:
            event = revalidate_strategy_input_event(data.data)
            if data.ts_event != event.ts_event or data.ts_init != event.ts_init:
                raise ValueError(
                    "Nautilus custom-data timestamps contradict project close boundary"
                )
        else:
            raise ValueError("Nautilus callback received an unexpected custom-data type")
        output = self._evaluator.evaluate(event)
        if output is not None:
            self._pilot_outputs.append(output)
