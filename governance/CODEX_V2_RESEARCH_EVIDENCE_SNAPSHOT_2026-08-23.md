# Codex V2 / Tool Router — Research Evidence Snapshot

**Date:** 2026-08-23  
**Purpose:** auditable external evidence behind the V2 tooling candidate. This is evidence, not a permanent model ranking.

## OpenAI / Codex

Checked current first-party sources:

- `https://openai.com/index/harness-engineering/`
- `https://developers.openai.com/codex/config-basic`
- `https://developers.openai.com/codex/config-reference`
- `https://developers.openai.com/codex/guides/agents-md`
- `https://developers.openai.com/codex/skills`
- `https://developers.openai.com/codex/noninteractive`
- `https://developers.openai.com/api/docs/guides/latest-model`

Key evidence used:

1. OpenAI's agent-first production case reports that a giant `AGENTS.md` caused predictable context/maintenance problems; the mature pattern is a short map pointing to structured repo knowledge.
2. Codex project configuration is supported at repo `.codex/config.toml`; precedence is CLI/override > project config > selected user profile > user config.
3. Codex AGENTS discovery has a combined default project-doc limit of 32 KiB; global guidance applies across repos and should not duplicate project governance.
4. Repo skills under `.agents/skills` use progressive disclosure: initial context contains small metadata, full `SKILL.md` loads only when selected.
5. `codex exec --json` emits JSONL including exact thread/session identity and turn usage (`input_tokens`, `cached_input_tokens`, `output_tokens`, `reasoning_output_tokens`). Exact session IDs can be resumed.
6. Structured final output is available through `--output-schema` when a future workflow needs machine-enforced result shape.
7. Current config supports `model_verbosity`, `model_reasoning_summary`, `web_search`, project/user layers and `agents.enabled`; multi-agent tools are on by default unless disabled.
8. Current GPT-5.6 guidance recommends intentional reasoning selection and a balanced medium baseline rather than assuming maximum reasoning is always best.
9. Repeated stable prompt prefixes are favorable for caching; V2 therefore freezes model/reasoning/CWD/sandbox/approval/tool shape within one coherent stage and places volatile evidence late.

## Anthropic / Z.AI / DeepSeek

Current model research supports treating Claude Opus 4.6, GLM-5.3 and DeepSeek V4 Pro as serious advanced coding candidates with different task fits, not as a single proven universal rank.

- Anthropic Opus 4.6: complex codebases, careful planning, longer agentic work, debugging/review strengths.
- Z.AI GLM-5.3 (official release 2026-08-14): strong vendor-reported long-horizon/agentic coding results.
- DeepSeek V4 Pro: enhanced agentic/repo coding and strong terminal/repo benchmark evidence.

Project policy therefore encodes task-fit guidance and user override rather than a universal ordering.

## Hermes

Checked current Nous Research Hermes documentation and repository. Relevant mature capabilities include terminal/files, browser automation, skills with conditional/progressive loading, profiles, delegation/orchestration, cron and multiple provider/model surfaces.

Project decision: Hermes fits **after L1 freezes a lossless Task Packet** and before/around the selected local executor as transport/operator/orchestration. It must not add a duplicate semantic reasoning layer or choose engineering/model routes. This matches existing Trader Assist Hermes authority boundaries.

## Local Codex audit

User-provided 2026-08-23 audit:

```text
codex-cli 0.149.0
~/.codex/config.toml = present (4119 bytes)
~/.codex/AGENTS.md = absent
~/.codex/AGENTS.override.md = absent
model = gpt-5.6-terra
model_reasoning_effort = high
service_tier = default
```

V2 keeps CLI/service tier, changes neutral global fallback reasoning to medium, preserves the absence of global project instructions, and moves stable Trader Assist low-noise defaults into repo `.codex/config.toml`.