"""Mock-only transport contract tests; NEVER open a live network connection."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256

import pytest

from trader_assist_v0.research_data.binance_archive import (
    DAY_NS,
    MAX_CHECKSUM_BYTES,
    MAX_ZIP_BYTES,
    HttpResponse,
    frozen_archive_objects,
)
from trader_assist_v0.research_data.binance_research_transport import (
    DECISION_URL,
    TERMS_SHA256,
    TERMS_URL,
    MockOnlyResearchTransport,
    PinnedHttpsResearchTransport,
    _exact_url,
    mock_checksum_receipt,
    require_candidate_rights,
)
from trader_assist_v0.research_data.contracts import SourceRightsProvenance

# Rights-shaped *fake* record: not permission to contact Binance.
CONSTRAINTS = frozenset({"ATTRIBUTION_RETAINED", "LICENSE_RETAINED"})


def mock_rights(**kw):
    data = dict(
        version="G0_RIGHTS_SHAPE_MOCK_V1",
        terms_locator=TERMS_URL, observed_version="1.0",
        observed_date="2026-08-26", terms_hash=TERMS_SHA256,
        intended_use="STRATEGY_DEV_RESEARCH", eligibility="ALLOWED",
        decision_locator=DECISION_URL, attribution_constraints=("ATTRIBUTION_RETAINED",),
        retention_constraints=("LICENSE_RETAINED",), synthetic=False,
    )
    data.update(kw)
    return SourceRightsProvenance.create(**data)


def response(url, body, *, status=200, redirected=False):
    return HttpResponse(
        url, status, (("Content-Length", str(len(body))),), body, redirected,
    )


def test_pinned_full_identity_roster_and_reserve_no_payload():
    items = frozen_archive_objects()
    assert len(items) == 256
    assert len({obj.zip_url for obj in items}) == 256
    assert sum(obj.role_intent == "CURRENT_DEV" for obj in items) == 240
    assert sum(obj.role_intent == "FUTURE_DEV_RESERVE" for obj in items) == 8
    assert sum(obj.role_intent == "CERTIFICATION_RESERVE" for obj in items) == 8
    for obj in items:
        assert _exact_url(obj, "CHECKSUM") == (obj.checksum_url, MAX_CHECKSUM_BYTES)
        if obj.role_intent == "CURRENT_DEV":
            assert _exact_url(obj, "ZIP") == (obj.zip_url, MAX_ZIP_BYTES)
        else:
            with pytest.raises(PermissionError, match="reserve"):
                _exact_url(obj, "ZIP")


@pytest.mark.parametrize(
    "kw",
    [
        dict(terms_locator="https://evil.example/terms"),
        dict(terms_hash="b" * 64), dict(observed_version="2.0"),
        dict(observed_date="2024-01-01"),
        dict(decision_locator="synthetic://forged"),
        dict(eligibility="UNKNOWN"), dict(eligibility="PROHIBITED"),
        dict(synthetic=True), dict(intended_use="LIVE_SIGNAL"),
        dict(attribution_constraints=()), dict(retention_constraints=()),
    ],
)
def test_fake_caller_rights_never_elevate_unpinned_claims(kw):
    with pytest.raises(PermissionError):
        require_candidate_rights(mock_rights(**kw), CONSTRAINTS)


def test_rights_constraint_satisfaction_required_even_in_fake_shape():
    assert require_candidate_rights(mock_rights(), CONSTRAINTS) == mock_rights()
    with pytest.raises(PermissionError, match="constraints"):
        require_candidate_rights(mock_rights(), frozenset())


def test_real_network_denied_even_with_perfect_fake_rights_and_no_socket(monkeypatch):
    def never_network(*args, **kwargs):
        pytest.fail("external HTTP was reached in mock-only phase")

    monkeypatch.setattr("urllib.request.build_opener", never_network)
    item = frozen_archive_objects()[0]
    client = PinnedHttpsResearchTransport()
    for kind in ("CHECKSUM", "ZIP"):
        with pytest.raises(PermissionError, match="REAL_PROVIDER_IO_NOT_AUTHORIZED"):
            client.request(item, kind, rights=mock_rights(), satisfied=CONSTRAINTS)
    bad = replace(item, zip_url=item.zip_url.replace("https://", "http://"))
    with pytest.raises(ValueError):
        client.request(bad, "CHECKSUM", rights=mock_rights(), satisfied=CONSTRAINTS)
    reserve = next(obj for obj in frozen_archive_objects()
                   if obj.role_intent == "CERTIFICATION_RESERVE")
    with pytest.raises(PermissionError, match="reserve"):
        client.request(reserve, "ZIP", rights=mock_rights(), satisfied=CONSTRAINTS)


def test_in_memory_checksum_receipt_is_not_provider_evidence():
    item = frozen_archive_objects()[0]
    digest = sha256(b"purely generated synthetic test fixture").hexdigest()
    checksum = (digest + "  " + item.zip_name + "\n").encode("ascii")
    mock = MockOnlyResearchTransport((response(item.checksum_url, checksum),))
    retrieved = item.end_ns + DAY_NS
    receipt = mock_checksum_receipt(item, mock, retrieved_at_ns=retrieved)
    assert receipt.archive_sha256 == digest
    assert receipt.retrieved_at_ns == retrieved
    assert receipt.retrieval_identity.startswith("synthetic://")
    assert len(mock.responses) == 1


def test_mock_http_rejects_redirect_html_oversize_wrong_path_and_duplicate():
    item = frozen_archive_objects()[0]
    cases = (
        response(item.checksum_url, b"x", redirected=True),
        response(item.checksum_url, b"HTML", status=302),
        response(item.checksum_url, b"y" * (MAX_CHECKSUM_BYTES + 1)),
    )
    for invalid in cases:
        mock = MockOnlyResearchTransport((invalid,))
        with pytest.raises(ValueError):
            mock.request(item, "CHECKSUM")
    with pytest.raises(ValueError):
        MockOnlyResearchTransport(()).request(item, "CHECKSUM")
    good = response(item.checksum_url, b"not a checksum")
    with pytest.raises(ValueError):
        MockOnlyResearchTransport((good, good)).request(item, "CHECKSUM")
    with pytest.raises(ValueError):
        mock_checksum_receipt(
            item, MockOnlyResearchTransport((good,)),
            retrieved_at_ns=item.end_ns + DAY_NS,
        )
    other_host = replace(item, zip_url=item.zip_url.replace(
        "data.binance.vision", "other.example"
    ))
    with pytest.raises(ValueError):
        _exact_url(other_host, "CHECKSUM")
