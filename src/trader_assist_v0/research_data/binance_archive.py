"""Frozen Binance USD-M 2024 archive identities and pure bounded ZIP/CSV verification.

No networking or DEV authority lives here. All bytes are caller supplied.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import re
import stat
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal

from trader_assist_v0.research_data.contracts import BarPayload

DAY_NS = 86_400_000_000_000
BAR_NS = 300_000_000_000
MAX_CHECKSUM_BYTES = 4096
MAX_ZIP_BYTES = 1_000_000
MAX_CSV_BYTES = 1_000_000
MAX_LINE_BYTES = 2048
MAX_NUMERIC_CHARS = 80
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")
HOST = "https://data.binance.vision"
Role = Literal["CURRENT_DEV", "FUTURE_DEV_RESERVE", "CERTIFICATION_RESERVE"]
_OFFICIAL_KLINE_HEADER = (
    "open_time,open,high,low,close,volume,close_time,quote_volume,"
    "count,taker_buy_volume,taker_buy_quote_volume,ignore"
)
_SHA_LINE = re.compile(r"([0-9a-fA-F]{64}) [ *]([A-Za-z0-9_.-]+)")
_NUMBER = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
_INTEGER = re.compile(r"(?:0|[1-9][0-9]*)")


@dataclass(frozen=True, slots=True)
class ArchiveObject:
    symbol: str
    period: str
    role_intent: Role
    start_ns: int
    end_ns: int
    zip_url: str
    zip_name: str
    csv_name: str

    @property
    def checksum_url(self) -> str:
        return self.zip_url + ".CHECKSUM"


@dataclass(frozen=True, slots=True)
class ChecksumReceipt:
    zip_url: str
    checksum_url: str
    zip_name: str
    archive_sha256: str
    checksum_bytes_sha256: str
    retrieved_at_ns: int
    retrieval_identity: str


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Injected deterministic transport result; not a networking interface."""

    url: str
    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes
    redirected: bool = False


@dataclass(frozen=True, slots=True)
class BinanceKline:
    open_ms: int
    close_ms: int
    open: str
    high: str
    low: str
    close: str
    volume: str
    trade_count: int


def _utc_ns(value: datetime) -> int:
    return int(value.timestamp()) * 1_000_000_000


def frozen_archive_objects() -> tuple[ArchiveObject, ...]:
    """Immutable, pre-outcome 240 daily DEV plus 8+8 monthly reserve identities."""
    result: list[ArchiveObject] = []
    for symbol in SYMBOLS:
        day = datetime(2024, 1, 1, tzinfo=UTC)
        stop = datetime(2024, 3, 1, tzinfo=UTC)
        while day < stop:
            period = day.strftime("%Y-%m-%d")
            name = f"{symbol}-5m-{period}"
            result.append(
                ArchiveObject(
                    symbol, period, "CURRENT_DEV", _utc_ns(day),
                    _utc_ns(day + timedelta(days=1)),
                    f"{HOST}/data/futures/um/daily/klines/{symbol}/5m/{name}.zip",
                    name + ".zip", name + ".csv",
                )
            )
            day += timedelta(days=1)
        for month in (3, 4, 5, 6):
            first = datetime(2024, month, 1, tzinfo=UTC)
            next_month = datetime(2024, month + 1, 1, tzinfo=UTC)
            period = first.strftime("%Y-%m")
            name = f"{symbol}-5m-{period}"
            role: Role = (
                "FUTURE_DEV_RESERVE" if month < 5 else "CERTIFICATION_RESERVE"
            )
            result.append(
                ArchiveObject(
                    symbol, period, role, _utc_ns(first), _utc_ns(next_month),
                    f"{HOST}/data/futures/um/monthly/klines/{symbol}/5m/{name}.zip",
                    name + ".zip", name + ".csv",
                )
            )
    return tuple(result)


def require_frozen_object(obj: ArchiveObject) -> ArchiveObject:
    if type(obj) is not ArchiveObject or obj not in frozen_archive_objects():
        raise ValueError("not an exact frozen Binance USD-M archive identity")
    return obj


