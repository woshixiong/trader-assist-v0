import json
import os

import pytest
from test_research_data_contracts import H, dataset, rights

from trader_assist_v0.research_data.okx_public import (
    OKXOpenInterestRequest,
    OKXPublicOIProfile,
    fetch_okx_open_interest,
)


def spec(**updates):
    values = dict(
        version="v1",
        profile=OKXPublicOIProfile.create(
            version="v1",
            profile="OKX_GLOBAL_PUBLIC",
            base_url="https://www.okx.com",
            source_locator="https://www.okx.com/docs-v5/en/#public-data-rest-api-get-open-interest",
            source_document_hash=H,
            observed_date="2026-10-04",
        ),
        inst_id="ETH-USDT-SWAP",
        base_currency="ETH",
        timeout_seconds=2,
        max_bytes=4096,
    )
    values.update(updates)
    return OKXOpenInterestRequest.create(**values)


def body(**updates):
    item = dict(instType="SWAP", instId="ETH-USDT-SWAP", oi="10", oiCcy="20", oiUsd="30", ts="100")
    item.update(updates)
    return {"code": "0", "data": [item]}


class OfflineResponse:
    status = 200

    def __init__(self, raw, url):
        self.raw, self.url, self.closed = raw, url, False

    def geturl(self):
        return self.url

    def read(self, size):
        return self.raw[:size]

    def close(self):
        self.closed = True


def fetch(raw=None, manifest=None, request=None, calls=None):
    calls = [] if calls is None else calls
    request = spec() if request is None else request

    def opener(req, *, timeout):
        calls.append((req.full_url, req.get_method(), timeout))
        return OfflineResponse(json.dumps(body()).encode() if raw is None else raw, req.full_url)

    return fetch_okx_open_interest(
        request,
        dataset() if manifest is None else manifest,
        capability_hash=H,
        observed_at=lambda: 300_000_000,
        use="PIPELINE_CORRECTNESS_ONLY",
        opener=opener,
    )


def test_offline_identity_units_timestamp_and_single_call(monkeypatch):
    class NoEnvironment(dict):
        def get(self, *args):
            raise AssertionError("environment read")

        def __getitem__(self, key):
            raise AssertionError("environment read")

    monkeypatch.setattr(os, "environ", NoEnvironment())
    calls = []
    event = fetch(calls=calls)
    assert calls == [(spec().url, "GET", 2)]
    assert (event.payload.oi, event.payload.oi_ccy, event.payload.oi_usd) == ("10", "20", "30")
    assert event.timestamps.ts_event == 100_000_000
    assert event.timestamps.observed_at_ns == 300_000_000
    assert event.timestamps.true_network_receive_ts is None
    assert event.authority == "EXTERNAL_REFERENCE"


@pytest.mark.parametrize("eligibility", ["UNKNOWN", "PROHIBITED"])
def test_rights_before_opener(eligibility):
    calls = []
    with pytest.raises(PermissionError):
        fetch(manifest=dataset(rights=rights(eligibility=eligibility)), calls=calls)
    assert calls == []


@pytest.mark.parametrize(
    "updates",
    [
        {"instType": "FUTURES"},
        {"instId": "BTC-USDT-SWAP"},
        {"oi": "NaN"},
        {"oiCcy": "-1"},
        {"oiUsd": 3.0},
        {"ts": None},
        {"ts": ""},
    ],
)
def test_strict_fields(updates):
    with pytest.raises((ValueError, KeyError)):
        fetch(json.dumps(body(**updates)).encode())


@pytest.mark.parametrize(
    "raw",
    [
        b"not json",
        b"x" * 4097,
        b'{"code":"1","data":[]}',
        b'{"code":0,"data":[]}',
        b'{"code":"0","data":[]}',
        b'{"code":"0","code":"0","data":[]}',
        json.dumps({"code": "0", "data": body()["data"] * 2}).encode(),
    ],
)
def test_response_failure(raw):
    with pytest.raises(ValueError):
        fetch(raw)


def test_no_retry():
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise OSError("transport failed")

    with pytest.raises(OSError):
        fetch_okx_open_interest(
            spec(),
            dataset(),
            capability_hash=H,
            observed_at=lambda: 1,
            use="PIPELINE_CORRECTNESS_ONLY",
            opener=fail,
        )
    assert calls == [1]


@pytest.mark.parametrize(
    "url", ["http://www.okx.com", "https://evil.example", "https://www.okx.com@evil.example"]
)
def test_unapproved_profile(url):
    with pytest.raises(ValueError):
        OKXPublicOIProfile.create(
            version="v1",
            profile="OKX_GLOBAL_PUBLIC",
            base_url=url,
            source_locator=spec().profile.source_locator,
            source_document_hash=H,
            observed_date="2026-10-04",
        )


@pytest.mark.parametrize(
    "override",
    [
        {"rights": None},
        {"rights": rights(intended_use="LIVE_CONTEXT")},
        {"rights": rights(attribution_constraints=("credit-source",))},
        {"rights": rights(retention_constraints=("expire-cut",))},
        {"exposure_state": "FINAL_LOCKBOX_SEALED"},
    ],
)
def test_role_constraints_and_sealed_refuse_before_opener(override):
    calls = []
    with pytest.raises(PermissionError):
        fetch(manifest=dataset(**override), calls=calls)
    assert calls == []


@pytest.mark.parametrize("field", ["oi", "oiCcy", "oiUsd", "ts", "instId", "instType"])
def test_missing_fields_never_substituted(field):
    response = body()
    del response["data"][0][field]
    with pytest.raises((KeyError, ValueError)):
        fetch(json.dumps(response).encode())


def test_redirect_rejected_and_response_closed():
    response = OfflineResponse(json.dumps(body()).encode(), "https://evil.example")
    with pytest.raises(ValueError, match="redirect"):
        fetch_okx_open_interest(
            spec(),
            dataset(),
            capability_hash=H,
            observed_at=lambda: 1,
            use="PIPELINE_CORRECTNESS_ONLY",
            opener=lambda *a, **k: response,
        )
    assert response.closed


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan"), 31])
def test_finite_timeout(timeout):
    with pytest.raises(ValueError):
        spec(timeout_seconds=timeout)


def test_stdlib_opener_has_no_ambient_proxy_or_redirect(monkeypatch):
    from urllib.request import ProxyHandler

    import trader_assist_v0.research_data.okx_public as module

    handlers = []

    class OfflineOpener:
        def open(self, request, *, timeout):
            return OfflineResponse(json.dumps(body()).encode(), request.full_url)

    def build(*args):
        handlers.extend(args)
        return OfflineOpener()

    monkeypatch.setattr(module, "build_opener", build)
    event = fetch_okx_open_interest(
        spec(),
        dataset(),
        capability_hash=H,
        observed_at=lambda: 300_000_000,
        use="PIPELINE_CORRECTNESS_ONLY",
    )
    assert event.timestamps.true_network_receive_ts is None
    assert isinstance(handlers[0], ProxyHandler) and handlers[0].proxies == {}
    with pytest.raises(ValueError, match="redirect"):
        handlers[1].redirect_request(None, None, 302, "redirect", {}, "https://evil.example")
