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

from trader_assist_v0.contracts.common import canonical_json_bytes

from .models import MarketLifecycle, RegistryMarket, RegistryVersion


class RegistryError(ValueError):
    pass


MetadataValidator = Callable[[RegistryMarket], bool]


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
        self.pointer = root / "current.json"
        self.history = root / "history"

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
        return self.load_version(version)

    def validate(self, candidate: RegistryVersion) -> None:
        if candidate.schema_version != "1":
            raise RegistryError("unsupported registry schema")
        for market in candidate.markets:
            if not self._metadata_validator(market):
                raise RegistryError(f"official metadata validation failed for {market.display}")

    def stage(self, candidate: RegistryVersion) -> Path:
        self.validate(candidate)
        target = self.versions / f"{candidate.version}.json"
        encoded = canonical_json_bytes(candidate.model_dump(mode="json"))
        if target.exists() and target.read_bytes() != encoded:
            raise RegistryError("immutable registry version already exists with different content")
        if not target.exists():
            _write_atomic(target, encoded)
        return target

    @staticmethod
    def is_safe_boundary(now: datetime) -> bool:
        if now.tzinfo is None:
            raise RegistryError("safe-boundary timestamp must be timezone-aware")
        instant = now.astimezone(UTC)
        return instant.second == 0 and instant.microsecond == 0 and instant.minute % 5 == 0

    def apply(self, version: str, *, now: datetime) -> RegistryVersion:
        if not self.is_safe_boundary(now):
            raise RegistryError("registry activation is permitted only at a closed 5m boundary")
        candidate = self.load_version(version)
        self.validate(candidate)
        prior = self.active()
        prior_pointer = self.pointer.read_bytes() if self.pointer.exists() else None
        pointer = {"version": candidate.version, "content_hash": candidate.content_hash}
        _write_atomic(self.pointer, canonical_json_bytes(pointer))
        if prior is not None and prior_pointer is not None:
            stamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
            _write_atomic(self.history / f"{stamp}-{prior.version}.json", prior_pointer)
        return candidate

    def rollback(self, version: str, *, now: datetime) -> RegistryVersion:
        return self.apply(version, now=now)

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
                markets.append(market.model_copy(update={"lifecycle": lifecycle}))
            else:
                markets.append(market)
        if not found:
            raise RegistryError("market is not in active registry")
        candidate = RegistryVersion.create(version=version, created_at=now, markets=tuple(markets))
        self.stage(candidate)
        return candidate
