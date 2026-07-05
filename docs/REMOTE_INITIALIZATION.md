# Remote Repository Initialization

Target: `woshixiong/trader-assist-v0`

## Current state

The private repository was created through GitHub with an initial README commit:

```text
REMOTE MAIN:
0638cecebe7bef973c50914621136fdffd92b401

FEATURE BRANCH:
feature/v0-00-bootstrap-contracts
```

The reviewed bootstrap content is written only to the feature branch. Do not recreate the repository, overwrite `main`, import the local Git bundle, or force-push either branch.

## Remaining remote workflow

1. Open a pull request from `feature/v0-00-bootstrap-contracts` to `main`.
2. Wait for `V0 contracts CI` on the exact PR head.
3. Obtain an independent review of contracts, schemas, provenance and authority boundaries.
4. Do not merge until CI and independent review pass.
5. Do not begin V0-01, import historical runtime code, add credentials or enable Testnet/Mainnet as part of this task.

The local bundle and patch remain recovery evidence only; GitHub becomes authoritative after reviewed merge.
