"""Callback receipt observations only; Nautilus owns connection and recovery."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from time import monotonic_ns

Stream = tuple[str, str]


class NativeFeedObservations:
    def __init__(
        self, streams: Mapping[Stream, int], *, now_ns: Callable[[], int] = monotonic_ns
    ) -> None:
        if not streams or len(streams) > 256 or any(age <= 0 for age in streams.values()):
            raise ValueError("require 1..256 streams with positive stale thresholds")
        self.thresholds = dict(streams)
        self._receipts: dict[Stream, int] = {}
        self._now = now_ns
        self.socket: dict[str, object] = {"state": "UNKNOWN"}
        self.queue: dict[str, object] = {"state": "UNKNOWN"}

    def received(self, stream: Stream) -> None:
        if stream not in self.thresholds:
            raise ValueError("unconfigured native stream")
        self._receipts[stream] = self._now()

    def socket_observed(self, *, client_id: str, endpoint: str, state: str) -> None:
        if client_id != "HYPERLIQUID" or endpoint != "hyperliquid-data-streams":
            return
        self.socket = {"state": state, "observed_monotonic_ns": self._now()}
        if state != "CONNECTED":
            self._receipts.clear()

    def queue_observed(self, event: object) -> None:
        self.queue = {
            name: str(getattr(event, name))
            for name in ("channel", "condition", "state", "queue_depth", "mean_dispatch_ns")
        }

    def snapshot(self) -> dict[str, object]:
        now = self._now()
        streams = []
        for stream, threshold in sorted(self.thresholds.items()):
            received = self._receipts.get(stream)
            age = None if received is None else now - received
            status = "UNKNOWN" if age is None or age < 0 else (
                "STALE" if age > threshold else "RECEIVING"
            )
            streams.append({
                "instrument_id": stream[0], "stream": stream[1],
                "callback_age_ns": age, "status": status,
            })
        return {"streams": streams, "socket": dict(self.socket), "queue": dict(self.queue)}
