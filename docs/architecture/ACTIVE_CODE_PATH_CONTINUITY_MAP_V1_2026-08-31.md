# Active Code Path and Continuity Map V1

**Effective date:** 2026-08-31  
**Scope:** Three Setup public-only shadow candidate and retained First Launch compatibility

This is a small navigation and change-amplification map, not a second architecture
authority. Product, Strategy, Operations, Security, and canonical engineering
governance remain controlling.

## Classifications

| Classification | Current paths/capability | Continuity rule |
| --- | --- | --- |
| `ACTIVE_CANONICAL` | `multi_asset_shadow` Registry, DataAuthority, Runtime, Bootstrap, ThreeSetupProductionApplication, Scanner, Strategy Kernel, Formal/Planning, Outcome, Evidence/Outbox; Three Setup entrypoint/systemd/config | Preserve one authority chain and exact release identity. New behavior uses existing composition seams. |
| `SHARED_COMPATIBILITY` | `runtime.first_launch_notification`, credential-file loading used by the Three Setup entrypoint, P4A deployment/backup helpers | Reuse is intentional. Separate shared capability behind a stable seam before deleting or renaming; do not assume the `first_launch` name means unused. |
| `LEGACY_READ_ONLY` | Historical First Launch durable records, schemas, replay/restore decoders, prior release evidence and accepted fixtures | Keep backward-readable/versioned. No new live authority is derived from legacy records unless a current migration contract says so. |
| `FUTURE_DEFERRED` | Private/account APIs, wallet/signing, exchange write/orders, autonomous trading, generalized host qualification, alternate provider/database/runtime, broader strategy families | Not active and not authorized by the Three Setup shadow path. |

## Stable authorities and interfaces

- `MarketRegistryManager` and version/content hash define the Registry epoch.
- `MultiAssetDataAuthority` plus `ClosedBarStore` own admitted provider-authoritative
  closed bars and causal history.
- `MultiAssetPublicRuntime` owns public transport/session/barrier lifecycle; it owns no
  Scanner/Strategy durable truth.
- `MultiAssetProductionBootstrap` binds runtime boundaries to Scanner, Strategy,
  Formal/Planning, Outcome, Evidence, and Outbox authorities.
- `ThreeSetupProductionApplication` is the production supervisor/composition entry,
  not a parallel runtime.
- Strategy input/output, Evidence immutable records, Outbox idempotency keys, Registry
  versions/content hashes, and release/config schemas are stable contract seams.

## Replaceable seams

- public transport/client behind `HyperliquidPublicClient`-compatible public methods;
- clock, sleep, notification delivery adapter, planning/public-data adapters;
- SQLite implementation behind the existing authoritative store APIs, only if a future
  separately accepted migration proves necessity;
- deterministic test providers and no-network notification sinks as consumers of the
  production composition.

Replacement of a provider or store must preserve authority and representation
contracts through a gradual stable-seam migration. It does not authorize a second live
authority during cutover.

## Durable representation versions

Preserve backward readability for Registry version/content hashes, closed-bar records,
Strategy continuation `REPRESENTATION_VERSION`, Evidence immutable record payloads,
Outcome/notification records, production config schema, and release/artifact manifests.
Semantic changes require an explicit version/migration decision; never reinterpret
retained bytes in place.

## Change-amplification triggers

- `multi_asset_shadow/integration.py` and `multi_asset_shadow/runtime.py` are current
  hotspots. Another unrelated responsibility triggers a bounded seam-extraction review
  before accretion; existing size alone does not trigger a split.
- A change spanning Registry + DataAuthority + Runtime + Evidence, or changing a durable
  representation, requires code-continuity review and production-composition coverage.
- A new provider, database, runtime, workflow/message framework, or deployment platform
  is a material route decision and `SAFE_STOP` boundary for a frozen Writer task.
- Repeated incident-specific guards around one state transition trigger the holistic
  convergence/global-responsibility gate.

## Known migration and lock-in risks

- fixed Python + venv + systemd + SQLite + single-process deployment is deliberate for
  the current scale; host paths are release policy, not business semantics;
- direct imports from `first_launch` are shared compatibility dependencies and must be
  classified/extracted before deletion;
- persisted Decimal/string/canonical-JSON forms and hash domains are compatibility
  boundaries;
- provider market identity and public payload normalization must remain at the adapter
  edge;
- no big-bang rewrite or file split solely for aesthetics. Use branch-by-abstraction
  style migration only when replacement is actually required.
