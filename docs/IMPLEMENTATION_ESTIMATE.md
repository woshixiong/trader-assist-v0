# Gate-Driven Implementation Estimate

These are effort and model-budget ranges, not promised calendar dates. Re-estimate at every gate using observed code, tests, data-source access, and review findings.

| Slice | Focus | Engineering work units | AI token planning range |
|---|---|---:|---:|
| V0-00 | repository, contracts, CI, provenance | 3–5 focused units | 0.4–0.9M Flash-equivalent + 0.1–0.3M high-reasoning review |
| V0-01 | read-only feeds, storage, health, replay | 6–10 units | 1.0–2.5M Flash-equivalent + 0.3–0.7M high-reasoning review |
| V0-02 | features/regime plus first two candidates | 6–12 units | 1.2–3.0M Flash-equivalent + 0.4–0.9M strategy review |
| V0-03 | AI explanation, proposal diff, human journal | 5–9 units | 0.9–2.0M Flash-equivalent + 0.2–0.6M high-reasoning review |
| V0-04 | Testnet gateway and reconciliation | 8–14 units | 1.5–3.5M implementation + 0.8–1.5M independent T0 review |
| V0-05 | conditional Mainnet pilot controls | evidence-driven | separately authorized; no automatic budget |

One work unit means one bounded implementation/review session with exact acceptance tests; it is not a calendar day.

Cash cost is not frozen here because API pricing, context size, AWS region, storage volume, and vendor selection are changeable. Every execution window must set a token cap and report actual usage. No cost overrun may weaken tests, review, or safety gates.
