# Codex Local Setup V2 — User Machine

**Status:** USER-OPERATED LOCAL SETUP GUIDE  
**Audit basis:** 2026-08-23 user output  
**Exact Codex compatibility target:** `codex-cli 0.149.0`

Observed:

```text
codex-cli 0.149.0
~/.codex/config.toml present
~/.codex/AGENTS.md absent
~/.codex/AGENTS.override.md absent
model = gpt-5.6-terra
model_reasoning_effort = high
service_tier = default
```

## Required local change after independent acceptance

Keep `codex-cli 0.149.0`, `model = gpt-5.6-terra`, and `service_tier = default` as the neutral cross-project fallback.

Change only the audited global fallback reasoning setting:

```text
model_reasoning_effort = medium
```

Do not create a global project-specific `AGENTS.md` or `AGENTS.override.md`.

Trader Assist task-specific model/reasoning/Web-Search selection remains an Engineering Control / Router decision and should normally be passed explicitly at launch. The user retains manual override.

## Optional named profiles — Codex 0.149.0 mechanism

For exact Codex CLI `0.149.0`, the neutral user fallback remains:

```text
${CODEX_HOME}/config.toml
```

When `--profile <name>` is selected, Codex loads the selected profile from a separate file layered above the neutral fallback:

```text
${CODEX_HOME}/<name>.config.toml
```

Do **not** define the same selected profile as legacy `profile = "<name>"` or `[profiles.<name>]` inside `~/.codex/config.toml`. Exact `0.149.0` detects that legacy configuration and instructs migration to the separate profile file.

Profiles are optional. Explicit task-local Router selection remains preferred when it avoids hidden state.

Example profile files, only if later useful and after checking for filename conflicts:

`~/.codex/ta_terra_high.config.toml`

```toml
model = "gpt-5.6-terra"
model_reasoning_effort = "high"
service_tier = "default"
```

`~/.codex/ta_sol_high.config.toml`

```toml
model = "gpt-5.6-sol"
model_reasoning_effort = "high"
service_tier = "default"
```

`~/.codex/ta_sol_xhigh.config.toml`

```toml
model = "gpt-5.6-sol"
model_reasoning_effort = "xhigh"
service_tier = "default"
```

Select one explicitly, for example:

```text
codex --profile ta_sol_high
```

Do not configure a permanent active Trader Assist profile if that would unexpectedly affect unrelated repositories.

## Verification before relying on a profile

Before first project use of a named profile:

1. verify `codex --version` is the intended supported version;
2. verify the exact `<name>.config.toml` file exists under `${CODEX_HOME}`;
3. invoke Codex with `--profile <name>` and verify the effective selected model/reasoning on the current surface;
4. fail closed on profile conflict, migration warning, parse error, or unexpected effective settings.

A named profile is an operator convenience, not project authority. The frozen Task Packet / Engineering Control routing decision remains authoritative for the task.

## Safety

Never overwrite the whole ~4KB user config merely to make the neutral fallback change. Back it up and replace only the audited top-level model/reasoning/service-tier keys, preserving unrelated MCP/provider/auth/UI settings.

Do not expose `~/.codex/auth.json`, API keys, OAuth/access/refresh tokens or credentials in chat/GitHub.