def checked_http_response(
    response: HttpResponse, *, expected_url: str, limit: int
) -> bytes:
    """Verify an injected single-request result. No alternate hosts or redirects."""
    if type(response) is not HttpResponse or response.url != expected_url:
        raise ValueError("HTTP response identity/URL mismatch")
    if response.redirected or response.status != 200:
        raise ValueError("redirect/non-200 archive transport prohibited")
    if type(response.body) is not bytes or len(response.body) > limit:
        raise ValueError("bounded HTTP response exceeded")
    headers: dict[str, str] = {}
    for key, value in response.headers:
        name = key.strip().lower()
        if name in headers:
            raise ValueError("duplicate HTTP response header")
        headers[name] = value.strip()
    if headers.get("content-encoding", "identity").lower() != "identity":
        raise ValueError("HTTP content encoding must be identity")
    if "transfer-encoding" in headers and headers["transfer-encoding"].lower() != "identity":
        raise ValueError("unsupported HTTP transfer encoding")
    if "content-length" in headers:
        size = headers["content-length"]
        if not size.isascii() or not size.isdecimal() or int(size) != len(response.body):
            raise ValueError("HTTP content-length mismatch")
    return response.body


def checksum_receipt(
    obj: ArchiveObject,
    raw: bytes,
    *,
    retrieved_at_ns: int,
    retrieval_identity: str,
) -> ChecksumReceipt:
    require_frozen_object(obj)
    if type(raw) is not bytes or not raw or len(raw) > MAX_CHECKSUM_BYTES:
        raise ValueError("invalid checksum byte bound")
    if type(retrieved_at_ns) is not int or retrieved_at_ns < obj.end_ns:
        raise ValueError("archive cannot be received before daily/monthly cut ends")
    if type(retrieval_identity) is not str or not retrieval_identity.strip():
        raise ValueError("explicit retrieval identity required")
    try:
        line = raw.decode("ascii").removesuffix("\n").removesuffix("\r")
    except UnicodeError as exc:
        raise ValueError("checksum must be ASCII") from exc
    match = _SHA_LINE.fullmatch(line)
    if match is None or match.group(2) != obj.zip_name:
        raise ValueError("single exact .CHECKSUM basename and SHA-256 required")
    return ChecksumReceipt(
        zip_url=obj.zip_url,
        checksum_url=obj.checksum_url,
        zip_name=obj.zip_name,
        archive_sha256=match.group(1).lower(),
        checksum_bytes_sha256=hashlib.sha256(raw).hexdigest(),
        retrieved_at_ns=retrieved_at_ns,
        retrieval_identity=retrieval_identity,
    )


def require_receipt(obj: ArchiveObject, receipt: ChecksumReceipt) -> ChecksumReceipt:
    require_frozen_object(obj)
    if (
        type(receipt) is not ChecksumReceipt
        or receipt.zip_url != obj.zip_url
        or receipt.checksum_url != obj.checksum_url
        or receipt.zip_name != obj.zip_name
        or re.fullmatch("[0-9a-f]{64}", receipt.archive_sha256) is None
        or re.fullmatch("[0-9a-f]{64}", receipt.checksum_bytes_sha256) is None
        or receipt.retrieved_at_ns < obj.end_ns
        or not receipt.retrieval_identity.strip()
    ):
        raise ValueError("archive checksum receipt identity mismatch")
    return receipt


def _decimal(value: str, *, positive: bool = False, integer: bool = False) -> str:
    if not value or len(value) > MAX_NUMERIC_CHARS:
        raise ValueError("numeric field length outside approved bound")
    if not (_INTEGER if integer else _NUMBER).fullmatch(value):
        raise ValueError("non-canonical/nonnumeric CSV value")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid decimal") from exc
    if not number.is_finite() or (number <= 0 if positive else number < 0):
        raise ValueError("negative/nonfinite/nonpositive numeric value")
    return value


