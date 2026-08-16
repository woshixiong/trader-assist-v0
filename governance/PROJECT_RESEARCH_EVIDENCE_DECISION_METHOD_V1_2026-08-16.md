# Project Research, Evidence, and Decision Method V1

Status: **MANDATORY PROJECT GOVERNANCE**

Effective scope: Trader Assist / Trade OS project research, planning, strategy, product, engineering, architecture, technology selection, framework selection, and other material direction-setting work.

## Purpose

Material project decisions must not be produced from either unsupported intuition or uncritical copying of external consensus. Every applicable task must separate independent reasoning from external evidence collection, then explicitly synthesize the two before a final recommendation is issued.

The required order is:

1. **Independent analysis first**
2. **External research and evidence second**
3. **Synthesis and final decision third**

The order is mandatory. Do not reverse it, collapse it into one opaque step, or read external conclusions first and later present them as independent reasoning.

## Applicability

Use this method for any task that materially determines or changes one or more of the following:

- research agenda or research plan;
- product direction, scope, prioritization, or launch route;
- trading-strategy research direction or strategy-design choice;
- engineering route, implementation approach, or build-vs-buy choice;
- system architecture, data architecture, infrastructure, reliability, or security direction;
- technology, library, framework, provider, protocol, model, Agent, or tooling selection;
- operating workflow or governance design;
- material optimization, replacement, migration, or deprecation decisions;
- any other recommendation where the project would spend meaningful engineering time, money, operational risk, or research capacity based on the answer.

This method is not required for purely mechanical execution of an already-authorized plan, exact state verification, routine file movement, formatting, or other tasks that do not create a new substantive judgment. If a task begins as execution but exposes a new material design choice, this method becomes required for that choice.

## Phase 1 — Independent analysis

Before seeking external conclusions, perform an independent pass using the known project facts, first principles, domain mechanics, constraints, and explicit user objectives.

At minimum, establish:

- the real problem being solved;
- assumptions and unknowns;
- decision criteria and constraints;
- causal/mechanical reasoning;
- candidate approaches or hypotheses;
- expected advantages, failure modes, and trade-offs;
- what evidence would confirm, weaken, or falsify the preliminary view.

For material decisions, preserve a short **pre-research position** so later work can distinguish genuinely independent reasoning from conclusions adopted from outside sources.

Independent analysis is not a license to ignore known project facts or live repository state. It means the analytical position is formed before consulting external opinions, frameworks, reports, or recommended solutions for the specific decision.

## Phase 2 — External research and evidence

After the independent pass, research the strongest available external evidence relevant to the decision.

Research broadly enough to include, when applicable:

- official documentation and specifications;
- primary-source technical material;
- academic papers and serious research reports;
- mature industry frameworks and standard practices;
- maintained open-source implementations;
- benchmark results and reproducible evaluations;
- production case studies and postmortems;
- independently verified examples of successful use;
- known failure cases, limitations, criticisms, and counterexamples;
- competing approaches, not only evidence supporting the initial hypothesis.

### Source priority

Prefer sources in roughly this order when the category exists:

1. official specifications, documentation, source repositories, and first-party technical material;
2. primary research, peer-reviewed work, or directly inspectable datasets/benchmarks;
3. mature maintained frameworks and credible production case studies;
4. high-quality independent technical analysis;
5. community discussion or anecdotal reports only as supplementary evidence.

For crypto/blockchain/transaction/arbitrage work, prefer English-language primary and technical sources unless another source is demonstrably more authoritative for the specific subject.

### Evidence quality rules

- Check publication/update date where freshness matters.
- Separate measured evidence from claims, marketing, and opinion.
- Prefer reproducible or inspectable evidence over popularity.
- Search for disconfirming evidence and failure reports, not only supporting evidence.
- Do not treat a mature framework as automatically suitable for this project; evaluate fit against project constraints.
- Do not recommend custom development before checking whether a maintained external solution already solves the problem adequately.

## Phase 3 — Synthesis and final decision

Only after Phases 1 and 2 are complete should the final report, route, or recommendation be produced.

The synthesis must explicitly compare the independent view with the external evidence and identify:

- what the external research confirms;
- what it changes or refines;
- what it contradicts or falsifies;
- which uncertainties remain unresolved;
- which candidate routes are rejected and why;
- why the selected route best fits the actual Trader Assist / Trade OS constraints.

For a material decision, the final output should make clear whether the recommendation is:

- **independently derived and externally confirmed**;
- **independently derived but externally modified**;
- **rejected after external evidence**; or
- **still uncertain and requiring an experiment or additional evidence**.

Do not hide disagreement between first-principles reasoning and external evidence. A conflict is itself decision-relevant information.

## Required output standard

For substantive research/route-setting work, the deliverable should contain enough structure for another project participant to audit the reasoning. At minimum include:

1. **Independent view** — initial reasoning, assumptions, candidate routes, and decision criteria.
2. **External evidence** — the most relevant sources, frameworks, cases, counterexamples, and findings.
3. **Synthesis** — where external evidence confirms, modifies, or rejects the independent view.
4. **Decision / recommendation** — selected route and rationale tied to project constraints.
5. **Residual uncertainty / validation plan** — what still needs testing, benchmarking, replay, shadow evidence, or operational validation.

The format may be compressed for time-critical work, but the three-stage sequence must still be preserved.

## Anti-patterns prohibited

The following are not acceptable substitutes for this method:

- searching first and merely summarizing the most common external answer;
- producing a preferred answer first and searching only for supporting evidence;
- citing many sources without independent causal analysis;
- claiming independent reasoning after external conclusions have already anchored the analysis;
- selecting a fashionable or complex framework without comparing simpler or mature alternatives;
- ignoring contrary evidence, negative case studies, or project-specific constraints;
- presenting an external framework as validated for Trader Assist / Trade OS without checking fit.

## Relationship to existing project rules

This method complements, rather than replaces, the existing efficiency-first and minimum-safe-boundary rules.

External research should actively look for mature solutions that reduce custom engineering. The final route should still prefer the smallest adequate, testable, reversible solution when it satisfies the real requirement.

No research conclusion independently grants implementation, commit, push, Mark Ready, merge, deployment, runtime, cloud, credential, account, signing, or exchange-write authority. Existing authorization gates remain unchanged.

## Successor-window requirement

Every successor window or Agent that performs an applicable research or direction-setting task must follow this document without requiring the user to restate the method.

If a task packet or prompt conflicts with this method without explicitly superseding it, this project governance document controls.