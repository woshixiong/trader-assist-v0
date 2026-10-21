"""Unfrozen rc7 API adapter for the frozen research replay algorithm.

rc7 moved fees from CryptoPerpetual to explicit venue FeeModel configuration.
The frozen algorithm still reads instrument fee fields and imports its native
modules through a module-local dependency binding. This adapter supplies that
legacy *view*, unwraps the real instrument at the native engine boundary, and
passes the declared replay cost profile to the official MakerTakerFeeModel.

No upstream class, stdlib module, sys.modules entry or native core is patched.
There is one native BacktestEngine; all matching/cache/portfolio operations
remain native. ContextVar confines the dependency views to one synchronous
replay invocation, including nested calls and exception cleanup. The fee rates
are simulation assumptions from the accepted run identity, not account fees.
"""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from decimal import Decimal, localcontext
from functools import wraps
from importlib.metadata import version
from types import ModuleType
from typing import Any


@dataclass(frozen=True)
class _FeeProfile:
    instrument: Any
    maker_rate: Decimal
    taker_rate: Decimal


_active: ContextVar[_FeeProfile | None] = ContextVar("research_replay_native_fees", default=None)


@dataclass(frozen=True)
class _InstrumentFeeView:
    """Read-only legacy fee fields over a verified real native instrument."""

    native: Any
    maker_fee: Decimal
    taker_fee: Decimal

    def __getattr__(self, name: str) -> Any:
        return getattr(self.native, name)


class _EngineView:
    def __init__(self, config: Any) -> None:
        profile = _active.get()
        if profile is None:
            raise RuntimeError("native fee compatibility requires a bound replay profile")
        self._profile = profile
        self._engine = importlib.import_module("nautilus_trader.backtest").BacktestEngine(config)

    def add_venue(self, **kwargs: Any) -> None:
        if "fee_model" in kwargs:
            raise ValueError("frozen replay cannot override its bound native fee model")
        execution = importlib.import_module("nautilus_trader.execution")
        self._engine.add_venue(
            **kwargs,
            fee_model=execution.MakerTakerFeeModel(
                maker_rate=self._profile.maker_rate,
                taker_rate=self._profile.taker_rate,
            ),
        )

    def add_instrument(self, instrument: Any) -> None:
        if not isinstance(instrument, _InstrumentFeeView):
            raise TypeError("native replay requires its bound instrument fee view")
        if instrument.native is not self._profile.instrument:
            raise ValueError("native replay instrument differs from bound fee profile")
        self._engine.add_instrument(instrument.native)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._engine, name)


class _ModuleView:
    def __init__(self, module: ModuleType, overrides: dict[str, Any]) -> None:
        self._module = module
        self._overrides = overrides

    def __getattr__(self, name: str) -> Any:
        return self._overrides[name] if name in self._overrides else getattr(self._module, name)


class _NativeModules:
    def import_module(self, name: str) -> Any:
        module = importlib.import_module(name)
        if _active.get() is not None:
            if name == "nautilus_trader.model":
                # The constructor/type in the upstream module is never changed.
                # Views are created only after verifying the real native type below.
                return _ModuleView(
                    module,
                    {
                        "CryptoPerpetual": (
                            module.CryptoPerpetual,
                            _InstrumentFeeView,
                        )
                    },
                )
            if name == "nautilus_trader.backtest":
                return _ModuleView(module, {"BacktestEngine": _EngineView})
        return module


native_modules = _NativeModules()


def native_fee_compatibility[**P, R](function: Callable[P, R]) -> Callable[P, R]:
    signature = inspect.signature(function)

    @wraps(function)
    def bound(*args: P.args, **kwargs: P.kwargs) -> R:
        if version("nautilus-trader") != "2.0.0rc7":
            # Preserve the historical call behavior; its existing exact-version
            # gate remains responsible for admitting any runtime.
            return function(*args, **kwargs)
        arguments = signature.bind(*args, **kwargs)
        instrument = arguments.arguments["instrument"]
        model = importlib.import_module("nautilus_trader.model")
        if not isinstance(instrument, model.CryptoPerpetual):
            raise TypeError("native Hyperliquid CryptoPerpetual required")
        cost = arguments.arguments["run"].cost
        with localcontext() as arithmetic:
            arithmetic.prec = 80
            maker, taker = cost.maker_bps / Decimal(10_000), cost.taker_bps / Decimal(10_000)
        if not maker.is_finite() or not taker.is_finite():
            raise ValueError("native replay fee assumptions must be finite")
        profile = _FeeProfile(instrument, maker, taker)
        arguments.arguments["instrument"] = _InstrumentFeeView(instrument, maker, taker)
        token = _active.set(profile)
        try:
            return function(*arguments.args, **arguments.kwargs)
        finally:
            _active.reset(token)

    return bound
