# mypy: disable-error-code="import-not-found"
"""Bounded provider-native history specifications; no acquisition runner."""

from datetime import UTC, datetime
from typing import Any, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from .contracts import BoundRecord, ControlReplan, ProviderCapability, SourceMode


class OfficialArchiveRoute(BoundRecord):
    provider: Literal["BINANCE", "OKX"]
    source_locator: str
    layout_hash: str = Field(pattern="^[a-f0-9]{64}$")
    semantics_proof_locator: str = Field(min_length=1)
    datatype: str
    product: str
    source_mode: Literal[SourceMode.HISTORY] = SourceMode.HISTORY

    @model_validator(mode="after")
    def official_locator(self) -> Self:
        parts = urlsplit(self.source_locator)
        host = "data.binance.vision" if self.provider == "BINANCE" else "www.okx.com"
        if (
            parts.scheme != "https"
            or parts.hostname != host
            or parts.username
            or parts.password
            or parts.port not in {None, 443}
            or parts.fragment
        ):
            raise ValueError("official archive profile required")
        return self


class HistoricalRequestSpec(BoundRecord):
    capability: ProviderCapability
    instrument_id: str = Field(min_length=1)
    start_ns: int = Field(gt=0)
    end_ns: int = Field(gt=0)
    limit: int = Field(gt=0, le=1000)
    bar_timestamp_meaning: Literal["OPEN", "CLOSE", "NOT_APPLICABLE"]
    finality_proven: bool

    @model_validator(mode="after")
    def bounded_history(self) -> Self:
        if self.start_ns >= self.end_ns or self.capability.source_mode != SourceMode.HISTORY:
            raise ValueError("bounded HISTORY source mode required")
        self.capability.require_core_proof()
        if self.capability.adapter_owner != "NAUTILUS_RC5":
            raise ValueError("no history substitute for the OKX current OI exception")
        if self.capability.datatype.startswith("BAR_") and (
            not self.finality_proven or self.bar_timestamp_meaning == "NOT_APPLICABLE"
        ):
            raise ControlReplan("historical bar semantics unproven")
        return self

    def dispatch(self, strategy: Any) -> str:
        from nautilus_trader import model

        start = datetime.fromtimestamp(self.start_ns // 1_000_000_000, UTC)
        end = datetime.fromtimestamp(self.end_ns // 1_000_000_000, UTC)
        if self.start_ns % 1_000_000_000 or self.end_ns % 1_000_000_000:
            raise ValueError("native datetime boundary requires exact whole-second cut")
        kwargs = dict(
            start=start,
            end=end,
            limit=self.limit,
            client_id=model.ClientId(self.capability.provider),
        )
        datatype = self.capability.datatype
        instrument = model.InstrumentId.from_str(self.instrument_id)
        if datatype in {"BAR_1M", "BAR_5M"}:
            minutes = 1 if datatype == "BAR_1M" else 5
            return str(
                strategy.request_bars(
                    model.BarType.from_str(f"{self.instrument_id}-{minutes}-MINUTE-LAST-EXTERNAL"),
                    **kwargs,
                )
            )
        if datatype == "TRADE":
            return str(strategy.request_trades(instrument, **kwargs))
        if datatype == "FUNDING":
            return str(strategy.request_funding_rates(instrument, **kwargs))
        if datatype == "OI" and self.capability.provider == "BINANCE":
            return str(
                strategy.request_data(
                    model.DataType(
                        "BinanceFuturesOpenInterestHist",
                        metadata={"instrument_id": self.instrument_id, "period": "5m"},
                    ),
                    **kwargs,
                )
            )
        raise ControlReplan("required historical dispatch unproven; no silent live substitution")
