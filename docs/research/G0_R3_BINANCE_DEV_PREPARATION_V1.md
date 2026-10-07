# G0 R3 Binance DEV preparation — synthetic-only Route B

**Package:** G0_R3_BINANCE_DEV_PREPARATION_CHATGPT_1. **Status:** candidate; independent Final Review required. This document is not an external rights approval, a market-data acquisition authorization, a trading claim, or a Strategy change.

Canonical authority: AGENTS.md → active manifest → V5 sole constitution → Issue #161 package-state comment 6029552891 → Control Plan V2 comment 6029545086 → Pre-code PASS comment 6029681710. Historic numeric G0 freeze: Issue #161 comments 6017065560 and 6017243748 (daily correction). All code is restricted to the frozen five paths.

## Original immutable allocation

The source-identity generator retains exactly 256 Binance Vision USD-M Futures 5m archive objects for BTCUSDT, ETHUSDT, SOLUSDT and XRPUSDT:

| Original intent | Window (UTC, half-open) | Physical identity | Count | Real rights state |
| --- | --- | --- | --- | --- |
| CURRENT_DEV | 2024-01-01 – 2024-03-01 | daily ZIP (Jan–Feb) | 240 | UNKNOWN / not executable |
| FUTURE_DEV_RESERVE | 2024-03-01 – 2024-05-01 | monthly ZIP | 8 | UNKNOWN / sealed |
| CERTIFICATION_RESERVE | 2024-05-01 – 2024-07-01 | monthly ZIP | 8 | UNKNOWN / sealed |

Daily source path: data/futures/um/daily/klines/{SYMBOL}/5m/{SYMBOL}-5m-{YYYY-MM-DD}.zip. Monthly reserve path: data/futures/um/monthly/klines/{SYMBOL}/5m/{SYMBOL}-5m-{YYYY-MM}.zip. Exact fixed host: https://data.binance.vision. The checksum identity is precisely the corresponding ZIP URL plus .CHECKSUM.

The in-memory immutable source ledger records intended role independently of *operative* R2B role. No absent SHA-256 receipt is filled with a dummy checksum or record hash. A checksum-bound row can be constructed as a DatasetManifest with 27 explicit metadata keys, unchanged rights=None/non-ALLOWED and exposure=UNSEEN_SEALED; its operative AllocationItem.role is always METADATA_ONLY_EXCLUDED, state UNKNOWN and explicit restrictions. Such rows are never executable. The ledger preserves all 256 source objects even when only a subset has CHECKSUM receipts. A metadata-only manifest/hash is never a substitute for a future rights-approved one.

The underlying R2B inventory builder remains unchanged: CURRENT_DEV/FUTURE_DEV_RESERVE/CERTIFICATION_RESERVE effective roles require ALLOWED rights. No source public availability proves rights. Neither receipt acquisition nor exact source identity upgrades rights or unseals monthly reserves.

## Data-source terms and production prohibition

Provider documentation: binance/binance-public-data official README, python/enums.py, TERMS_AND_CONDITIONS.md. Official terms observed in Pre-code Review: 2026-08-26 v1.0, CC BY-NC-SA 4.0; non-commercial/non-production research may be eligible subject to independent review of actual user/use/attribution/retention. Publicly readable ZIP does **not** grant commercial, proprietary live trading or derivative redistribution rights. This package takes no position that real data rights are ALLOWED, performs no real URL request or real CSV/ZIP download in implementation tests, and has **no built-in HTTP client** or default opener.

Future real DEV access is separate Control scope: verify the full official terms/version/hash, intended-use eligibility, conditions, decision and attribution; rebind 240 DEV plus 16 sealed reserve dataset/rights/mapping/hash identities; attach exactly authorized preregistration and issue authority; do not reuse metadata-only hashes, reclassify reserve outcomes, or access a reserved ZIP without a separately frozen pre-outcome allocation.

## Provider parser and transport invariants

The provider file owns only pure frozen identities, checksum parsing, injected HTTP-response shape validation and ZIP/CSV verification. An explicit caller injects synthetic fixture bytes, not an implicit network requester. Provider mode is USD-M Futures, 2024 UTC milliseconds, finalized 5m bars. The official file schema is **headerless**, exactly twelve positional columns:

open_time, open, high, low, close, volume, close_time, quote_volume, count, taker_buy_volume, taker_buy_quote_volume, ignore.

Any header, aliases, BOM, hidden quote, empty/malformed line, extra field, nonnumeric or exponent/NaN/Infinity rejects; the nonnegative finite numeric ignore field may be nonzero. Open, high, low and close are positive; volumes are nonnegative and taker volumes cannot exceed total volumes; trade count is nonnegative integer. The close time must be open_ms + 300000 - 1. A daily file must contain 288 unique ordered and gap-free bars across exactly the expected UTC day. No guessed microsecond timestamps.

