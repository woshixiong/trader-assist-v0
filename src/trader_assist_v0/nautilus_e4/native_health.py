"""Thin native-event freshness certificate; never reconnects or reconstructs a book."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NativeHealth:
    required: dict[str, int]  # stream -> maximum age ns (bars include their cadence)
    max_future_skew_ns: int = 1_000_000_000
    report_max_age_ns: int = 10_000_000_000
    minimum_free_bytes: int = 1_073_741_824
    epoch: int = 0
    connected: bool = False
    writer_ok: bool = False
    catalog_verified: bool = False
    last: dict[str, tuple[int, int, int]] = field(default_factory=dict)
    event_ends: dict[str, int] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    duplicates: int = 0
    out_of_order: int = 0
    failures: set[str] = field(default_factory=set)
    first_observed_ns: int | None = None
    last_observed_ns: int | None = None

    def socket(self, connected: bool) -> None:
        if not connected:
            self.epoch += 1
            self.last.clear()
            self.event_ends.clear()
        self.connected = connected

    def observe(
        self,
        stream: str,
        *,
        ts_event: int,
        ts_init: int,
        now: int,
        event_end_ns: int | None = None,
    ) -> bool:
        if stream not in self.required:
            self.failures.add("UNKNOWN_INSTRUMENT_OR_STREAM")
            return False
        if (
            min(ts_event, ts_init, now) <= 0
            or max(ts_event, ts_init) > now + self.max_future_skew_ns
        ):
            self.failures.add("INVALID_EVENT_CLOCK")
            return False
        if event_end_ns is not None and not ts_event <= event_end_ns <= min(ts_init, now):
            self.failures.add("INVALID_EVENT_END_CLOCK")
            return False
        prior = self.last.get(stream)
        if prior and ts_event < prior[0]:
            self.out_of_order += 1
            self.failures.add("OUT_OF_ORDER_OR_GAP")
            return False
        if prior and (ts_event, ts_init) == prior[:2]:
            self.duplicates += 1
        self.last[stream] = (ts_event, ts_init, self.epoch)
        self.event_ends[stream] = ts_event if event_end_ns is None else event_end_ns
        self.counts[stream] = self.counts.get(stream, 0) + 1
        if self.first_observed_ns is None:
            self.first_observed_ns = now
        self.last_observed_ns = now
        return True

    def report(self, *, now: int, generated: int, free_bytes: int) -> dict[str, object]:
        reasons = set(self.failures)
        if not self.connected:
            reasons.add("NATIVE_DISCONNECTED")
        if not self.writer_ok:
            reasons.add("WRITER_UNKNOWN_OR_FAILED")
        if not self.catalog_verified:
            reasons.add("CATALOG_UNVERIFIED")
        if not 0 <= now - generated <= self.report_max_age_ns:
            reasons.add("HEALTH_REPORT_STALE_OR_CLOCK_INVALID")
        if free_bytes < self.minimum_free_bytes:
            reasons.add("DISK_LOW")
        for stream, max_age in self.required.items():
            event = self.last.get(stream)
            if event is None or event[2] != self.epoch:
                reasons.add(f"MISSING:{stream}")
            elif (
                not 0 <= now - self.event_ends[stream] <= max_age
                or not 0 <= now - event[1] <= max_age
            ):
                reasons.add(f"STALE:{stream}")
        return {
            "status": "HEALTHY" if not reasons else "DEGRADED",
            "reasons": sorted(reasons),
            "generated_ns": generated,
            "epoch": self.epoch,
            "counts": dict(self.counts),
            "duplicates": self.duplicates,
            "out_of_order": self.out_of_order,
        }
