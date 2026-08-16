# Engineering Continuity and Scale / Provider Budget Gate V1

Effective: 2026-08-16

## Purpose

Prevent a bounded implementation that is locally correct from becoming an operational blocker when the real target workload, provider limits, or future system growth are applied.

This rule complements the mandatory research / evidence / decision method. It does not grant deployment, runtime, account, signing, exchange-write, or merge authority.

## 1. Continuity-first technical route rule

Every material technical route, architecture choice, provider integration, persistence design, runtime workflow, and performance repair must preserve an explicit continuation path into the next expected development stages.

A route must not be selected solely because it is the smallest implementation for the current host or current launch size if it predictably creates a near-term rewrite, incompatible authority model, hard-coded scale ceiling, or avoidable migration burden.

Before acceptance, state:

- the current bounded need;
- the next expected scale or capability step;
- which interfaces / contracts / authorities remain stable;
- which values are tuning parameters rather than architectural constants;
- what future change would require redesign rather than retuning;
- known migration or lock-in risk.

Prefer solutions whose current implementation is small while the interface and authority model remain reusable at larger scale. Do not overbuild speculative future functionality; continuity means a safe extension path, not premature generalization.

## 2. Scale and Provider Budget Gate

Before first deployment, or before changing any material workload dimension, perform a lightweight scale / provider budget calculation and a realistic-size acceptance test.

This gate is mandatory when materially changing one or more of:

- market / instrument count;
- historical warmup depth;
- polling or scan cadence;
- REST / WebSocket request rate;
- provider or endpoint;
- confirmation / retry count;
- concurrency;
- database write or read volume;
- runtime cohort size;
- notification / evidence throughput.

At minimum calculate:

`market_count × calls_per_market × provider_weight × cadence`

and, where relevant:

`market_count × history_points × database_operations`

Also estimate / measure:

- provider headroom after normal traffic and retry margin;
- expected worst-case freshness / completion latency;
- memory, CPU and database-operation order of magnitude;
- shutdown / cancellation responsiveness under the target workload.

The calculation should normally take minutes, not become a large project. Use a short worksheet, test fixture, or issue comment unless the workload genuinely requires a maintained tool.

## 3. Trading freshness gate

For trading or scanner data, target-scale qualification must prove that authoritative data reaches the decision layer within the product's explicit freshness SLA. A larger universe is not an improvement if provider limits or processing latency make the resulting information stale for the intended trading cadence.

Any material Universe-size change requires renewed Provider Budget + Freshness qualification before release. Universe size is a tunable product/operations parameter, not an assumed permanent constant.

## 4. Realistic-scale acceptance rule

Unit correctness at one market or a small fixture is insufficient when the production workload is materially larger.

Before accepting the route, include at least one deterministic or bounded real-host test at the intended order of magnitude. The test must exercise the actual bottleneck class when feasible: provider request budget, historical ingestion, persistence transactions, cohort convergence, event-loop responsiveness, or equivalent.

## 5. Lessons from Three Setup cold-start incident

The 2026-08-16 Three Setup qualification exposed a route that was authority-correct at small scale but operationally pathological at Fixed-40 × 2304 5m bars: repeated full-history deserialization, per-row SQLite commits, moving warmup currentness, and event-loop starvation prevented timely startup and bounded shutdown.

The lesson is not to weaken authority. The lesson is to add scale, provider-budget, freshness, and shutdown criteria alongside authority correctness before real deployment.

The repair direction remains: reuse mature bounded patterns (provider-aware rate limiting, bounded concurrency, single authority writer, bounded SQLite transactions, rolling aggregation windows, cohort/watermark currentness, cooperative yielding) while preserving existing Registry, Closed5mAdmission, readiness, StrategyEvaluation, Formal, and ShadowOrder authority.
