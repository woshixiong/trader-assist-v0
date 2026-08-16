# Operator One-Paste Terminal Delivery Rule V1

Effective: 2026-08-16

Status: governance/operator-interface rule. This rule does not grant code, merge, deployment, runtime, cloud, credential, account, signing, wallet, or exchange-write authority.

## Core rule

For every user-operated macOS engineering action, the default deliverable is exactly one contiguous command block that the operator can paste directly into a freshly opened ordinary Terminal window and execute immediately.

The operator must not be required to perform a preparatory `cd`, launch Codex separately, open another CLI first, paste a second prompt, choose between a shell prompt and an agent prompt, or translate prose instructions into commands.

The engineering orchestrator owns all execution routing inside the delivered block.

If the task needs Codex CLI, the Terminal block must launch Codex itself and provide the complete Codex task through stdin/heredoc or another self-contained mechanism. If the task needs Git, tests, GitHub CLI, packaging, inspection, or another local tool, the same Terminal block must invoke those tools itself.

Do not present a naked Codex prompt as the operator deliverable unless the user explicitly asks for prompt text only.

## User interaction contract

Normal local workflow:

1. User opens Terminal.
2. User copies the single block supplied by Engineering.
3. User pastes it once and runs it.
4. The block performs all required routing, preflight, working-directory changes, tool invocation, and prompt injection.
5. User returns the requested final output only if human return evidence is still required.

No intermediate operator step is allowed merely because the internal worker happens to be Codex CLI, shell, Git, gh, Python, or another tool.

Do not require the user to distinguish `Terminal local command` from `Terminal -> Codex CLI`. That distinction may remain internal to the orchestrator, but it must not create an extra human step.

## Required properties of every one-paste block

When material, the block must self-contain:

- the absolute repository/worktree path;
- `cd` / tool working-directory targeting;
- fail-closed repository, branch, SHA, worktree, dirty-state, dependency, and authority preflight checks;
- the full task prompt when an agent is invoked;
- intended model/reasoning/sandbox/approval settings when applicable;
- the authorized mutation boundary;
- tests/verification required by the current task;
- commit/push/PR behavior only when currently authorized;
- explicit refusal to cross merge/deploy/runtime/cloud/account/exchange authority unless separately authorized;
- a concise final result for the operator to return when needed.

The operator must never have to infer which text belongs in the shell versus which text belongs in an agent prompt.

## Failure containment

A one-paste block must not unnecessarily terminate the user's parent interactive Terminal or SSH session when an internal check fails.

For multi-step scripts, prefer a contained subshell/heredoc such as `bash <<'EOF' ... EOF` (or an equivalent safe wrapper), so `set -e` / `exit` applies to the task block rather than logging the operator out of the parent shell.

## Codex-specific transport

When Codex is the selected Writer/Reviewer, Engineering must embed the complete instruction inside the one-paste Terminal block and invoke Codex from that block. The user must not be told to:

- run `codex` first and then paste a prompt;
- paste a raw task packet into zsh;
- manually switch to a branch before starting Codex;
- manually create a prompt file solely to transport the task;
- perform a second copy/paste after the first Terminal action.

If the selected Codex invocation cannot safely perform an authorized network/Git operation because of sandbox/approval constraints, Engineering must encode an appropriate supported invocation or split the work internally. It must not silently push that routing burden back to the user.

## FinalShell / target-host companion rule

This rule does not replace the existing FinalShell target-host rule.

For Lightsail target-host work, when the user is already connected through FinalShell, deliver one contiguous copy-ready remote-shell block for the current session. Do not repeat SSH setup. Prefer contained heredoc/subshell execution so a fail-closed check does not disconnect the parent FinalShell session.

## Exceptions

An additional human step is allowed only when technically unavoidable or when a safety/authority boundary requires explicit human action, for example:

- OS/browser credential approval that cannot be delegated;
- MFA/security-key confirmation;
- an explicit user merge/deploy/runtime authorization gate;
- a GUI-only action with no safe available command/tool path;
- a secret that must not be transported through chat or command history.

When such an exception exists, state the blocker before asking for the extra step and keep the number of operator actions to the minimum possible.
