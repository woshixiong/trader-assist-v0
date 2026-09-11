# Trader Assist / Trade OS — V0 Frontend Product and Technical Architecture Research Freeze

**Date:** 2026-09-11  
**Status:** RESEARCH / PRODUCT-ARCHITECTURE DECISION RECORD ONLY  
**Repository:** `woshixiong/trader-assist-v0`  
**Research base main:** `41e72737a09d45583df8c6473150c4500ffbf239`  
**Research branch:** `research/frontend-v0-product-architecture-20260911`  
**Authority effect:** NONE until separately reviewed/accepted under project governance  
**Implementation authority:** NO  
**Deployment/runtime authority:** NO  
**Credential/private API/wallet/signing/exchange-write authority:** NO  
**Mark Ready / merge authority:** NO

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS_FOR_PRODUCT_RESEARCH_FREEZE_ONLY
PRODUCT_WRITER_DISPATCH=NO
IMPLEMENTATION_PACKET=NO
EXECUTION_PLAN=NO
```

This file is intentionally additive. It does not modify or silently supersede the historical Product, Strategy, Operations or Governance files. It records a new post-Nautilus frontend/product-architecture research decision so the new route can be compared with the old V0 planning record.

---

## 1. Decision scope

The product target already frozen by current authority is:

```text
SYSTEM FINDS / EVALUATES OPPORTUNITY
-> SYSTEM PRODUCES EXACT ORDER PREVIEW / INTENT
-> HUMAN TRADER REVIEWS
-> HUMAN EXPLICITLY APPROVES
-> SYSTEM EXECUTES THROUGH MATURE INFRASTRUCTURE
-> SYSTEM OWNS ORDER LIFECYCLE / PROTECTION / RECONCILIATION
-> SYSTEM RECORDS EXECUTION + RESEARCH EVIDENCE
```

The frontend problem is therefore **not** to build a general-purpose exchange terminal, charting workstation, research dashboard or autonomous trading UI.

The bounded product responsibility is:

```text
FAST HUMAN REVIEW
+ EXACT TRANSACTION AUTHORIZATION
+ EXECUTION SUPERVISION
+ FAIL-CLOSED STATUS VISIBILITY
```

User/product constraints:

- functional before decorative;
- minimal cognitive load during frequent intraday use;
- stable and fast;
- responsive/mobile usable;
- no unnecessary frontend engineering platform;
- no duplicated trading/execution authority in the browser;
- future UX iteration should be driven by real use feedback rather than speculative feature breadth.

---

## 2. Live internal authority review

Fresh review included current live versions of:

- `AGENTS.md`;
- `governance/PROJECT_RULES_INDEX.md`;
- `governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V2_2026-09-01.md`;
- `governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md`;
- `governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md`;
- `governance/EXTERNAL_MATURE_SOLUTION_SELECTION_AND_ADOPTION_RULE_V1_2026-09-07.md`;
- Issue #18 later Product amendment comment `5581144976`;
- Issue #139 current Nautilus-centered risk ladder comment `5580843025`;
- Issue #161 Strategy Research Master Plan;
- Issue #163 Nautilus Transition Master Plan;
- historical TraderOS `TRADER_ASSIST_V0_TARGET_ARCHITECTURE.md`;
- historical TraderOS Issue #59 V0 human-review workflow;
- current `src/trader_assist_v0/contracts/approval.py`;
- current `pyproject.toml`;
- current Draft PR #168 identity and changed paths.

Key internal conclusions:

1. The old manual-Hyperliquid-click path is historical, not the desired terminal V0 interaction.
2. Human approval of each exact new-risk order package remains mandatory.
3. Nautilus/mature infrastructure owns generic execution lifecycle and reconciliation; project code must not recreate a second OMS/account/order authority.
4. The historical V0 dashboard already preferred a lean server-rendered web application with a mandatory health strip, active candidate/evidence, proposal-vs-current diff, exact order package and human approval controls.
5. Zero-write Human Approval is the authoritative stage for proving the real future UI interaction before exchange writes.
6. Current Strategy authority remains independent from the frontend and must be versioned/promoted separately.
7. Current `ProposalV0` / `HumanReviewDecisionV0` / `ExecutionPermitV0` semantics provide valuable approval-safety concepts, but their historical ETH/playbook bindings must not be treated as the final new-route Strategy schema.

No current authority requires a SPA, a large dashboard, a charting engine, a native mobile app, or browser-side trading logic.

---

## 3. Phase 1 — independent analysis before external solution selection

### 3.1 Problem

The operator must be able to answer, quickly and accurately:

```text
IS THE SYSTEM SAFE/READY?
WHAT OPPORTUNITY IS BEING PROPOSED?
WHAT EXACT ORDER/RISK AM I APPROVING?
WHAT CHANGED SINCE THE PROPOSAL WAS CREATED?
CAN I APPROVE IT NOW?
WHAT HAPPENED AFTER APPROVAL?
```

### 3.2 Hard requirements / P0

```text
P0_SERVER_SIDE_AUTHORITY=REQUIRED
P0_NO_BROWSER_TRADING_AUTHORITY=REQUIRED
P0_EXACT_PROPOSAL/ORDER_BINDING=REQUIRED
P0_SERVER_REVALIDATION_AT_APPROVAL=REQUIRED
P0_FAIL_CLOSED_ON_STALE/UNKNOWN/RECONCILING=REQUIRED
P0_MOBILE_RESPONSIVE=REQUIRED
P0_REALTIME_SERVER_TO_BROWSER_STATE=REQUIRED
P0_APPROVAL_ACTION_AUDITABLE=REQUIRED
P0_NO_SECOND_OMS/POSITION/AUTHORITY=REQUIRED
P0_LOW_FRONTEND_LIFECYCLE_BURDEN=REQUIRED
P0_SAME_UI_ACROSS_SHADOW/ZERO-WRITE/TESTNET/MAINNET_PILOT=TARGET
P0_PRIVATE_AUTHENTICATED_OPERATOR_SURFACE=REQUIRED
```

### 3.3 Initial candidate routes

- client-heavy SPA: React/Vue/Svelte class;
- pure full-page SSR;
- SSR + HTMX;
- SSR + Hotwire/Turbo;
- Phoenix LiveView class;
- Streamlit/Gradio-style rapid dashboard;
- Python SSR + browser-native HTML/HTTP/EventSource + minimal vanilla JS.

### 3.4 Initial independent hypothesis

The bounded product does not require a client-side application state machine. The browser should be a **presentation and explicit-human-action surface**, while authoritative state remains on the server.

The initial expected best fit was server-rendered Python with small hypermedia enhancement. External research was required to determine whether HTMX, Turbo, native browser standards or another mature route minimized total burden.

---

## 4. Phase 2 — external / mature evidence

Research date: 2026-09-11. Primary/official sources were preferred.

### 4.1 Server-rendered Python and SSE

**FastAPI official documentation** supports Jinja2 template rendering and, in current releases, first-party Server-Sent Events through `EventSourceResponse` / `ServerSentEvent`.

- Templates: https://fastapi.tiangolo.com/advanced/templates/
- Jinja2Templates API: https://fastapi.tiangolo.com/reference/templating/
- SSE: https://fastapi.tiangolo.com/tutorial/server-sent-events/
- current researched FastAPI release: `0.141.1` (2026-07-29)
- license: MIT

Relevant finding: current project is already Python 3.12 + Pydantic. FastAPI keeps the operator surface in the same language/runtime family and can own HTML endpoints plus SSE without introducing a second backend platform.

### 4.2 Browser-native EventSource / SSE

MDN records Server-Sent Events / `EventSource` as widely available across major browsers and devices since January 2020. SSE is one-way server-to-browser communication and reconnects automatically after a lost connection.

- https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
- https://developer.mozilla.org/en-US/docs/Web/API/EventSource

This direction matches the product topology:

```text
SERVER STATE -> BROWSER   = continuous push needed
BROWSER -> SERVER         = discrete explicit human transactions
```

The browser does **not** need a permanent bidirectional trading channel. Human Approve/Reject actions fit ordinary HTTPS requests better than WebSocket messages because they are discrete, auditable transaction authorizations.

SSE limitation noted by MDN: without HTTP/2, browsers may impose a low per-origin connection limit. Product consequence: V1 should use **one operator SSE stream per active page/session**, not many component streams.

### 4.3 HTML-over-the-wire mature evidence

Hotwire/Turbo is a mature example of server-owned application logic with HTML-over-the-wire partial updates. Turbo 8.0.23 is current in the researched release line, and 37signals documents production use of Hotwire inside Basecamp/HEY.

- https://turbo.hotwired.dev/handbook/introduction
- https://turbo.hotwired.dev/handbook/streams
- https://turbo.hotwired.dev/
- production case: https://dev.37signals.com/building-basecamp-project-stacks-with-hotwire/
- Turbo license: MIT

External confirmation: a fast modern application does not require a client-heavy SPA; server templates plus narrow live updates can support complex production UX with substantially less custom browser logic.

Turbo is not selected for this project because the bounded current need is smaller than the framework surface and the project does not otherwise use the Rails/Hotwire ecosystem.

### 4.4 HTMX evidence and counterevidence

HTMX strongly matches the hypermedia/server-rendered architecture. It supports partial HTTP updates and SSE/WebSocket extensions and has a permissive 0BSD license.

However, the exact research date matters:

- htmx 4.0.0 was released on 2026-08-28, only about two weeks before this decision record;
- htmx 4 changes inheritance, events, fetch behavior, error swapping and history semantics;
- the canonical repository `master` package metadata observed during research still reports `2.0.10`, while the separate v4 documentation/release site reports 4.0.0.

Sources:

- https://four.htmx.org/announcements/2026-08-28-htmx-4.0.0-is-released
- https://four.htmx.org/docs/whats-new-in-htmx-4
- https://github.com/bigskysoftware/htmx
- https://github.com/bigskysoftware/htmx/blob/master/LICENSE

Conclusion: HTMX remains a credible mature option, but **this exact moment is a poor time to create an unnecessary new dependency on a fresh major-version transition** when browser-native standards already satisfy the current requirement. HTMX becomes a re-open candidate only if native fragment-update code begins duplicating material request/swap/error-management complexity.

### 4.5 SPA counterexample

React and Vue officially describe SPA/client-side routing and state ownership as useful for rich, deeply interactive applications. They also require the frontend to own substantially more state, routing, rendering and build/test tooling.

- https://react.dev/learn/managing-state
- https://react.dev/learn/creating-a-react-app
- https://vuejs.org/guide/scaling-up/routing
- https://vuejs.org/guide/extras/ways-of-using-vue

For this bounded V1, those capabilities do not solve a current P0 that native HTML/SSR/SSE cannot solve. A SPA would add a second application state layer and a larger dependency/build/test/security surface without a demonstrated product benefit.

Disposition: **reject for V1, not reject forever**.

Re-open trigger: a later product stage requires genuinely rich client-side stateful interactions that cannot be expressed cleanly as server-owned views and discrete actions.

### 4.6 Phoenix LiveView counterexample

Phoenix LiveView is a strong mature server-rendered real-time model and demonstrates that rich live interfaces can remain server-centric.

- https://phoenix-live-view.hexdocs.pm/
- https://github.com/phoenixframework/phoenix_live_view

It is not selected because adopting Elixir/Phoenix solely for this UI would create a second runtime/platform and violate current project continuity / bounded-integration burden. This is a project-fit rejection, not a maturity rejection.

### 4.7 Streamlit counterexample

Streamlit is excellent for rapid data applications but its documented execution model reruns the script on interaction and binds Session State to the browser/WebSocket session; session state resets with connection/tab lifecycle.

- https://docs.streamlit.io/develop/concepts/architecture
- https://docs.streamlit.io/develop/concepts/architecture/session-state
- https://docs.streamlit.io/develop/concepts/architecture/forms

That model is convenient for exploratory dashboards, but it is a poor fit for an exact transaction-authorization surface whose durable truth must be independent of browser/session lifecycle.

Disposition: reject for approval/execution V1; it may remain appropriate for isolated research tooling outside execution authority.

### 4.8 Responsive/mobile mature evidence

Bootstrap 5.3 is mobile-first and provides mature responsive layout/form primitives. Current researched version is `5.3.8`, MIT licensed.

- https://getbootstrap.com/docs/5.3/extend/approach/
- https://getbootstrap.com/docs/5.3/layout/breakpoints/
- https://getbootstrap.com/docs/5.3/forms/overview/
- https://github.com/twbs/bootstrap

W3C WCAG 2.2 requires content to reflow without loss of functionality at a width equivalent to 320 CSS pixels, subject to defined exceptions. WCAG 2.2 Target Size (Minimum) is 24x24 CSS pixels or equivalent spacing. Apple Human Interface Guidelines recommend a 44x44 pt hit region for buttons.

- https://www.w3.org/TR/WCAG22/#reflow
- https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
- https://developer.apple.com/design/human-interface-guidelines/buttons

Conclusion: mobile support should be native responsive web, not a separate mobile codebase.

### 4.9 Transaction authorization security evidence

OWASP Transaction Authorization guidance closely matches the project’s existing Proposal -> Human Decision -> Permit model:

- significant transaction data must be visible and acknowledged by the user (`What You See Is What You Sign`);
- authorization must be distinct and enforced server-side;
- transaction verification data must be generated/protected server-side;
- each transaction authorization should be unique and limited in time;
- execution must verify that the transaction was properly authorized.

Source:
- https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html

Additional OWASP guidance:

- stateful applications should use CSRF protection;
- SameSite is defense-in-depth, not a replacement for CSRF protection;
- Secure + HttpOnly session cookies and `__Host-` prefix are recommended where applicable;
- CSP should restrict scripts/connections/forms/framing;
- clickjacking protection should prevent hostile framing.

Sources:
- https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Clickjacking_Defense_Cheat_Sheet.html

### 4.10 Nautilus execution-state ownership

NautilusTrader’s official documentation defines the `LiveExecutionEngine` as the reconciliation owner for live order/position state, including startup reconciliation and continuous discrepancy checks. Execution clients own venue submit/modify/cancel and execution reports.

- https://nautilustrader.io/docs/latest/concepts/reconciliation/

Product consequence: the frontend must **present a project-owned projection of Nautilus state, not maintain a second order/position lifecycle authority**.

### 4.11 Performance evidence

Core Web Vitals provide mature field-performance targets, split by mobile and desktop at the 75th percentile:

- LCP <= 2.5 s;
- INP <= 200 ms;
- CLS <= 0.1.

Source:
- https://web.dev/articles/vitals

These are baseline user-experience targets, not trading-safety gates. Approval safety must never depend on the browser rendering an update quickly enough; server-side revalidation remains authoritative.

---

## 5. Candidate comparison and Stage-0 disposition

| Candidate | Server authority fit | Mobile fit | Realtime fit | Project continuity | Lifecycle burden | Current disposition |
|---|---|---|---|---|---|---|
| FastAPI + Jinja2 + native HTML/HTTP/SSE + minimal JS | PASS | PASS | PASS | PASS | LOW | **SELECT** |
| FastAPI + Jinja2 + HTMX | PASS | PASS | PASS | PASS | LOW-MEDIUM | DEFER; current v4 transition adds avoidable uncertainty |
| FastAPI/Python + Hotwire Turbo | PASS | PASS | PASS | PASS | MEDIUM | REJECT FOR V1; broader than need |
| React/Vue SPA | PASS functionally | PASS | PASS | PASS | HIGHER | REJECT FOR V1; no current P0 benefit |
| Phoenix LiveView | PASS | PASS | PASS | **FAIL continuity** | HIGH | REJECT |
| Streamlit | WEAK for transactional authority | PASS | PASS-ish | PASS | LOW start / higher authority mismatch | REJECT for execution UI |
| Pure full-page SSR only | PASS | PASS | FAIL/weak for live execution supervision | PASS | LOW | REJECT alone; keep as graceful baseline |

Typed mature-solution disposition:

```text
CAPABILITY_CLASS=THIN_INTEGRATION + PRESENTATION
SELECTED_ROUTE=SELECT_MODULAR_COMPOSITION
COMPOSITION=
  FASTAPI SERVER ENDPOINTS
  + JINJA2 SERVER TEMPLATES
  + NATIVE HTML FORMS / HTTP
  + NATIVE EVENTSOURCE / SSE
  + MINIMAL VANILLA JS FOR LIVE FRAGMENT REFRESH / CONNECTION INDICATOR
  + BOOTSTRAP 5.3 CSS-ONLY RESPONSIVE PRIMITIVES
