# V0-00 Scope and Start Declaration

## Source of truth

- TraderOS repository: `woshixiong/trade-os`
- authoritative TraderOS main: `2a400348a0ced56171f889540a9a481ebaa0d191`
- merged planning PR: `trade-os#54`
- active task: TraderOS Issue `#56`
- target repository: `woshixiong/trader-assist-v0`
- remote V0 base/main: `0638cecebe7bef973c50914621136fdffd92b401`
- active branch: `feature/v0-00-bootstrap-contracts`

## Goal

Freeze strict V0 envelopes and authority contracts before any historical runtime code is ported.

## Included

- canonical data-health enum and legal transition table;
- Bronze/Silver/Gold event envelopes;
- strategy candidate and promotion contracts;
- AI recommendation, proposal, human decision, order-package, and execution-permit contracts;
- evidence-bundle and provenance contracts;
- schema export and drift check;
- contract tests, static checks, and secret scan;
- threat model and authority boundary.

## Excluded

- data collectors and exchange network calls;
- feature or strategy implementations;
- risk sizing;
- signing and permit issuance service;
- order submission, cancellation, protection, reconciliation runtime;
- credentials, Testnet, Mainnet, AWS, or deployment.

## Credential state

`ABSENT_BY_DESIGN`

## Rollback

Close the unmerged pull request and delete the feature branch. `main`, credentials, venue state and TraderOS production authorities remain unchanged.
