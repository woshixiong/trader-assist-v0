# mypy: disable-error-code="import-not-found"
"""Bounded synchronous native batches. Errors leave the entire batch uncertain."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from time import monotonic_ns
from typing import Any


class NativeCatalogBatchSink:
    def __init__(
        self, root: Path, *, batch_size: int = 512,
        now_ns: Callable[[], int] = monotonic_ns,
    ) -> None:
        from nautilus_trader.persistence import ParquetDataCatalog

        if not 1 <= batch_size <= 4096:
            raise ValueError("batch_size must be 1..4096")
        self.root = root
        self._factory = ParquetDataCatalog
        root.mkdir(parents=True, exist_ok=True)
        self._catalog = self._factory(str(root))
        self._batch_size = batch_size
        self._now = now_ns
        self._last_flush = now_ns()
        self._pending: list[Any] = []
        self.verified = 0
        self.failed = False
        self.closed = False

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def write_instruments(self, instruments: list[Any]) -> None:
        self._require_open()
        try:
            self._catalog.write_instruments(instruments)
        except Exception:
            self.failed = True
            raise

    def _require_open(self) -> None:
        if self.failed or self.closed:
            raise RuntimeError("catalog sink failed/closed; unverified batch must not be retried")

    @staticmethod
    def _route(event: Any) -> tuple[str, str, str, str]:
        from nautilus_trader.model import Bar, OrderBookDepth10, QuoteTick, TradeTick

        if isinstance(event, QuoteTick):
            return "quote_ticks", str(event.instrument_id), "identifiers", str(event.instrument_id)
        if isinstance(event, TradeTick):
            return "trade_ticks", str(event.instrument_id), "identifiers", str(event.instrument_id)
        if isinstance(event, OrderBookDepth10):
            return (
                "order_book_depths", str(event.instrument_id), "instrument_ids",
                str(event.instrument_id),
            )
        if isinstance(event, Bar):
            return "bars", str(event.bar_type), "identifiers", str(event.bar_type)
        raise TypeError("unsupported native catalog event")

    def append(self, event: Any) -> None:
        self._require_open()
        self._route(event)
        self._pending.append(event)
        if len(self._pending) >= self._batch_size:
            self.flush()
        else:
            self.flush_due()

    def flush_due(self) -> None:
        self._require_open()
        if self._now() - self._last_flush >= 1_000_000_000:
            self.flush()

    def flush(self) -> None:
        self._require_open()
        groups: dict[tuple[str, str, str, str], list[Any]] = defaultdict(list)
        for event in self._pending:
            groups[self._route(event)].append(event)
        try:
            for (family, _stream, key, identifier), events in groups.items():
                timestamps = [int(event.ts_init) for event in events]
                if timestamps != sorted(timestamps):
                    raise ValueError("native batch ts_init must be nondecreasing")
                getattr(self._catalog, "write_" + family)(events)
                reopened = self._factory(str(self.root))
                actual = getattr(reopened, "query_" + family)(
                    **{key: [identifier]}, start=min(timestamps), end=max(timestamps),
                )
                if list(actual) != events:
                    raise RuntimeError("native catalog fresh-instance batch readback mismatch")
        except Exception:
            self.failed = True
            # Some groups may already be written. Retain all references and never retry.
            raise
        self.verified += len(self._pending)
        self._pending.clear()
        self._last_flush = self._now()

    def close(self) -> None:
        if not self.closed:
            self.flush()
            self.closed = True

    def observation(self) -> dict[str, object]:
        return {
            "verified_events": self.verified, "unverified_events": len(self._pending),
            "write_or_readback_failed": self.failed, "closed": self.closed,
            "crash_atomicity_proven": False, "continuity_proven": False,
        }
