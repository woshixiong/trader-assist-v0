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
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from trader_assist_v0.contracts.common import canonical_json_bytes

from .models import MarketLifecycle, RegistryMarket, RegistryVersion

if TYPE_CHECKING:
    from .data import Closed5mAdmission, MultiAssetDataAuthority


class RegistryError(ValueError):
    """Registry control-plane integrity failure."""


@dataclass(frozen=True)
class CohortWitness:
    """Process-local, one-use capability authorizing exactly one successor apply.

    Binds the boundary, the exact base Registry epoch, the exact expected
    successor, the required evidence cohort, and the issuer.  Application
    re-reads live active/pending state and requires exact equality before any
    durable transition, so a witness minted for one candidate can never apply
    another.  The consumed flag is process-local capability state, not durable
    Registry authority.
    """

    boundary_open_time_ms: int
    base_registry_version: str
    base_registry_hash: str
    expected_successor_version: str
    expected_successor_hash: str
    required_evidence_market_ids: frozenset[str]
    issuer: str
    _consumed: bool = field(default=False, repr=False, compare=False)

    @classmethod
    def create(
        cls,
        *,
        boundary_open_time_ms: int,
        base_registry_version: str,
        base_registry_hash: str,
        expected_successor_version: str,
        expected_successor_hash: str,
        required_evidence_market_ids: frozenset[str],
        issuer: str,
    ) -> CohortWitness:
        if (
            not isinstance(boundary_open_time_ms, int)
            or boundary_open_time_ms < 0
            or boundary_open_time_ms % 300_000 != 0
        ):
            raise RegistryError("witness boundary must be an aligned 5m open")
        for name, value in (
            ("base_registry_version", base_registry_version),
            ("base_registry_hash", base_registry_hash),
            ("expected_successor_version", expected_successor_version),
            ("expected_successor_hash", expected_successor_hash),
        ):
            if not isinstance(value, str) or not value:
                raise RegistryError(f"witness {name} is required")
        if not isinstance(required_evidence_market_ids, frozenset) or any(
            not isinstance(item, str) or not item for item in required_evidence_market_ids
        ):
            raise RegistryError("witness evidence cohort must be market id strings")
        if not isinstance(issuer, str) or not issuer:
            raise RegistryError("witness issuer is required")
        return cls(
            boundary_open_time_ms=boundary_open_time_ms,
            base_registry_version=base_registry_version,
            base_registry_hash=base_registry_hash,
            expected_successor_version=expected_successor_version,
            expected_successor_hash=expected_successor_hash,
            required_evidence_market_ids=frozenset(required_evidence_market_ids),
            issuer=issuer,
        )


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

    def reconcile_pending(self) -> RegistryVersion | None:
        """Explicit single-owner crash-convergence for a stale pending pointer.

        Crash-after-pointer-switch/before-pending-cleanup leaves
        ``active == pending``: recognize it as already applied, clean the stale
        pointer idempotently, and report no pending proposal.  A read accessor
        (:meth:`pending_version`) never performs this mutation; only the Cohort
        Barrier's explicit reconciliation does.  No second transition, no new
        history record, no alternate candidate.
        """
        candidate = self.pending_version()
        if candidate is None:
            return None
        active = self.active()
        if (
            active is not None
            and active.version == candidate.version
            and active.content_hash == candidate.content_hash
        ):
            try:
                self.pending.unlink()
            except FileNotFoundError:
                pass
            return None
        return candidate

    def prior_active(self, version: str) -> RegistryVersion | None:
        """Load one version only if it was an actually superseded active epoch.

        A merely staged/validated candidate that was never the live authority
        is NOT a predecessor epoch.  Proof comes from the existing immutable
        history record format, not a new lineage store.
        """
        if self._prior_history_record(version) is None:
            return None
        return self.load_version(version)

    def _prior_history_record(self, version: str) -> Path | None:
        """Exact ``{stamp}-{version}.json`` history record for one version."""
        if not self.history.exists():
            return None
        suffix = f"-{version}.json"
        for path in self.history.glob("*.json"):
            if len(path.name) > 17 and path.name[16] == "-" and path.name[16:] == suffix:
                return path
        return None

    def apply_witness(
        self,
        witness: CohortWitness,
        *,
        evidence_authority: MultiAssetDataAuthority,
    ) -> RegistryVersion:
        """Activate exactly the successor bound by one one-use cohort witness.

        Re-reads live active and pending Registry state immediately before any
        durable transition and requires exact equality with the witness
        binding, then proves the required evidence cohort through the
        provider-authoritative Data authority itself.  The Registry never
        trusts an arbitrary caller-supplied proof callback: evidence proof is
        owned by :class:`MultiAssetDataAuthority` (packet section 4A).  The
        ``issuer`` string is diagnostic text only; real authority is the
        process-local one-use witness binding plus live state equality plus
        authority-owned evidence.  Transition order is the crash-convergent
        existing-format sequence: prior history record, atomic pointer switch,
        pending cleanup.  Any mismatch fails closed with no mutation.
        """
        from .data import MultiAssetDataAuthority

        if witness._consumed:
            raise RegistryError("cohort witness was already consumed")
        object.__setattr__(witness, "_consumed", True)
        if not isinstance(evidence_authority, MultiAssetDataAuthority):
            raise RegistryError(
                "cohort witness evidence must be proven by the Data authority"
            )
        if not witness.required_evidence_market_ids:
            raise RegistryError("cohort witness requires a non-empty evidence cohort")
        active = self.active()
        if active is None:
            raise RegistryError("cohort witness apply requires an active Registry")
        pending = self.pending_version()
        if pending is None:
            raise RegistryError("cohort witness apply requires the expected pending successor")
        if (
            active.version != witness.base_registry_version
            or active.content_hash != witness.base_registry_hash
        ):
            raise RegistryError("witness base Registry epoch does not match live active")
        if (
            pending.version != witness.expected_successor_version
            or pending.content_hash != witness.expected_successor_hash
        ):
            raise RegistryError("witness expected successor does not match live pending")
        try:
            proven = bool(
                evidence_authority.prove_boundary_evidence(
                    boundary_open_time_ms=witness.boundary_open_time_ms,
                    market_ids=witness.required_evidence_market_ids,
                    base_registry_version=witness.base_registry_version,
                    base_registry_hash=witness.base_registry_hash,
                )
            )
        except RegistryError:
            raise
        except Exception as exc:
            raise RegistryError("cohort witness evidence proof failed") from exc
        if not proven:
            raise RegistryError("cohort witness evidence cohort is not proven at boundary")
        prior_pointer = self.pointer.read_bytes()
        stamp = datetime.fromtimestamp(witness.boundary_open_time_ms / 1000, UTC).strftime(
            "%Y%m%dT%H%M%SZ"
        )
        record = self.history / f"{stamp}-{active.version}.json"
        existing = self._prior_history_record(active.version)
        if existing is None:
            _write_atomic(record, prior_pointer)
        elif existing.read_bytes() != prior_pointer:
            raise RegistryError("prior Registry history record conflicts with live pointer")
        _write_atomic(
            self.pointer,
            canonical_json_bytes(
                {"version": pending.version, "content_hash": pending.content_hash}
            ),
        )
        try:
            self.pending.unlink()
        except FileNotFoundError:
            pass
        return pending

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

    def lifecycle_successor(
        self,
        *,
        version: str,
        updates: dict[str, MarketLifecycle],
        now: datetime,
    ) -> RegistryVersion:
        """Stage one batched, one-step lifecycle successor.

        A lifecycle change is still activated only by the opaque admitted-bar
        capability.  Batching avoids one Registry version per healthy market.
        """
        active = self.active()
        if active is None:
            raise RegistryError("no active registry")
        if self.versions.joinpath(f"{version}.json").exists():
            raise RegistryError("new lifecycle version already exists")
        unknown = set(updates)
        markets: list[RegistryMarket] = []
        for market in active.markets:
            lifecycle = updates.get(market.identity.market_id)
            if lifecycle is None:
                markets.append(market)
                continue
            unknown.discard(market.identity.market_id)
            if lifecycle not in _LIFECYCLE_NEXT[market.lifecycle]:
                raise RegistryError(
                    "illegal market lifecycle transition: "
                    f"{market.lifecycle.value} -> {lifecycle.value}"
                )
            markets.append(market.model_copy(update={"lifecycle": lifecycle}))
        if unknown:
            raise RegistryError("market is not in active registry")
        candidate = RegistryVersion.create(version=version, created_at=now, markets=tuple(markets))
        self.stage(candidate)
        return candidate

    def add_new(self, *, version: str, now: datetime, market: RegistryMarket) -> RegistryVersion:
        """Stage a validated new identity, always from WARMING."""
        active = self.active()
        if active is None:
            raise RegistryError("no active registry")
        if any(item.identity.market_id == market.identity.market_id for item in active.markets):
            raise RegistryError("ADD requires a new canonical market identity")
        warming = market.model_copy(update={"lifecycle": MarketLifecycle.WARMING})
        return self.successor(version=version, now=now, update_market=warming)

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
