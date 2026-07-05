from __future__ import annotations

from datetime import UTC, datetime

import pytest


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 7, 6, 0, 0, tzinfo=UTC)


@pytest.fixture
def h() -> str:
    return "a" * 64
