# SOURCE_EVIDENCE_LEDGER — Ryan Brown / AlgoLee — 2026-10-16

**Research identity:** `SOFT_MARTINGALE_BOUNDED_GRID_V0_1`. **Source coverage is partial and explicitly typed.** This document is not an archive of copyrighted video subtitles. It indexes source locations and limited paraphrased findings.

## Identification

1. Screenshot channel **Ryan Brown (ResponsibleForexTrading)**: https://www.youtube.com/@ResponsibleForexTrading — channel ID `UCIZpqvFv_B9ktXvEzhaeELQ`. A third-party channel-stat snapshot counted ~486 uploaded videos (July/Aug 2026). A channel upload list/keyword search was queried, **not a transcript reading of all 486 videos**.
2. Supplied URL **AlgoLee / 和AlgoLee一起交易**: https://youtu.be/W5B_TP6Res8 — channel ID `UCORA1o1m0qVRCjqhcxKIK_A`; 2026-10-15, 9m40s, video title **全网说的爆仓神器，我却跑了好几年，月化2%~5%**. **Different channel**, not Ryan Brown.

## Evidence status glossary

`FULL_CAPTIONS_READ`: retrieved full available captions, not necessarily visual replay.  
`METADATA_AND_DESCRIPTION`: title, description, chapters and/or channel list only.  
`WEBSITE_FIRST_PARTY_CLAIM`: vendor page; commercial and self-reported evidence.  
`THIRD_PARTY_UNVERIFIED`: article or tracker linked but raw trade ledger not audited.  
`NOT_READ`: unresolved, do not derive parameter claims.

| Source | Link | Evidence status | Key documented value / caveat |
|---|---|---|---|
| AlgoLee: 爆仓神器/2–5% monthly | https://youtu.be/W5B_TP6Res8 | **FULL_CAPTIONS_READ (English captions)** | 1.1/1.3/1.5 slower progression; step-size/regime selection; equity stop; “30%” example; purported 2–5% monthly/99% recovery **unverified**. Chinese original/visual account history not independently checked. |
| Ryan: Martingale Grid Trading: Is it Dangerous? | https://www.youtube.com/watch?v=Wbi9Knt5Yrk | **FULL_CAPTIONS_READ** | 2022 Ranger example: 1.5 multiplier after third trade; GBP/CAD Ranger example no progressive multiplier; basket-level averaging/exit; 2006-onward backtest **author claim**. |
| Ryan: I Can Prove Martingale Grid Trading Works | https://www.youtube.com/watch?v=vnK0TYp-XGA | **METADATA_AND_DESCRIPTION / FULL TRANSCRIPT NOT READ** | 2026-08-16 promotional 20-year-data/Northstar AUDCAD argument; video-specific claims must be checked later. |
| Ryan: GRID TRADING - How to Use it & Why it's Effective | https://www.youtube.com/watch?v=md7-7CSbOcA | **METADATA_AND_DESCRIPTION ONLY** | 2021 tutorial, deferred deeper reading. |
| Ryan: How I Profit 24% Every Year with a Grid Trading Robot | https://www.youtube.com/watch?v=01mALraoxek | **METADATA_AND_DESCRIPTION ONLY** | 2025 vendor performance claim, not independently established. |
| Ryan: My Perfect Trading Bot Doesn't Exist / Loss Story | https://www.youtube.com/watch?v=OPGCLTwUkLI | **METADATA ONLY** | Examine loss period counterexamples before trusting survivorship. |
| Ryan: Lost 25% and recovery | https://www.youtube.com/watch?v=CkW3xfh_VNc | **METADATA ONLY** | Potential drawdown counterexample; do not assume cause without transcript. |
| Ryan: 2574 Trades, 85% Win Rate | https://www.youtube.com/watch?v=FfdWbJZ376w | **METADATA_AND_DESCRIPTION** | Refers to Vigorous AI layered technical/news filters; **not** identical to martingale-grid. |
| Ryan: 90% of AI Trading Bots are FAKE | https://www.youtube.com/watch?v=7LCT8Tzwg-Y | **METADATA ONLY** | Important context: win-rate marketing may be misleading, not proof of another bot. |
| Ryan: Risk and offered portfolio | https://responsibleforextrading.com/powerhouse/ | **WEBSITE_FIRST_PARTY_CLAIM** | Six different strategies; Northstar AUD/CAD H1, Ranger GBP/CAD + AUD/CAD M30/H1, controls, order spacing, equity protection. |
| Ryan: FAQ | https://responsibleforextrading.com/faq/ | **WEBSITE_FIRST_PARTY_CLAIM** | Notes bounded progression, volatility/time filters; stops can exceed preset values due gaps/illiquidity. |
| Ryan: Account overview | https://responsibleforextrading.com/ | **WEBSITE_FIRST_PARTY_CLAIM with dated snapshot** | 2026-09-30: high-risk +97.72% TWR / 32.18% DD; Night Sky +458.99% gain / 42.04% DD; not audited by this project. |
| Ryan: Live Results | https://responsibleforextrading.com/stats/ | **WEBSITE_FIRST_PARTY_CLAIM / linked widgets not audited** | 24 account-index entries at page snapshot; accounts/settings/horizons heterogeneous. |
| Mathematical counter-analysis | https://www.mql5.com/en/articles/8390 | **INDEPENDENT ANALYSIS SOURCE** | Grid/martingale arithmetic and misleading balance-only profitability. |
| Soft-grid tail-loss study | https://www.mdpi.com/1999-4893/19/6/442 | **ACADEMIC SOURCE** | Soft Martingale / drawdown dichotomy; not independent proof of RFT or AlgoLee system performance. |

## Channel-wide request: transparent coverage boundary

- The channel's catalog comprises **hundreds of uploads**. This first research pass queried the channel's recent long-form catalog and topic-filtered grid videos, and fully read **two central source transcripts across the two channels**.
- A provider credit limit blocked further transcript fetches; later readings of the above prioritized videos remain a **specific TODO under #346**. Never state that all channel content was watched or verified.
- Reproduce only rule summaries with source URLs. Do not paste complete captions or redistribute paid/source software.
- Public tracker performance is not equivalent to order-by-order accounting. Check broker/account modes, actual deposits and withdrawals, all live/open positions, ongoing floating drawdown, delisted/closed losing accounts, account-curve vs equity-curve, funding and historical changes before making performance claims.

## Independent validation and action boundaries

Original hypotheses and bounded candidate protocol: [RESEARCH_SPEC_V0_1.md](./RESEARCH_SPEC_V0_1.md). Research and experimental ToDos: [Issue #346](https://github.com/woshixiong/trader-assist-v0/issues/346). No live operation authorized.