HTMX_DEFAULT=NO
HOTWIRE_DEFAULT=NO
SPA_DEFAULT=NO
ALPINE_DEFAULT=NO
BOOTSTRAP_JS_DEFAULT=NO
NATIVE_MOBILE_APP=NO
```

Research route status:

```text
RESEARCH_ROUTE=INDEPENDENTLY_DERIVED_EXTERNALLY_MODIFIED
```

The earlier high-level `FastAPI + HTML + HTMX-or-Alpine + WebSocket-or-SSE` concept is narrowed to a smaller route. External evidence confirms server-rendered HTML and SSE, but the current htmx major-version transition and lack of need for bidirectional browser streaming justify removing HTMX/Alpine/WebSocket from the V1 default dependency set.

---

## 6. Frozen authority ownership map

### 6.1 Project Strategy / product authority

Project-owned:

- Strategy decision semantics;
- Opportunity / setup / side / version identity;
- project-specific TradePlan / OrderPreview semantics;
- project-specific risk/eligibility/chase/expiry policy;
- exact human approval policy;
- evidence/journal semantics;
- presentation information hierarchy.

### 6.2 Nautilus / mature infrastructure authority

Mature infrastructure owns generic:

- venue connection mechanics;
- order lifecycle;
- fills;
- generic position/account state;
- reconciliation/restart behavior;
- venue order state.

### 6.3 Frontend authority

The browser owns **no trading authority**.

```text
BROWSER_CAN_DISPLAY=YES
BROWSER_CAN_REQUEST_APPROVAL/REJECTION=YES
BROWSER_CAN_COMPUTE_AUTHORITATIVE_RISK=NO
BROWSER_CAN_COMPUTE_AUTHORITATIVE_SIZE=NO
BROWSER_CAN_DECIDE_VALIDITY=NO
BROWSER_CAN_CREATE_EXECUTION_PERMIT=NO
BROWSER_CAN_OWN_ORDER_STATE=NO
BROWSER_CAN_OWN_POSITION_STATE=NO
BROWSER_CAN_HOLD_EXCHANGE_CREDENTIALS=NO
```

The UI server exposes a **rebuildable, non-authoritative presentation projection** derived from current project-domain and Nautilus-owned state.

No browser/localStorage/session state becomes project truth.

---

## 7. Frontend/backend seam

Freeze the conceptual seam, not endpoint filenames:

```text
PROJECT STRATEGY / DOMAIN CONTRACTS
        +
