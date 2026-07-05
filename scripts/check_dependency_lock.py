from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN_RE = re.compile(r"^[A-Za-z0-9_.-]+==[A-Za-z0-9_.!+-]+$")


def main() -> int:
    lock = ROOT / "requirements-dev.lock"
    if not lock.exists():
        raise SystemExit("requirements-dev.lock missing")
    lines = [line.strip() for line in lock.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise SystemExit("requirements-dev.lock empty")
    bad = [line for line in lines if not PIN_RE.match(line)]
    if bad:
        raise SystemExit("unpinned dependency lines: " + ", ".join(bad))
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    missing = [
        line for line in lines if line not in pyproject and not line.startswith("pip-audit==")
    ]
    if missing:
        raise SystemExit("lock contains packages not pinned in pyproject: " + ", ".join(missing))
    print("dependency lock: pinned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
