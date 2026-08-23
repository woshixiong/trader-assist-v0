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

Keep `codex-cli 0.149.0` and `service_tier=default`.

Change only the user-level fallback:

```text
model_reasoning_effort = medium
```

Do not create a global project-specific `AGENTS.md` or override file.

Create optional named user profiles for task-local Engineering Control selection:

```text
~/.codex/ta-terra-high.config.toml
  model = gpt-5.6-terra
  model_reasoning_effort = high
  service_tier = default

~/.codex/ta-sol-high.config.toml
  model = gpt-5.6-sol
  model_reasoning_effort = high
  service_tier = default

~/.codex/ta-sol-xhigh.config.toml
  model = gpt-5.6-sol
  model_reasoning_effort = xhigh
  service_tier = default
```

Engineering Control chooses the exact profile/flags per task. The user should not need to manually decide unless exercising the permanent Router override.

## Safety

Never overwrite the whole 4KB user config to accomplish this change. Back it up and replace only the audited top-level model/reasoning/service-tier keys, preserving unrelated MCP/provider/auth/UI settings.

Do not expose `~/.codex/auth.json`, API keys, OAuth/access/refresh tokens or credentials in chat/GitHub.