def parse_verified_daily_zip(
    obj: ArchiveObject,
    archive: bytes,
    receipt: ChecksumReceipt,
    *,
    finalized_as_of_ns: int,
) -> tuple[BinanceKline, ...]:
    """SHA-256-first verification; exactly 288 UTC 5m bars, optional official header."""
    require_frozen_object(obj)
    require_receipt(obj, receipt)
    if obj.role_intent != "CURRENT_DEV":
        raise PermissionError("reserve ZIP must never be opened")
    if type(finalized_as_of_ns) is not int or finalized_as_of_ns < obj.end_ns:
        raise ValueError("historical daily archive is not finalized")
    if type(archive) is not bytes or not archive or len(archive) > MAX_ZIP_BYTES:
        raise ValueError("bounded ZIP size exceeded")
    if not hmac.compare_digest(hashlib.sha256(archive).hexdigest(), receipt.archive_sha256):
        raise ValueError("ZIP SHA256 mismatch before ZIP parsing")
    try:
        with zipfile.ZipFile(io.BytesIO(archive), "r") as zf:
            members = zf.infolist()
            if len(members) != 1:
                raise ValueError("exactly one daily CSV ZIP member required")
            member = members[0]
            mode = member.external_attr >> 16
            if (
                member.filename != obj.csv_name
                or member.is_dir()
                or (mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG))
                or member.flag_bits & 1
                or member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                or member.file_size <= 0
                or member.file_size > MAX_CSV_BYTES
                or member.compress_size <= 0
                or member.file_size > 200 * member.compress_size
            ):
                raise ValueError("unsafe/oversized ZIP member")
            with zf.open(member, "r") as handle:
                raw = handle.read(MAX_CSV_BYTES + 1)
                if len(raw) > MAX_CSV_BYTES or handle.read(1):
                    raise ValueError("uncompressed daily CSV exceeds bound")
    except (zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        raise ValueError("invalid ZIP/CRC archive") from exc
    if b"\x00" in raw or b"\xef\xbb\xbf" in raw or b'"' in raw:
        raise ValueError("header/BOM/quoted CSV not accepted")
    try:
        content = raw.decode("ascii")
    except UnicodeError as exc:
        raise ValueError("CSV must be ASCII") from exc
    lines = content.splitlines()
    if lines and lines[0] == _OFFICIAL_KLINE_HEADER:
        lines = lines[1:]
    if len(lines) != 288 or any(
        not line or len(line.encode("ascii")) > MAX_LINE_BYTES for line in lines
    ):
        raise ValueError("288 bounded contiguous 5m data rows required")
    result: list[BinanceKline] = []
    for index, line in enumerate(lines):
        row = next(csv.reader([line], strict=True))
        if len(row) != 12:
            raise ValueError("official USD-M positional schema requires 12 columns")
        open_text, op, hi, lo, cl, vol, close_text, quote, count, buy, buy_quote, ignore = row
        if (
            _INTEGER.fullmatch(open_text) is None
            or _INTEGER.fullmatch(close_text) is None
            or len(open_text) != 13
            or len(close_text) != 13
        ):
            raise ValueError("raw 2024 UTC epoch-milliseconds required")
        open_ms, close_ms = int(open_text), int(close_text)
        if (
            open_ms * 1_000_000 != obj.start_ns + index * BAR_NS
            or close_ms != open_ms + 300_000 - 1
        ):
            raise ValueError("missing/duplicate/out-of-order/non-finalized 5m bar")
        for value in (op, hi, lo, cl):
            _decimal(value, positive=True)
        for value in (vol, quote, buy, buy_quote, ignore):
            _decimal(value)
        _decimal(count, integer=True)
        BarPayload(
            interval_minutes=5, start_ns=open_ms * 1_000_000,
            end_ns=(close_ms + 1) * 1_000_000, timestamp_meaning="OPEN",
            aggregation_origin="BINANCE_UM_OFFLINE_FINALIZED",
            finalized=True, open=op, high=hi, low=lo, close=cl, volume=vol,
        )
        if Decimal(buy) > Decimal(vol) or Decimal(buy_quote) > Decimal(quote):
            raise ValueError("taker buy volume outside total volume")
        result.append(BinanceKline(open_ms, close_ms, op, hi, lo, cl, vol, int(count)))
    if result[-1].close_ms * 1_000_000 + 1_000_000 != obj.end_ns:
        raise ValueError("daily interval is not complete")
    return tuple(result)