A single CHECKSUM line is validated against exact ZIP basename with ASCII SHA-256 and optional terminal line ending; SHA-256 is checked **before ZIP parsing**. Fixed injected-response URL/status, no redirects, no alternate hosts, no encoded response and bounded content length. ZIP bytes <= 1,000,000; CSV bytes <= 1,000,000; row line <= 2,048; numeric field <= 80; one exact ZIP CSV member; no traversal, symlink, encrypted member, archive extra, duplicate member, unsafe compression/ratio, CRC mismatch or output extraction. This is a deliberately narrow parser; if the actual provider CSV does not conform, it requires Engineering Control format replan, not a permissive parser downgrade.

Next-day archive availability and later provider corrections differ from historical network receive/finality facts. Retrieval proof is retrospective source evidence only. Synthetic replay records keep original bar start as ts_event, end-exclusive 5m interval and timestamp provenance source_unit=ms. Their observed_at_ns and evaluated_at_ns are the fixture receipt retrieval time, **never backdated to 2024 bar-close**. true_network_receive_ts=None and receive_provenance=NOT_EXPOSED. Any bar-close decision clock is an explicitly offline reconstruction, not a contemporaneously received PIT signal.

## Synthetic DEV integration

research_replay/dev_archive.py is the only new composition/write layer. It rejects a non-concrete admission, missing or non-ALLOWED rights, non-synthetic flag, non-SYNTHETIC_ENGINEERING prereg, mismatched dataset/checksum/cut/strategy/mapping, absent exact DevAccessAuthority, non-operative inventory role, reserve object/hash, visibility and adapter mismatches **before any opener, ZIP, output-root or sidecar I/O**. The existing DevExternalAdmission and DevAccessAuthority guard remains the decision owner; the new code adds a hard real-data denial even for self-declared real ALLOWED rights. The only admitted capability is FREE_REFERENCE_IMPORT / FREE_FILE with an explicitly synthetic proof and mapping. No live Binance adapter, production mapping or Nautilus adapter claim is made.

One synthetic daily ZIP -> one R3 DatasetManifest -> one ExternalReferenceLedger (288 observations) -> the existing EvidenceSidecar(version="1") canonical JSON wire -> one local {record_hash}.reference.json -> existing read_external_dev verified roundtrip. The adapter does not change ReferenceDatasetStore.write or pipeline-only authorization. source_bytes_hex=() and catalog_files=(); raw ZIP/CSV and even the local normalized sidecar are not GitHub artifacts. The actual byte bound is min(DevVisibilityPolicy.max_bytes, 4,000,000), with a further synthetic envelope ceiling 4096 + 288*8192 = 2,363,392 bytes; violations occur before output root resolution/write.

All synthetic tests inject artificial generated 288-row CSVs/ZIPs and fake HTTP responses. Negative tests cover original 256 role identities, nonexistent checksum, UNKNOWN/PROHIBITED rights, forged real ALLOWED, R2B role upgrade, wrong prereg/strategy/hash, reserve opener sentinel, checksum-before-ZIP, malicious ZIPs/headers, malformed 5m sequence, nonzero ignored fields, late receipt, visibility size and tamper, existing DEV reader roundtrip, and maximum length accepted fields. No real market payload, live credentials or exchange orders are required.

## Preserved G0 experiment and gates

No change to original Three Setup frozen candidate order (Champion + four simpler baselines), complexity 2/1/1/1/1, five material trials and one bounded causal repair, 8-day warmup with Jan 9 decision start, 4h outcome, 1h expiry, 30s delay, next-open stop-first, Donchian 20, synthetic fees/friction/cost profile, 10 mandatory cells, 12 independent MarketEvents + 4 clusters per cell, paired incremental-R/simpler-on-equivalence, 0.05R tolerance, 0.10R nonsimpler threshold, drawdown/tail/concentration/coverage/unavailable/cost gates, holdout and sequential exposure rules. 69,120 is *nominal input bar count*, not a sufficiency claim or independent events. R4/R5, exchange write, real execution, Strategy/Replay changes and promotion remain prohibited. Claim: MECHANISM_VALIDATION; venue economics: SYNTHETIC_VENUE_OVERLAY; promotion: PROHIBITED.

## Validation and release boundary

Focused synthetic tests: tests/test_research_data_binance_archive.py and tests/test_research_replay_dev_archive.py; verify on configured locked exact-head GitHub CI. Normal required CI includes Contracts, Nautilus Pilot, Nautilus G4 and E4 Capture where configured on exact head. This text does not claim those checks passed. Independent Final Review must evaluate all five changed files and verify exact HEAD/TREE/required checks. Mark Ready, merge, deployment and any real market activity require separate current human authorization.
