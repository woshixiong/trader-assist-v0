# Codex Local Setup V2 — User Machine

**Status:** USER-OPERATED LOCAL SETUP GUIDE  
**Audit basis:** 2026-08-23 user output

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

## Required local change

Keep `codex-cli 0.149.0`, `model = gpt-5.6-terra`, and `service_tier = default` as the neutral cross-project fallback.

Change only the audited global fallback reasoning setting:

```text
model_reasoning_effort = medium
```

Do not create a global project-specific `AGENTS.md` or `AGENTS.override.md`.

Trader Assist task-specific model/reasoning selection remains a Router decision and should normally be passed explicitly by Engineering Control at launch. The user retains manual override.

## Optional named profiles

Named Codex CLI profiles, if later useful for operator convenience, belong inside the existing `~/.codex/config.toml` under `[profiles.<name>]`; they are not separate `*.config.toml` files.

Example only — add these only after auditing the existing config for name conflicts:

```toml
[profiles.ta_terra_high]
model = "gpt-5.6-terra"
model_reasoning_effort = "high"
service_tier = "default"

[profiles.ta_sol_high]
model = "gpt-5.6-sol"
model_reasoning_effort = "high"
service_tier = "default"

[profiles.ta_sol_xhigh]
model = "gpt-5.6-sol"
model_reasoning_effort = "xhigh"
service_tier = "default"
```

Select a named profile with the current Codex CLI profile selector. Do not set a permanent active profile merely to optimize Trader Assist if it would unexpectedly affect other repositories.

Profiles are optional. They are not required for V2 correctness, and explicit task-local Router selection is preferred when it avoids hidden state.

## Safety

Never overwrite the whole ~4KB user config merely to make this change. Back it up and replace only the audited top-level model/reasoning/service-tier keys, preserving unrelated MCP/provider/auth/UI settings.

Do not expose `~/.codex/auth.json`, API keys, OAuth/access/refresh tokens or credentials in chat/GitHub.