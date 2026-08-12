"""Versioned, atomic, locally managed market Registry.

The Registry is deliberately a filesystem control plane: no database service,
automatic discovery, or strategy-code edit is required to change the approved
universe.  A caller stages an approved version and applies it only at a closed
5m safe boundary.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from trader_assist_v0.contracts.common import canonical_json_bytes

from .models import MarketLifecycle, RegistryMarket, RegistryVersion

if TYPE_CHECKING:
    from .data import Closed5mAdmission


class RegistryError(ValueError):
    pass


MetadataValidator = Callable[[RegistryMarket], bool]

_LIFECYCLE_NEXT: dict[MarketLifecycle, frozenset[MarketLifecycle]] = {
    MarketLifecycle.WARMING: frozenset({MarketLifecycle.HISTORY_READY, MarketLifecycle.DISABLED}),
    MarketLifecycle.HISTORY_READY: frozenset(
        {MarketLifecycle.SNAPSHOT_READY, MarketLifecycle.DISABLED}
    ),
    MarketLifecycle.SNAPSHOT_READY: frozenset({MarketLifecycle.ACTIVE, MarketLifecycle.DISABLED}),
    MarketLifecycle.ACTIVE: frozenset({MarketLifecycle.DRAINING}),
    MarketLifecycle.DRAINING: frozenset({MarketLifecycle.OUTCOMES_COMPLETE}),
    MarketLifecycle.OUTCOMES_COMPLETE: frozenset({MarketLifecycle.DISABLED}),
    # Re-enabling never resurrects an ACTIVE market; it restarts readiness.
    MarketLifecycle.DISABLED: frozenset({MarketLifecycle.WARMING}),
}


def _write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


class MarketRegistryManager:
    def __init__(self, root: Path, *, metadata_validator: MetadataValidator) -> None:
        self.root = root
        self._metadata_validator = metadata_validator
        self.versions = root / "versions"
        self.validations = root / "validations"
        self.pointer = root / "current.json"
        self.pending = root / "pending.json"
        self.history = root / "history"
        # Capability identity is intentionally process-local.  A Registry
        # operation never accepts a generic candle as time authority.
        self._boundary_issuer = object()

    def _decode(self, raw: bytes) -> RegistryVersion:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RegistryError("registry is not valid JSON") from exc
        if canonical_json_bytes(parsed) != raw:
            raise RegistryError("registry JSON must be canonical")
        try:
            return RegistryVersion.model_validate(parsed)
        except ValueError as exc:
            raise RegistryError("registry schema validation failed") from exc

    def load_version(self, version: str) -> RegistryVersion:
        path = self.versions / f"{version}.json"
        try:
            return self._decode(path.read_bytes())
        except FileNotFoundError as exc:
            raise RegistryError("registry version does not exist") from exc

    def active(self) -> RegistryVersion | None:
        if not self.pointer.exists():
            return None
        try:
            pointer = json.loads(self.pointer.read_text(encoding="utf-8"))
            version = pointer["version"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise RegistryError("current registry pointer is invalid") from exc
        if type(version) is not str:
            raise RegistryError("current registry pointer is invalid")
        if pointer.get("content_hash") is None or type(pointer["content_hash"]) is not str:
            raise RegistryError("current registry pointer is invalid")
        active = self.load_version(version)
        if pointer["content_hash"] != active.content_hash:
            raise RegistryError("current registry pointer content_hash does not match version")
        return active

    def validate(self, candidate: RegistryVersion) -> None:
        if candidate.schema_version != "1":
            raise RegistryError("unsupported registry schema")
        try:
            for market in candidate.markets:
                if not self._metadata_validator(market):
                    raise RegistryError(f"REGISTRY_IDENTITY_UNRESOLVED: {market.display}")
        except RegistryError:
            raise
        except Exception as exc:
            raise RegistryError("REGISTRY_METADATA_VALIDATION_UNAVAILABLE") from exc

    def _validation_path(self, version: str) -> Path:
        return self.validations / f"{version}.json"

    def _assert_prior_validation(self, candidate: RegistryVersion) -> None:
        try:
            evidence = json.loads(
                self._validation_path(candidate.version).read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            raise RegistryError("registry version has no validated metadata evidence") from exc
        if evidence != {"version": candidate.version, "content_hash": candidate.content_hash}:
            raise RegistryError("registry validation evidence does not bind version contents")

    def stage(self, candidate: RegistryVersion) -> Path:
        self.validate(candidate)
        target = self.versions / f"{candidate.version}.json"
        encoded = canonical_json_bytes(candidate.model_dump(mode="json"))
        if target.exists() and target.read_bytes() != encoded:
            raise RegistryError("immutable registry version already exists with different content")
        if not target.exists():
            _write_atomic(target, encoded)
        _write_atomic(
            self._validation_path(candidate.version),
            canonical_json_bytes(
                {"version": candidate.version, "content_hash": candidate.content_hash}
            ),
        )
        return target

    def request_apply(self, version: str) -> RegistryVersion:
        """Validate a staged version without manufacturing a time boundary."""
        candidate = self.load_version(version)
        self._assert_prior_validation(candidate)
        _write_atomic(
            self.pending,
            canonical_json_bytes(
                {"version": candidate.version, "content_hash": candidate.content_hash}
            ),
        )
        return candidate

    def pending_version(self) -> RegistryVersion | None:
        if not self.pending.exists():
            return None
        try:
            pending = json.loads(self.pending.read_text(encoding="utf-8"))
            version, content_hash = pending["version"], pending["content_hash"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise RegistryError("pending registry pointer is invalid") from exc
        candidate = self.load_version(version)
        if content_hash != candidate.content_hash:
            raise RegistryError("pending registry pointer content_hash does not match version")
        self._assert_prior_validation(candidate)
        return candidate

    def _apply_admitted(self, admission: Closed5mAdmission) -> RegistryVersion | None:
        """Consume one provider-issued boundary capability exactly once.

        This deliberately has no ``ClosedBar`` parameter and no public
        counterpart.  The data authority verifies provider finality and calls
        it through this narrow capability seam.
        """
        issuer = getattr(admission, "_issuer", None)
        if (
            issuer is not self._boundary_issuer
            or not getattr(admission, "_consume", lambda: False)()
        ):
            raise RegistryError(
                "registry activation requires provider admitted boundary capability"
            )
        candidate = self.pending_version()
        if candidate is None:
            return None
        prior = self.active()
        prior_pointer = self.pointer.read_bytes() if self.pointer.exists() else None
        pointer = {"version": candidate.version, "content_hash": candidate.content_hash}
        _write_atomic(self.pointer, canonical_json_bytes(pointer))
        if prior is not None and prior_pointer is not None:
            stamp = admission.bar.received_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
            _write_atomic(self.history / f"{stamp}-{prior.version}.json", prior_pointer)
        try:
            self.pending.unlink()
        except FileNotFoundError:
            pass
        return candidate

    def rollback_request(self, version: str) -> RegistryVersion:
        return self.request_apply(version)

    def lifecycle_update(
        self, version: str, market_id: str, lifecycle: MarketLifecycle, *, now: datetime
    ) -> RegistryVersion:
        """Create an immutable lifecycle-only successor; events are not expired here."""
        active = self.active()
        if active is None:
            raise RegistryError("no active registry")
        if self.versions.joinpath(f"{version}.json").exists():
            raise RegistryError("new lifecycle version already exists")
        found = False
        markets: list[RegistryMarket] = []
        for market in active.markets:
            if market.identity.market_id == market_id:
                found = True
                if lifecycle not in _LIFECYCLE_NEXT[market.lifecycle]:
                    raise RegistryError(
                        "illegal market lifecycle transition: "
                        f"{market.lifecycle.value} -> {lifecycle.value}"
                    )
                markets.append(market.model_copy(update={"lifecycle": lifecycle}))
            else:
                markets.append(market)
        if not found:
            raise RegistryError("market is not in active registry")
        candidate = RegistryVersion.create(version=version, created_at=now, markets=tuple(markets))
        self.stage(candidate)
        return candidate

    def successor(
        self,
        *,
        version: str,
        now: datetime,
        update_market: RegistryMarket | None = None,
        remove_market_id: str | None = None,
    ) -> RegistryVersion:
        """Stage a deterministic add/replace/remove successor without activation."""
        active = self.active()
        if active is None:
            raise RegistryError("no active registry")
        if self.versions.joinpath(f"{version}.json").exists():
            raise RegistryError("new registry version already exists")
        markets = list(active.markets)
        if remove_market_id is not None:
            markets = [m for m in markets if m.identity.market_id != remove_market_id]
        if update_market is not None:
            existing = next(
                (
                    index
                    for index, item in enumerate(markets)
                    if item.identity.market_id == update_market.identity.market_id
                ),
                None,
            )
            if existing is None:
                markets.append(update_market)
            else:
                markets[existing] = update_market
        candidate = RegistryVersion.create(version=version, created_at=now, markets=tuple(markets))
        self.stage(candidate)
        return candidate
