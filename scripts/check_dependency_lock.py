from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN_RE = re.compile(r"^[A-Za-z0-9_.-]+==[A-Za-z0-9_.!+-]+$")


def _read_lock(name: str) -> tuple[str, ...]:
    path = ROOT / name
    if not path.exists():
        raise SystemExit(f"{name} missing")
    lines = tuple(
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if not lines:
        raise SystemExit(f"{name} empty")
    bad = [line for line in lines if not PIN_RE.fullmatch(line)]
    if bad:
        raise SystemExit(f"{name} contains unpinned lines: " + ", ".join(bad))
    names = [line.split("==", 1)[0].lower().replace("_", "-") for line in lines]
    if len(names) != len(set(names)):
        raise SystemExit(f"{name} contains duplicate packages")
    return lines


def _normalized_name(requirement: str) -> str:
    return requirement.split("==", 1)[0].lower().replace("_", "-")


def main() -> int:
    runtime = _read_lock("requirements-runtime.lock")
    dev = _read_lock("requirements-dev.lock")
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = tuple(data["project"]["dependencies"])
    optional_dev = tuple(data["project"]["optional-dependencies"]["dev"])
    build = tuple(data["build-system"]["requires"])
    for requirement in (*project, *optional_dev, *build):
        if not PIN_RE.fullmatch(requirement):
            raise SystemExit(f"pyproject dependency is not exactly pinned: {requirement}")
    runtime_by_name = {_normalized_name(line): line for line in runtime}
    dev_by_name = {_normalized_name(line): line for line in dev}
    missing_runtime = [req for req in project if runtime_by_name.get(_normalized_name(req)) != req]
    missing_dev = [
        req
        for req in (*optional_dev, *build)
        if dev_by_name.get(_normalized_name(req)) != req
    ]
    if missing_runtime:
        raise SystemExit("runtime lock mismatch: " + ", ".join(missing_runtime))
    if missing_dev:
        raise SystemExit("dev lock mismatch: " + ", ".join(missing_dev))
    print(f"dependency locks: pinned ({len(runtime)} runtime, {len(dev)} dev)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
