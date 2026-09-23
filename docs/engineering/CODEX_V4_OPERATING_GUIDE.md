# Trader Assist V4 — Codex Setup and Operating Guide

This guide activates the repository-side V4 tooling after the corresponding PR
is independently reviewed and merged. It grants no merge, deployment, runtime,
credential, exchange-write, or trading authority.

## Before a development package

1. Use a current Codex Desktop release and open this repository as a trusted
   project. Project `.codex/` configuration and hooks do not load for an
   untrusted project.
2. Review and trust the exact project hook definition when Codex prompts after
   it changes. The hook is hash-bound and skipped until trusted.
3. Confirm `.codex/config.toml` loads these normal defaults:
   - routine main Writer: `gpt-5.6-terra`, Medium;
   - hard semantic escalation: `gpt-5.6-sol`, Medium, only when explicitly rebound by Engineering Control;
   - web search: disabled;
   - Writer sandbox: workspace-write;
   - Explorer request: `gpt-5.6-luna`, Low, read-only;
   - internal Code Reviewer request: `gpt-5.6-terra`, Medium, read-only.
   Child-agent profile files are requests, not proof. Spawn Explorer or Code
   Reviewer only when the actual child model/reasoning is verifiable at runtime;
   otherwise skip that child and never fall back to the parent/default Sol/High.
4. Do not duplicate project rules in global `~/.codex` configuration.

## Package lifecycle

Engineering Control freezes the complete Development Package and selects the
route. The user does not choose executor or Plan versus Goal.

For a large Codex route:

```text
exact task + Control Capsule
-> deterministic V4 bootstrap
-> Plan-only
-> automatic boundary check
-> one package-scoped Goal
-> implementation / focused validation / bounded repair
-> read-only Code Review
-> commit / push / Draft PR
-> CI_PENDING
-> zero-model exact-head CI wait
-> fresh ordinary-ChatGPT Independent Review
-> retained human Mark Ready / merge gates
```

Resume the same Goal/thread/worktree/checkpoint after interruption. Do not
restart or switch model/executor/reasoning without a new Engineering Control
binding.

## Deterministic checks

Run the active governance smoke check with the repository interpreter:

```text
python scripts/check_v4_governance.py
```

It emits the Issue #232 acceptance labels and fails nonzero on inconsistency.

`scripts/control/v4_bootstrap.py` verifies origin/ref/base/tree, a clean
worktree, preflight PASS fields, Control Capsule, packet/governance binding, and
requested/actual model/reasoning/search identity. Use `--freshen-remote` when
the bootstrap tool owns remote freshness. Pass hashes and attestations from the
exact frozen Development Package; never self-generate authority values merely
to make the check pass.

## Review and CI

The `code_reviewer` agent is read-only implementation-quality review and may
run only when its actual Terra/Medium child identity is runtime-verifiable. If
that identity cannot be proven, skip it rather than silently falling back to
Sol/High. It cannot be the final authority-bearing Reviewer.

After Draft PR publication, checkpoint the exact head at `CI_PENDING` and use
provider-native/deterministic CI waiting. Do not keep a semantic model active to
poll. On all-green exact-head CI, launch one fresh ordinary ChatGPT Independent
Reviewer with exact GitHub evidence and High reasoning.

If GitHub rejects native self-approval, write the complete canonical result as
`REVIEW_SUBMISSION_MODE=COMMENT_ONLY`. This preserves review evidence but does
not create an independent GitHub identity.

## Local Git publication nonregression

The accepted user-local route is HTTPS + GitHub CLI browser OAuth + macOS system
credential storage + `gh auth setup-git`. No manual PAT, plaintext token, or
`--insecure-storage` route is allowed. When `.github/workflows/**` changes,
verify the active OAuth credential includes `workflow` before the real push;
`gh auth status`, `gh api user`, `git ls-remote`, and `git push --dry-run` are not
scope proof. If identity, required scopes, and the exact local checkpoint are
already PASS but real HTTPS push fails with the known LibreSSL
`SSL_ERROR_SYSCALL` class, do not retry semantic work, push, credentials, or
Codex. Preserve the exact offline checkpoint and use the accepted connected
GitHub publication surface.

## After merge

Only after explicit current merge authority and observed live-main readback:

1. replace the ChatGPT Project Instruction with the exact merged content of
   `governance/CHATGPT_PROJECT_GOVERNANCE_BRIDGE_V4_CORE_ENFORCEMENT_2026-09-23.md`;
2. freshen local main and reopen the trusted project;
3. confirm config, agents, hooks, and the four V4 skills load;
4. rerun `scripts/check_v4_governance.py`;
5. return to product development unless a real observed tooling failure or
   materially new capability justifies another tooling cycle.

Merge does not authorize deployment, runtime/service changes, credentials,
private APIs, wallet/signing, exchange writes, or trading.
