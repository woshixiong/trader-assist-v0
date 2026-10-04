"""C1 observation, recovery and real HTTP/ASGI authority-seam simulations."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import sqlite3
import subprocess
import threading
import time
from pathlib import Path

import pytest
from starlette.requests import Request
from test_three_setup_operator_contracts import (
    make_config,
    make_credential,
    make_health,
    make_source,
)

from trader_assist_v0.multi_asset_shadow.shadow_records.store import EvidenceStore
from trader_assist_v0.operator import service
from trader_assist_v0.operator.approval import OperatorBlocked, OperatorEngine
from trader_assist_v0.operator.contracts import RUNTIME_HEALTH_FILENAME, ReconcilerStatus
from trader_assist_v0.operator.dashboard import build_dashboard
from trader_assist_v0.operator.runtime_health import MAX_SNAPSHOT_BYTES, read_runtime_health
from trader_assist_v0.operator.security import OperatorSecurity


def _now() -> int:
    return time.time_ns() // 1_000_000


def _request(
    method: str,
    path: str,
    *,
    cookie: str,
    origin: str | None = None,
    csrf: str | None = None,
    json_body: dict[str, str] | None = None,
) -> Request:
    body = b"" if json_body is None else json.dumps(json_body).encode()
    headers = [
        (b"host", b"operator.test"),
        (b"cookie", f"__Host-ts8-session={cookie}".encode()),
    ]
    if origin is not None:
        headers.append((b"origin", origin.encode()))
    if csrf is not None:
        headers.append((b"x-csrf-token", csrf.encode()))
    if json_body is not None:
        headers.append((b"content-type", b"application/json"))

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "https",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": ("operator.test", 443),
        },
        receive,
    )


def _endpoint(app: object, path: str, method: str) -> object:
    return next(
        route.endpoint
        for route in app.routes  # type: ignore[attr-defined]
        if getattr(route, "path", "") == path
        and method in (getattr(route, "methods", set()) or set())
    )


@pytest.mark.parametrize("raw", [
    b"{", b"{}", b"null", b"[]", b"\xff", b"x" * (MAX_SNAPSHOT_BYTES + 1),
])
def test_invalid_snapshot_recovers_without_reset(tmp_path: Path, raw: bytes) -> None:
    evidence = tmp_path / "evidence.sqlite"
    path = evidence.with_name(RUNTIME_HEALTH_FILENAME)
    assert not read_runtime_health(evidence, now_ms=1000).ready
    assert not path.exists()  # reader never creates state
    path.write_bytes(raw)
    assert read_runtime_health(evidence, now_ms=1000).reasons == ("RUNTIME_HEALTH_INVALID",)
    make_health(evidence, observed_ms=1000)
    assert read_runtime_health(evidence, now_ms=1000).ready


@pytest.mark.parametrize("changes,reason", [
    ({"running": False}, "RUNTIME_NOT_RUNNING"),
    ({"data_ready": False}, "RUNTIME_DATA_NOT_READY"),
    ({"stream_health": "DISCONNECTED"}, "RUNTIME_STREAM_NOT_HEALTHY"),
    ({"stream_health": "REESTABLISHING"}, "RUNTIME_STREAM_NOT_HEALTHY"),
    ({"continuity_requirements_remaining": 1}, "RUNTIME_CONTINUITY_PENDING"),
    ({"warmup_readiness": "NOT_READY"}, "RUNTIME_WARMUP_NOT_READY"),
    ({"storage_failures": 1}, "RUNTIME_STORAGE_FAILURE"),
    ({"observed_ms": 1001}, "RUNTIME_HEALTH_FUTURE"),
    ({"observed_ms": 0}, "RUNTIME_HEALTH_STALE"),
    ({"running": "true"}, "RUNTIME_HEALTH_INVALID"),
    ({"data_ready": 1}, "RUNTIME_HEALTH_INVALID"),
    ({"stream_health": "UNKNOWN"}, "RUNTIME_HEALTH_INVALID"),
    ({"publication_interval_ms": 60_001}, "RUNTIME_HEALTH_INVALID"),
    ({"schema_version": "v2"}, "RUNTIME_HEALTH_INVALID"),
])
def test_independent_runtime_blockers(
    tmp_path: Path, changes: dict[str, object], reason: str,
) -> None:
    evidence = tmp_path / "evidence.sqlite"
    now = 20_000 if changes.get("observed_ms") == 0 else 1000
    make_health(evidence, observed_ms=1000,
                **{k: v for k, v in changes.items() if k != "observed_ms"})
    if "observed_ms" in changes:
        path = evidence.with_name(RUNTIME_HEALTH_FILENAME)
        value = json.loads(path.read_bytes())
        value.update(changes)
        path.write_text(json.dumps(value))
    assert reason in read_runtime_health(evidence, now_ms=now).reasons


@pytest.mark.parametrize("interval,limit", [(1000, 15_000), (5000, 15_000), (60_000, 180_000)])
def test_runtime_death_ages_observation_not_quote(
    tmp_path: Path, interval: int, limit: int,
) -> None:
    evidence = tmp_path / "evidence.sqlite"
    path = make_health(evidence, observed_ms=1000, publication_interval_ms=interval)
    original = path.read_bytes()
    assert read_runtime_health(evidence, now_ms=1000 + limit).ready
    assert read_runtime_health(evidence, now_ms=1001 + limit).reasons == ("RUNTIME_HEALTH_STALE",)
    assert path.read_bytes() == original  # no quote inspection, provider request or recovery write
    make_health(evidence, observed_ms=1001 + limit, publication_interval_ms=interval)
    assert read_runtime_health(evidence, now_ms=1001 + limit).ready


def test_cold_idle_then_exact_package_and_runtime_recovery(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    engine = OperatorEngine(config)
    with EvidenceStore(config.runtime_evidence_path):
        pass
    assert build_dashboard(engine, config).overall == "BLOCKED"
    make_health(config.runtime_evidence_path, observed_ms=_now())
    idle = build_dashboard(engine, config)
    assert idle.overall == "READY" and idle.state == "NO_OPPORTUNITY"
    assert idle.package_gate == "BLOCKED"
    make_source(config.runtime_evidence_path, created_ms=_now())
    assert build_dashboard(engine, config).package_gate == "PASS"
    for changes in (
        {"stream_health": "DISCONNECTED"},
        {"stream_health": "REESTABLISHING"},
        {"continuity_requirements_remaining": 1},
    ):
        make_health(config.runtime_evidence_path, observed_ms=_now(), **changes)
        assert build_dashboard(engine, config).package_gate == "BLOCKED"
        make_health(config.runtime_evidence_path, observed_ms=_now())
        assert build_dashboard(engine, config).package_gate == "PASS"


def test_new_approve_rereads_health_but_committed_replay_does_not(tmp_path: Path) -> None:
    now = _now()
    config = make_config(tmp_path)
    make_source(config.runtime_evidence_path, created_ms=now)
    engine = OperatorEngine(config)
    package = engine.latest(now_ms=now)[0].package
    args = {
        "shadow_id": package.parent_strategy_order_id, "package_id": package.package_id,
        "package_hash": package.package_hash, "action_key": "health-reread-action-1234",
        "action": "APPROVE", "session_id": "session",
    }
    runtime_before = config.runtime_evidence_path.read_bytes()
    assert build_dashboard(engine, config).package_gate == "PASS"
    path = make_health(config.runtime_evidence_path, observed_ms=now, stream_health="DISCONNECTED")
    with pytest.raises(OperatorBlocked, match="STREAM_NOT_HEALTHY"):
        engine.human_action_record(**args, now_ms=now + 1)
    with sqlite3.connect(config.operator_ledger_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM ts8_actions").fetchone()[0] == 0
    make_health(config.runtime_evidence_path, observed_ms=now)
    with pytest.raises(OperatorBlocked, match="HEALTH_STALE"):
        engine.human_action_record(**args, now_ms=now + 15_001)
    result = engine.human_action_record(**args, now_ms=now + 1)
    assert config.runtime_evidence_path.read_bytes() == runtime_before
    path.unlink()
    config.runtime_evidence_path.unlink()
    assert engine.human_action_record(**args, now_ms=now + 20_000) == result
    assert result.state == "NO_SUBMIT"
    with sqlite3.connect(config.operator_ledger_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM ts8_actions").fetchone()[0] == 1
        assert connection.execute("SELECT submission_status FROM ts8_state").fetchone()[0] == (
            "NOT_SUBMITTED"
        )


def test_display_events_failure_degrades_without_blocking_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config(tmp_path)
    make_source(config.runtime_evidence_path, created_ms=_now())
    engine = OperatorEngine(config)
    import trader_assist_v0.operator.dashboard as dashboard
    monkeypatch.setattr(dashboard, "_recent_events", lambda _path: ((), False))
    model = build_dashboard(engine, config)
    assert model.overall == "DEGRADED" and model.package_gate == "PASS"


def test_source_operational_failure_preserves_health_and_programming_defect_surfaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = make_config(tmp_path)
    make_source(config.runtime_evidence_path, created_ms=_now())
    engine = OperatorEngine(config)
    def fail(**_kwargs: object) -> object:
        raise OperatorBlocked("operational source failure")
    monkeypatch.setattr(engine, "latest", fail)
    model = build_dashboard(engine, config)
    assert model.overall == "BLOCKED" and model.runtime_health.ready
    def defect(**_kwargs: object) -> object:
        raise TypeError("programming defect")
    monkeypatch.setattr(engine, "latest", defect)
    with pytest.raises(TypeError, match="programming defect"):
        build_dashboard(engine, config)


@pytest.mark.parametrize("surface", ["dashboard", "sse"])
def test_slow_display_or_sse_does_not_block_event_loop_or_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, surface: str,
) -> None:
    config = make_config(tmp_path)
    make_source(config.runtime_evidence_path, created_ms=_now())
    engine = OperatorEngine(config)
    package = engine.latest()[0].package
    credential = make_credential()
    app = service.create_app(config, credential, engine=engine)
    session, cookie = OperatorSecurity(config, credential).issue(authenticated=True)
    entered, release = threading.Event(), threading.Event()
    owner = threading.get_ident()
    original = service.build_dashboard if surface == "dashboard" else engine.revision

    def slow(*args: object, **kwargs: object) -> object:
        assert threading.get_ident() != owner
        entered.set()
        assert release.wait(5)
        return original(*args, **kwargs)  # type: ignore[arg-type]

    if surface == "dashboard":
        monkeypatch.setattr(service, "build_dashboard", slow)
    else:
        monkeypatch.setattr(engine, "revision", slow)

    async def exercise() -> None:
        dashboard_endpoint = _endpoint(app, "/", "GET")
        events_endpoint = _endpoint(app, "/events", "GET")
        action_endpoint = _endpoint(app, "/api/action", "POST")
        iterator = None
        if surface == "dashboard":
            display = asyncio.create_task(
                dashboard_endpoint(_request("GET", "/", cookie=cookie))  # type: ignore[operator]
            )
        else:
            response = await events_endpoint(  # type: ignore[operator]
                _request("GET", "/events", cookie=cookie)
            )
            iterator = response.body_iterator
            display = asyncio.create_task(anext(iterator))
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            await asyncio.sleep(0)
            result = await asyncio.wait_for(
                action_endpoint(  # type: ignore[operator]
                    _request(
                        "POST",
                        "/api/action",
                        cookie=cookie,
                        origin=config.allowed_origin,
                        csrf=session.csrf,
                        json_body={
                            "shadow_id": package.parent_strategy_order_id,
                            "package_id": package.package_id,
                            "package_hash": package.package_hash,
                            "action_key": "independent-action-123456",
                            "action": "APPROVE",
                        },
                    )
                ),
                2,
            )
            assert result.status_code == 200
            assert json.loads(result.body)["submission_status"] == "NOT_SUBMITTED"
            assert not display.done()
        finally:
            release.set()
            await asyncio.wait_for(display, 2)
            if iterator is not None:
                await iterator.aclose()

    asyncio.run(exercise())


def test_reconciler_failure_visible_nonblocking_and_automatically_clears(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    config = make_config(tmp_path).model_copy(update={"reconcile_interval_ms": 100})
    make_source(config.runtime_evidence_path, created_ms=_now())
    engine = OperatorEngine(config)
    calls = 0

    def reconcile() -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise sqlite3.OperationalError("injected reconciler failure")
        return 0

    monkeypatch.setattr(engine, "reconcile_once", reconcile)
    app = service.create_app(config, make_credential(), engine=engine)
    session, cookie = OperatorSecurity(config, make_credential()).issue(authenticated=True)

    async def wait_status(failing: bool) -> ReconcilerStatus:
        async with asyncio.timeout(2):
            while True:
                status = app.state.reconciler_status
                if status.last_pass_ms is not None and bool(status.current_error) == failing:
                    return status
                await asyncio.sleep(0.001)

    async def exercise() -> None:
        dashboard_endpoint = _endpoint(app, "/", "GET")
        action_endpoint = _endpoint(app, "/api/action", "POST")
        async with app.router.lifespan_context(app):
            failed = await wait_status(True)
            assert failed.consecutive_failures == failed.failure_count == 1
            assert failed.last_success_ms is None
            page = await dashboard_endpoint(  # type: ignore[operator]
                _request("GET", "/", cookie=cookie)
            )
            text = page.body.decode()
            assert "OPERATOR_RECONCILER_FAILED" in text
            assert "Trade Gate: PASS" in text
            package = engine.latest()[0].package
            result = await action_endpoint(  # type: ignore[operator]
                _request(
                    "POST",
                    "/api/action",
                    cookie=cookie,
                    origin=config.allowed_origin,
                    csrf=session.csrf,
                    json_body={
                        "shadow_id": package.parent_strategy_order_id,
                        "package_id": package.package_id,
                        "package_hash": package.package_hash,
                        "action_key": "reconciler-independent-1234",
                        "action": "APPROVE",
                    },
                )
            )
            assert result.status_code == 200
            recovered = await wait_status(False)
            assert recovered.consecutive_failures == 0 and recovered.failure_count == 1
            assert recovered.last_success_ms is not None and recovered.last_duration_ms >= 0

    with caplog.at_level(logging.ERROR, logger="trader_assist_v0.operator"):
        asyncio.run(exercise())
    record = next(r for r in caplog.records if "OPERATOR_RECONCILER_FAILURE" in r.message)
    assert record.exc_info is not None


def test_browser_executes_stale_health_only_recovery_sse_fallback_and_direct_post(
    tmp_path: Path,
) -> None:
    node = shutil.which("node")
    assert node is not None, "C1 browser evidence requires the already-available JS runtime"
    script = Path("src/trader_assist_v0/operator/static/operator.js").resolve()
    harness = tmp_path / "browser.cjs"
    harness.write_text(r'''
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
class Button { constructor() { this.disabled = false; this.value = "APPROVE"; } }
class Form {
  constructor(view) { this.buttons = view.buttons; this.classList = {contains: () => true}; }
  querySelectorAll() { return this.buttons; }
}
global.HTMLFormElement = Form;
global.HTMLButtonElement = Button;
global.FormData = class {
  get(key) { return key === "action_key" ? "unchanged-action-key" : "a".repeat(64); }
};
function view(gate = "PASS") {
  const v = {
    dataset: {csrf: "csrf", revision: "1", packageId: "package",
              state: "AWAITING_HUMAN_APPROVAL", packageGate: gate},
    buttons: [new Button()], status: {textContent: "Current server view"},
    result: {textContent: ""},
    querySelector(selector) {
      if (selector === "[data-browser-status]") return this.status;
      if (selector === "#action-result") return this.result;
      return null;
    },
    querySelectorAll() { return this.buttons; },
    replaceWith(next) { current = next; },
  };
  if (gate !== "PASS") v.buttons.forEach(b => b.disabled = true);
  return v;
}
let current = view();
let submit;
const intervals = new Map();
global.document = {
  getElementById(id) { return id === "dashboard" ? current : null; },
  addEventListener(name, callback) { assert.equal(name, "submit"); submit = callback; },
};
global.setInterval = (callback, ms) => { intervals.set(ms, callback); };
let events;
global.EventSource = class {
  constructor(path) { assert.equal(path, "/events"); this.listeners = {}; events = this; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
};
global.DOMParser = class {
  parseFromString(text) { return {getElementById: () => text === "missing" ? null : view(text)}; }
};
const pending = [];
const requests = [];
global.fetch = async (path, options) => {
  requests.push(path);
  const response = pending.shift();
  assert(response, `unexpected fetch ${path}`);
  assert.equal(response.path || "/", path);
  if (path === "/") assert.equal(options.cache, "no-store");
  if (path === "/api/action") assert.equal(options.method, "POST");
  if (response.error) throw Error("network unavailable");
  if (response.wait) return response.wait;
  return {ok: response.ok !== false, text: async () => response.text || "PASS"};
};
vm.runInThisContext(fs.readFileSync(process.argv[2], "utf8"));
const flush = () => new Promise(resolve => setImmediate(resolve));
async function tick(response) { pending.push(response); intervals.get(5000)(); await flush(); }
async function click(...responses) {
  pending.push(...responses);
  const form = new Form(current);
  await submit({target: form, submitter: form.buttons[0], preventDefault() {}});
  await flush();
}
(async () => {
  await tick({error: true});
  assert.equal(current.dataset.freshness, "STALE");
  assert(current.status.textContent.includes("DEGRADED"));
  assert(current.buttons.every(b => b.disabled));
  const count = requests.length;
  await submit({target: new Form(current), submitter: current.buttons[0], preventDefault() {}});
  assert.equal(requests.length, count); // stale client cannot initiate a new action
  await tick({ok: false});
  assert(current.buttons.every(b => b.disabled));
  await tick({text: "missing"});
  assert(current.buttons.every(b => b.disabled));
  const staleView = current;
  await tick({text: "PASS"});
  assert.notEqual(current, staleView); // unchanged package/revision still replaces
  assert(!current.buttons[0].disabled);
  await tick({text: "BLOCKED"});
  assert(current.buttons.every(b => b.disabled));
  pending.push({text: "PASS"});
  events.listeners.error(); // native SSE failure -> existing authoritative GET
  await flush();
  assert(!current.buttons[0].disabled);
  await click({path: "/api/action", ok: false}, {error: true});
  assert.equal(current.dataset.freshness, "STALE");
  assert(current.buttons.every(b => b.disabled)); // failed action never enables stale controls
  await tick({text: "PASS"});
  const offset = requests.length;
  await click({path: "/api/action"}, {text: "BLOCKED"});
  assert.deepEqual(requests.slice(offset), ["/api/action", "/"]); // direct POST first
  assert(current.buttons.every(b => b.disabled));
  let resolve;
  pending.push({wait: new Promise(r => { resolve = r; })});
  const before = requests.length;
  intervals.get(5000)(); intervals.get(5000)();
  assert.equal(requests.length, before + 1); // bounded in-flight refresh
  resolve({ok: true, text: async () => "PASS"});
  await flush();
  assert(!current.buttons[0].disabled);
  assert.equal(pending.length, 0);
  process.stdout.write("C1 browser recovery PASS\n");
})().catch(error => { console.error(error); process.exitCode = 1; });
''', encoding="utf-8")
    result = subprocess.run([node, str(harness), str(script)], capture_output=True, text=True,
                            timeout=10, check=False)
    assert result.returncode == 0, result.stderr
    assert "C1 browser recovery PASS" in result.stdout