NAUTILUS EXECUTION / RECONCILIATION STATE
        +
APPROVAL / EVIDENCE STATE
        |
        v
SERVER-SIDE OPERATOR VIEW PROJECTION
        |
        +--> JINJA2 HTML INITIAL VIEW
        +--> SSE REVISION / STATUS EVENTS
        |
        v
RESPONSIVE BROWSER SURFACE
        |
        +--> HTTPS POST: APPROVE
        +--> HTTPS POST: REJECT
        |
        v
SERVER RE-READS AUTHORITATIVE STATE
-> REVALIDATES EXACT PROPOSAL / ORDER / EXPIRY / HEALTH / ACCOUNT / POSITION
-> ACCEPTS OR FAILS CLOSED
-> RECORDS DETERMINISTIC RESULT
```

A presentation ViewModel may contain, conceptually:

```text
schema_version
view_revision
generated_at
environment
system_health
market_data_freshness
execution_health
reconciliation_state
kill_or_disengage_state
proposal_identity
strategy/policy/parameter_identity
opportunity_summary
exact_order_preview
proposal_vs_current_diff
approval_state
approval_block_reasons
execution_state
position_summary
evidence_summary
```

This read model is deliberately **not** a second durable authority.

---

## 8. V1 operator screen information hierarchy

The main screen should optimize for a fast decision, not data density.

### Layer A — always visible safety header

Sticky/top priority:

- environment: `SHADOW / ZERO-WRITE / TESTNET / MAINNET_PILOT`;
- overall system readiness;
- market-data freshness;
- Nautilus execution/connection state when applicable;
- account/position reconciliation state when applicable;
- kill/disengage state.

Environment must be expressed in text, not color alone.

### Layer B — opportunity identity

Show only the facts needed to identify the decision:

- instrument;
- side;
- setup / strategy state;
- Strategy/Policy/Parameter version identity;
- proposal creation time;
- expiry / time remaining.

### Layer C — exact transaction being authorized

The review surface must satisfy the transaction-authority principle `What You See Is What You Sign`.

Show the exact significant data relevant to the current order contract, including as applicable:

- order type;
- exact quantity;
- entry/limit/trigger/entry-zone information;
- notional;
- risk amount / risk percent where current policy defines them;
- max slippage;
- time-in-force;
- stop/protection policy;
- take-profit policy;
- cancellation/expiry policy;
- any emergency reduce-only policy covered by the same approval.

### Layer D — Proposal vs Current Diff — safety-critical

This remains one of the highest-value V0 product features.

Show material drift between proposal creation and current authoritative state, including as applicable:

- price movement;
- spread/depth/execution feasibility;
- chase boundary;
- market/regime/invalidation state;
- data freshness;
- account state;
- existing position;
- open orders;
- available risk/margin;
- any reason the original proposal is no longer approvable.

If a material binding changes, do not offer `approve anyway`. The old authorization becomes invalid and the server must require an exact current/new proposal according to the governing contract.

### Layer E — action bar

V1 core actions:

```text
APPROVE
REJECT
```

Refinement versus historical V0:

- `MODIFY` is **not** a default V1 primary action because in-place manual mutation increases UI complexity, attribution ambiguity and approval risk.
- If a later product requirement restores Modify, it must create a **new/superseding Proposal**; it must never mutate the already-reviewed package in place.
- `OBSERVE` does not need a button in V1; not acting is sufficient unless later evidence shows an explicit observation record has material product value.

One explicit Approve action is preferred over routine double-confirm dialogs when the exact significant transaction data is already clearly visible. Double-click/replay safety is enforced server-side through single-use/idempotent authorization; the browser may disable the pressed button only as UX feedback.

### Layer F — execution supervision

After approval, the same surface becomes supervision rather than a second trading terminal.

Human-readable lifecycle may include:

```text
APPROVED
SUBMITTING
ACCEPTED
PARTIAL_FILL
FILLED
PROTECTED
CANCELED
REJECTED
UNKNOWN
RECONCILING
CLOSED
```

Exact labels must ultimately map to accepted project/Nautilus domain semantics; the UI must not invent an independent lifecycle.

`UNKNOWN` and `RECONCILING` are high-salience fail-closed states.

### Layer G — current position and protection

When a position exists, show only essential supervision data:

- current quantity;
- average fill;
- stop/protection state;
- take-profit state;
- realized/unrealized PnL where authoritative;
- fees/funding where authoritative;
- reconciliation state.

### Layer H — secondary detail

Collapsed/secondary by default:

- detailed evidence;
- research fields;
- IDs/hashes;
- full version/provenance detail;
- extended context;
- AI narrative/explanation.

Deterministic facts must remain visually separable from any AI narrative.

---

## 9. Mobile contract

V1 is **responsive web**, not a separate native application.

Required mobile behavior:

```text
ONE_COLUMN_PRIMARY_FLOW=YES
320_CSS_PX_REFLOW_WITHOUT_LOSS=TARGET
HORIZONTAL_SCROLL_FOR_CORE_APPROVAL_FLOW=NO
HOVER_ONLY_INTERACTION=NO
STICKY_MODE/HEALTH_VISIBILITY=YES
STICKY_OR_EASILY_REACHABLE_ACTION_BAR=YES
PRIMARY_TOUCH_TARGET_TARGET=ABOUT_44x44_OR_LARGER
COLOR_AS_SOLE_STATUS_SIGNAL=NO
DENSE_TABLES_FOR_CORE_FLOW=NO
```

Mobile information priority:

```text
MODE / HEALTH
-> OPPORTUNITY IDENTITY + EXPIRY
-> PROPOSAL VS CURRENT DIFF / WARNINGS
-> EXACT ORDER / RISK SUMMARY
-> APPROVE / REJECT
-> EXECUTION / POSITION STATE
-> COLLAPSED DETAILS
```

Use text/key-value stacks rather than desktop-width tables. Long IDs/hashes belong in detail sections and must wrap safely.

No offline transaction authority is allowed. A future installable/PWA shell must not cache or replay approval state unless separately designed and security-reviewed; V1 does not require a service worker.

---

## 10. Browser transport contract

### 10.1 Initial load

Server-rendered HTML over HTTPS.

### 10.2 Live updates

Use one same-origin `EventSource` / SSE channel for server-to-browser state notifications.

Preferred semantic pattern:

```text
SERVER AUTHORITY CHANGES
-> SSE emits view_revision / event kind
-> browser requests/replaces the canonical server-rendered live-state fragment
```

A tiny vanilla-JS adapter may manage:

- one EventSource connection;
- connection-open / connection-error indicator;
- requesting/replacing one bounded server-rendered live-state container;
- pressed/pending visual feedback.

The JavaScript adapter must not interpret trading economics or recreate domain transitions.

### 10.3 Human actions

Approve/Reject are ordinary same-origin state-changing HTTPS requests, preferably normal HTML form semantics.

The client submits only identity/action material needed to bind the request, such as exact proposal/order identity plus CSRF/session material. The client must not be trusted to submit authoritative price/risk/quantity values.

The server re-reads current authoritative state and fails closed on any mismatch/expiry/staleness/reconciliation problem.

After a successful state-changing POST, HTTP `303 See Other` to a canonical GET representation is a suitable standard pattern to avoid accidental form resubmission.

### 10.4 WebSocket

```text
BROWSER_WEBSOCKET_V1=NO_BY_DEFAULT
```

Re-open only when a real product requirement needs continuous bidirectional client-originated streaming that ordinary HTTPS actions cannot express cleanly.

---

## 11. CSS / visual-system route

```text
BOOTSTRAP_REFERENCE_VERSION=5.3.8
BOOTSTRAP_CSS=SELECTED
BOOTSTRAP_JS=NOT_REQUIRED_BY_DEFAULT
CUSTOM_DESIGN_SYSTEM=NO
THIRD_PARTY_CDN=NO
EXTERNAL_FONT=NO_BY_DEFAULT
```

Use Bootstrap’s responsive grid/utilities/forms/buttons as mature commodity primitives and add only narrow project CSS required for information hierarchy/status semantics.

This is not a mandate to make the interface look like default Bootstrap. It is a lifecycle-burden decision: avoid building/maintaining a private responsive CSS system for ordinary layout/forms/buttons.

All static dependencies should be pinned/self-hosted when implementation is later authorized.

---

## 12. Security / integrity frontend contract

The UI is a high-consequence transaction-authorization surface even while V1 is human-confirmed.

Freeze these product/security requirements:

```text
PRIVATE_AUTHENTICATED_OPERATOR_SURFACE=REQUIRED
HTTPS_ONLY=REQUIRED
SAME_ORIGIN_UI_AND_ACTIONS=PREFERRED
CORS_BY_DEFAULT=NO
SECURE_HTTPONLY_SESSION_COOKIE=REQUIRED
SAMESITE_STRICT_PREFERRED_WHEN_COMPATIBLE=YES
__HOST_COOKIE_PREFIX_PREFERRED_WHEN_APPLICABLE=YES
CSRF_PROTECTION_FOR_STATE_CHANGES=REQUIRED
SERVER_SIDE_TRANSACTION_AUTHORIZATION=REQUIRED
CSP=REQUIRED
FRAME_ANCESTORS_NONE=TARGET
FORM_ACTION_SELF=TARGET
NO_THIRD_PARTY_ANALYTICS=YES
NO_THIRD_PARTY_FRONTEND_SCRIPT=YES
NO_BROWSER_EXCHANGE_SECRET=YES
NO_AUTHORITY_IN_LOCALSTORAGE=YES
DYNAMIC_OPERATOR_PAGES_CACHE_CONTROL_NO_STORE=TARGET
```

Exact authentication/ingress provider is **not selected by this frontend research file**. That is a separately scoped Security/Operations infrastructure choice and must not be guessed here. The product requirement is only that the operator surface be private/authenticated and that approval identity be auditable.

SSE disconnect or stale UI state must become clearly visible. Client-side disabling of Approve is only a UX safeguard; the server independently rejects unsafe requests even if the browser is stale or malicious.

---

## 13. Performance / stability contract

Use Core Web Vitals as mature baseline field metrics, separately measured on mobile and desktop:

```text
P75_LCP_TARGET <= 2.5s
P75_INP_TARGET <= 200ms
P75_CLS_TARGET <= 0.1
```

These are UX targets, not execution-safety gates.

Additional architectural principles:

- first meaningful operator state should be rendered server-side;
- no client hydration dependency for core functionality;
- no large JS bundle;
- no charting library in V1;
- no client-side router;
- no frontend state store;
- static assets may use immutable/versioned caching;
- dynamic operator/approval state must not be served from stale shared/browser caches;
- reconnect/freshness state must be visible;
- a live-update transport failure must not silently leave the interface looking current.

No arbitrary sub-100ms UI latency promise is frozen without real end-to-end measurement. Safety is enforced by server revalidation, not by assuming the screen is instantaneous.

---

## 14. Explicit V1 non-goals

Do not include by default:

- TradingView replacement / large charting terminal;
- generic exchange terminal;
- order-book visualization;
- research dashboard;
- strategy parameter editor;
- strategy lifecycle admin console;
- generic portfolio analytics suite;
- multi-user RBAC product;
- AI chat trading interface;
- native iOS/Android application;
- PWA offline execution;
- React/Vue/Svelte SPA;
- WebSocket browser trading protocol;
- browser-side risk/size/execution calculations;
- browser-to-Nautilus direct connection;
- browser-to-Hyperliquid direct connection;
- duplicate journal/OMS/position store in frontend code.

Charts, richer research views, keyboard workflows, native wrappers or richer customization should be added only after observed operator use demonstrates a material need.

---

## 15. Notification boundary

Notification is an attention/recall channel, not an execution authority surface.

Preferred product semantics:

```text
NOTIFICATION:
  opportunity identity
  side / setup
  review required
  deep link to operator surface

