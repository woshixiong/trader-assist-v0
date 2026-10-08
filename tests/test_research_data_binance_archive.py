"""Pure synthetic Binance USD-M archive integrity/transport regression tests.

No network, Binance payload, or historical provider observations are used.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import replace

import pytest

from trader_assist_v0.research_data.binance_archive import (
    DAY_NS,
    MAX_CHECKSUM_BYTES,
    MAX_ZIP_BYTES,
    ArchiveObject,
    HttpResponse,
    checked_http_response,
    checksum_receipt,
    frozen_archive_objects,
    parse_verified_daily_zip,
    require_frozen_object,
)


OFFICIAL_HEADER = (
    "open_time,open,high,low,close,volume,close_time,quote_volume,"
    "count,taker_buy_volume,taker_buy_quote_volume,ignore"
)


def obj() -> ArchiveObject:
    return frozen_archive_objects()[0]


def rows(item: ArchiveObject, *, ignore: str = "12.5") -> list[str]:
    start_ms = item.start_ns // 1_000_000
    return [
        f"{start_ms + 300000 * index},10.000,11.000,9.000,10.500,1.5,"
        f"{start_ms + 300000 * index + 299999},15.750,2,0.5,5.25,{ignore}"
        for index in range(288)
    ]


def zipped(item: ArchiveObject, lines: list[str] | None = None, *,
           name: str | None = None, extra: bool = False) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        handle.writestr(
            name or item.csv_name, "\n".join(lines if lines is not None else rows(item))
        )
        if extra:
            handle.writestr("extra.csv", "NOT_ALLOWED")
    return buffer.getvalue()


def receipt(item: ArchiveObject, payload: bytes, **changes):
    from hashlib import sha256

    raw = (sha256(payload).hexdigest() + "  " + item.zip_name + "\n").encode()
    kw = dict(retrieved_at_ns=item.end_ns + DAY_NS, retrieval_identity="synthetic://offline")
    kw.update(changes)
    return checksum_receipt(item, raw, **kw)


def test_frozen_source_ledger_is_exact_and_pre_outcome():
    items = frozen_archive_objects()
    assert len(items) == 256
    assert len({x.zip_url for x in items}) == 256
    assert sum(x.role_intent == "CURRENT_DEV" for x in items) == 240
    assert sum(x.role_intent == "FUTURE_DEV_RESERVE" for x in items) == 8
    assert sum(x.role_intent == "CERTIFICATION_RESERVE" for x in items) == 8
    assert {x.symbol for x in items} == {"BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"}
    assert items[0].zip_url == (
        "https://data.binance.vision/data/futures/um/daily/klines/"
        "BTCUSDT/5m/BTCUSDT-5m-2024-01-01.zip"
    )
    assert items[-1].zip_url.endswith("/XRPUSDT-5m-2024-06.zip")
    assert all(x.checksum_url == x.zip_url + ".CHECKSUM" for x in items)
    assert items[0].end_ns - items[0].start_ns == DAY_NS
    assert items[0].start_ns == 1704067200000000000
    assert items[59].end_ns == 1709251200000000000
    assert items[60].start_ns == 1709251200000000000
    for change in (
        dict(symbol="XBTUSDT"),
        dict(period="../2024-01-01"),
        dict(zip_url=obj().zip_url.replace("https://", "http://")),
        dict(zip_url=obj().zip_url + "?x=1"),
        dict(zip_url=obj().zip_url.replace("data.binance.vision", "evil.example")),
        dict(role_intent="CERTIFICATION_RESERVE"),
    ):
        with pytest.raises(ValueError):
            require_frozen_object(replace(obj(), **change))


def test_checksum_grammar_and_exact_identity():
    item = obj()
    archive = zipped(item)
    good = receipt(item, archive)
    assert good.zip_url == item.zip_url
    assert good.archive_sha256 and good.checksum_bytes_sha256
    from hashlib import sha256

    digest = sha256(archive).hexdigest()
    for blob in (
        digest.encode(), (digest + "  wrong.zip").encode(),
        (digest + "  ../" + item.zip_name).encode(),
        (digest + "  " + item.zip_name + "\nextra").encode(),
        (digest + "  " + item.zip_name + "\n" + digest).encode(),
        b"\xef\xbb\xbf" + digest.encode() + b"  " + item.zip_name.encode(),
        b" " * (MAX_CHECKSUM_BYTES + 1),
    ):
        with pytest.raises(ValueError):
            checksum_receipt(
                item, blob, retrieved_at_ns=item.end_ns + DAY_NS,
                retrieval_identity="synthetic://offline",
            )
    with pytest.raises(ValueError):
        receipt(item, archive, retrieved_at_ns=item.start_ns)
    with pytest.raises(ValueError):
        receipt(item, archive, retrieval_identity="")


def test_exact_http_response_bounded_and_no_redirects():
    item = obj()
    good = HttpResponse(
        item.checksum_url, 200, (("Content-Length", "3"),), b"abc"
    )
    assert checked_http_response(good, expected_url=item.checksum_url, limit=3) == b"abc"
    for response in (
        replace(good, redirected=True),
        replace(good, url=item.checksum_url + "?fallback"),
        replace(good, status=302),
        replace(good, body=b"abcd"),
        replace(good, headers=(("Content-Length", "100"),)),
        replace(good, headers=(("Content-Encoding", "gzip"),)),
        replace(good, headers=(("X", "a"), ("x", "b"))),
    ):
        with pytest.raises(ValueError):
            checked_http_response(response, expected_url=item.checksum_url, limit=3)
    with pytest.raises(ValueError):
        checked_http_response(
            HttpResponse(item.zip_url, 200, (), b"x" * (MAX_ZIP_BYTES + 1)),
            expected_url=item.zip_url, limit=MAX_ZIP_BYTES,
        )


def test_288_rows_and_nonzero_ignored_numeric_field_are_accepted():
    item = obj()
    archive = zipped(item)
    bars = parse_verified_daily_zip(
        item, archive, receipt(item, archive), finalized_as_of_ns=item.end_ns
    )
    assert len(bars) == 288
    assert bars[0].open_ms * 1_000_000 == item.start_ns
    assert (bars[-1].close_ms + 1) * 1_000_000 == item.end_ns
    assert bars[0].high == "11.000"
    assert bars[-1].trade_count == 2


def test_exact_official_header_preserves_all_288_validated_bars():
    item = obj()
    data = rows(item)
    without_header = zipped(item, data)
    with_header = zipped(item, [OFFICIAL_HEADER, *data])
    original = parse_verified_daily_zip(
        item, without_header, receipt(item, without_header), finalized_as_of_ns=item.end_ns
    )
    parsed = parse_verified_daily_zip(
        item, with_header, receipt(item, with_header), finalized_as_of_ns=item.end_ns
    )
    assert len(original) == len(parsed) == 288
    assert parsed == original
    assert parsed[0].open_ms * 1_000_000 == item.start_ns
    assert (parsed[-1].close_ms + 1) * 1_000_000 == item.end_ns


@pytest.mark.parametrize(
    "change",
    [
        lambda a: [OFFICIAL_HEADER, OFFICIAL_HEADER, *a],
        lambda a: [OFFICIAL_HEADER, a[0], OFFICIAL_HEADER, *a[2:]],
        lambda a: [OFFICIAL_HEADER.upper(), *a],
        lambda a: [OFFICIAL_HEADER.replace("open_time,open", "open,open_time"), *a],
        lambda a: [" " + OFFICIAL_HEADER, *a],
        lambda a: [OFFICIAL_HEADER + ",extra", *a],
        lambda a: ['"' + OFFICIAL_HEADER + '"', *a],
        lambda a: ["\\ufeff" + OFFICIAL_HEADER, *a],
        lambda a: [OFFICIAL_HEADER, *a[:-1]],
        lambda a: [OFFICIAL_HEADER, *a, a[-1]],
        lambda a: [OFFICIAL_HEADER, a[1], *a[1:]],
        lambda a: [OFFICIAL_HEADER, *a[:50], *a[51:]],
        lambda a: [OFFICIAL_HEADER, *a[:50], a[51], a[50], *a[52:]],
        lambda a: [OFFICIAL_HEADER, a[0].replace(",2,0.5", ",NaN,0.5"), *a[1:]],
    ],
)
def test_exact_header_does_not_bypass_schema_count_or_chronology(change):
    item = obj()
    archive = zipped(item, change(rows(item)))
    with pytest.raises((ValueError, zipfile.BadZipFile)):
        parse_verified_daily_zip(
            item, archive, receipt(item, archive), finalized_as_of_ns=item.end_ns
        )


def plus_one_close_ms(a: list[str]) -> list[str]:
    fields = a[0].split(",")
    fields[6] = str(int(fields[6]) + 1)
    return [",".join(fields), *a[1:]]


@pytest.mark.parametrize(
    "change",
    [
        lambda a: [OFFICIAL_HEADER, OFFICIAL_HEADER, *a[2:]],
        lambda a: ["\ufeff" + a[0], *a[1:]],
        lambda a: [a[0], OFFICIAL_HEADER, *a[2:]],
        lambda a: a[:-1],
        lambda a: [*a, a[-1]],
        lambda a: [a[0], a[0], *a[2:]],
        lambda a: [a[1], a[0], *a[2:]],
        lambda a: [a[0].replace(",2,0.5", ",NaN,0.5"), *a[1:]],
        lambda a: [a[0].replace(",2,0.5", ",2.5,0.5"), *a[1:]],
        lambda a: [a[0].replace(",12.5", ",Inf"), *a[1:]],
        lambda a: [a[0].replace("10.000,11.000", "12.000,11.000"), *a[1:]],
        plus_one_close_ms,
        lambda a: [a[0].replace(",1.5,", ",-1,"), *a[1:]],
        lambda a: [a[0] + ",extra", *a[1:]],
        lambda a: ["", *a[1:]],
        lambda a: [a[0].replace(",", '","'), *a[1:]],
    ],
)
def test_reject_bad_csv_rows_without_skipping_headers(change):
    item = obj()
    original_rows = rows(item)
    mutated_rows = change(original_rows)
    assert mutated_rows != original_rows
    archive = zipped(item, mutated_rows)
    with pytest.raises((ValueError, zipfile.BadZipFile)):
        parse_verified_daily_zip(
            item, archive, receipt(item, archive), finalized_as_of_ns=item.end_ns
        )


def test_zip_sha_before_any_zip_parser(monkeypatch):
    item = obj()
    archive = zipped(item)
    proof = receipt(item, archive)
    monkeypatch.setattr(
        zipfile, "ZipFile",
        lambda *args, **kwargs: pytest.fail("ZIP parsed before SHA verification"),
    )
    with pytest.raises(ValueError, match="SHA256"):
        parse_verified_daily_zip(
            item, archive + b"x", proof, finalized_as_of_ns=item.end_ns
        )


def test_header_zip_sha_mismatch_stops_before_zip_open(monkeypatch):
    item = obj()
    archive = zipped(item, [OFFICIAL_HEADER, *rows(item)])
    proof = receipt(item, archive)
    monkeypatch.setattr(
        zipfile, "ZipFile",
        lambda *args, **kwargs: pytest.fail("header ZIP parsed before SHA verification"),
    )
    with pytest.raises(ValueError, match="SHA256"):
        parse_verified_daily_zip(
            item, archive + b"x", proof, finalized_as_of_ns=item.end_ns
        )


@pytest.mark.parametrize(
    "make",
    [
        lambda item: zipped(item, extra=True),
        lambda item: zipped(item, name="../../escape.csv"),
        lambda item: zipped(item, name="wrong.csv"),
        lambda item: b"not a ZIP archive",
        lambda item: zipped(item) + b"x" * MAX_ZIP_BYTES,
    ],
)
def test_bad_zip_member_extras_traversal_and_byte_bomb(make):
    item = obj()
    archive = make(item)
    with pytest.raises(ValueError):
        parse_verified_daily_zip(
            item, archive, receipt(item, archive), finalized_as_of_ns=item.end_ns
        )


def test_reserved_zip_rejected_even_if_synthetic_bytes_supplied(monkeypatch):
    item = next(x for x in frozen_archive_objects() if x.role_intent != "CURRENT_DEV")
    archive = b"synthetic-not-provider-data"
    proof = receipt(item, archive)
    monkeypatch.setattr(
        zipfile, "ZipFile",
        lambda *args, **kwargs: pytest.fail("sealed reserve opener used"),
    )
    with pytest.raises(PermissionError):
        parse_verified_daily_zip(
            item, archive, proof, finalized_as_of_ns=item.end_ns
        )


def test_daily_finality_not_inferred_from_source_bar_timestamp():
    item = obj()
    archive = zipped(item)
    with pytest.raises(ValueError, match="finalized"):
        parse_verified_daily_zip(
            item, archive, receipt(item, archive), finalized_as_of_ns=item.start_ns
        )