DASHBOARD:
  complete current evidence
  exact order preview
  proposal-vs-current diff
  authoritative approval eligibility
  Approve / Reject
```

Approval from Discord/notification messages is not part of V1.

---

## 16. Product-stage alignment without execution authorization

This is a product architecture boundary only, not an implementation sequence or work packet.

The accepted stage logic remains:

```text
NAUTILUS SHADOW
-> FORWARD SHADOW
-> ZERO-WRITE HUMAN APPROVAL
-> SEPARATELY AUTHORIZED TESTNET HUMAN-APPROVED EXECUTION
-> STRATEGY + PRODUCTION NAUTILUS VERSION GATES
-> SEPARATELY AUTHORIZED TINY MAINNET HUMAN-APPROVED CANARY
-> NORMAL HUMAN-APPROVED V0
```

Product implication:

- frontend contracts can be frozen before exchange-write authority exists;
- the first **real operator approval interaction** belongs in the Zero-Write stage;
- the same interaction model should survive into Testnet/Mainnet rather than being redesigned per environment;
- environment authority changes behind the same visible product surface; the browser never infers a higher authority from a lower-stage PASS.

---

## 17. Re-open triggers

Do not broaden the frontend architecture merely because more options exist.

Re-open the relevant decision only when a concrete trigger occurs:

### Re-open HTMX/Turbo or another hypermedia helper if

- native fragment-refresh code begins duplicating material request/swap/error/synchronization logic;
- partial page interaction count or complexity materially expands;
- maintaining the minimal JS adapter becomes more complex than adopting a mature helper.

### Re-open SPA if

- a future product requires substantial client-owned interactive state that cannot remain a rebuildable presentation projection;
- complex local visualization/editing becomes a product P0;
- offline-capable non-authoritative workflows become materially valuable.

### Re-open WebSocket if

- a future product requires continuous bidirectional browser-originated streaming rather than discrete HTTPS actions.

### Re-open native mobile if

- responsive web proves measurably insufficient for required latency, device integration, notification, background behavior or operator usability.

### Re-open charting/research UI if

- observed live use shows the operator cannot make correct/fast decisions without integrated visualization.

---

## 18. Residual uncertainties — deliberately not invented

The following are real later decisions but do not invalidate this frontend/product route:

1. exact authentication / private-ingress provider;
2. exact production HTTP/ASGI server and reverse-proxy topology;
3. exact dependency pins at future implementation time;
4. exact accepted project/Nautilus execution-state vocabulary after the next domain-contract stage;
5. exact Strategy/OrderPreview contract after current Strategy/Nautilus convergence;
6. measured operator latency/refresh thresholds after the Zero-Write environment exists;
7. whether a future Modify action has enough product value to justify reintroduction.

They are not filled with speculative answers in this research record.

---

## 19. Final synthesis / decision

### What external evidence confirms

- server-authoritative transaction authorization is the correct safety model;
- significant order data should be shown exactly before approval;
- server-rendered HTML remains a mature production architecture for responsive live applications;
- SSE is a mature browser-native fit for one-way live state;
- responsive web can cover desktop/mobile without a second app codebase;
- Nautilus should remain the execution/reconciliation authority rather than the UI.

### What external evidence modifies

Earlier candidate:

```text
FastAPI + HTML + HTMX-or-Alpine + WebSocket-or-SSE
```

Refined route:

```text
FastAPI + Jinja2
+ native HTML forms / HTTPS
+ native EventSource / SSE
+ minimal vanilla JS presentation adapter
+ Bootstrap 5.3 CSS-only
```

The change is driven by lower lifecycle burden and the timing risk of htmx 4.0’s very recent major release, not by rejection of hypermedia architecture.

### What is rejected for V1

- SPA by default;
- client-side trading state;
- browser WebSocket by default;
- HTMX/Alpine/Turbo dependency by default;
- Streamlit as execution-authority UI;
- Phoenix/Elixir second runtime;
- large dashboard/terminal/charting scope;
- native mobile app;
- in-place manual modification of an already-reviewed order package.

### Final decision

```text
FRONTEND_PRODUCT_TARGET=LEAN_HUMAN_APPROVAL_AND_EXECUTION_SUPERVISION_SURFACE
FRONTEND_ARCHITECTURE=SERVER_AUTHORITATIVE_RESPONSIVE_WEB
BACKEND_WEB_OWNER=FASTAPI_FAMILY
TEMPLATE_OWNER=JINJA2
LIVE_BROWSER_TRANSPORT=SSE_EVENTSOURCE
CLIENT_ACTION_TRANSPORT=HTTPS_FORM_POST
CLIENT_JS=MINIMAL_PRESENTATION_ONLY
RESPONSIVE_CSS=BOOTSTRAP_5_3_CSS_ONLY
MOBILE=FIRST_CLASS_RESPONSIVE_WEB
SPA=NO_V1
HTMX=DEFERRED_REOPEN_TRIGGER_ONLY
WEBSOCKET_BROWSER_CHANNEL=NO_V1_BY_DEFAULT
NAUTILUS_GENERIC_EXECUTION_AUTHORITY=KEEP
BROWSER_TRADING_AUTHORITY=NONE
CORE_ACTIONS=APPROVE_REJECT
MODIFY=DEFERRED_UNLESS_LATER_JUSTIFIED_AND_MUST_CREATE_NEW_PROPOSAL
AI_EXPLANATION=SECONDARY_NONBLOCKING
CHARTING=NO_V1
RESEARCH_ROUTE=INDEPENDENTLY_DERIVED_EXTERNALLY_MODIFIED
```

This decision intentionally optimizes for the smallest stable system that can support frequent human trading decisions accurately and quickly. Future visual/product richness is subordinate to measured operator need.
