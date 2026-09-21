from __future__ import annotations

import argparse
import re
import tomllib
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT_REQUIREMENT = "nautilus-trader==2.0.0rc5"
PILOT_WHEEL_SHA256 = "eab45fafd2312deda1236554c49a9798bfc76bc8465af864878e2f70189ebebe"
DECISION_MODEL_TYPESAFE_REQUIREMENT = "typesafe-sdk==0.7.0"
PIN_RE = re.compile(r"^[A-Za-z0-9_.-]+==[A-Za-z0-9_.!+-]+$")
LOCK_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)==(?P<version>[A-Za-z0-9_.!+-]+) "
    r"--hash=sha256:(?P<digest>[0-9a-f]{64})$"
)


def _normalized_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _pin(requirement: str) -> tuple[str, str]:
    name, version = requirement.split("==", 1)
    return _normalized_name(name), version


def _read_lock(name: str) -> dict[str, tuple[str, str]]:
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
    entries: dict[str, tuple[str, str]] = {}
    for line in lines:
        match = LOCK_RE.fullmatch(line)
        if match is None:
            raise SystemExit(f"{name} contains unhashed or unpinned line: {line}")
        normalized = _normalized_name(match.group("name"))
        if normalized in entries:
            raise SystemExit(f"{name} contains duplicate package: {normalized}")
        entries[normalized] = (match.group("version"), match.group("digest"))
    return entries


def _verify_direct_pins(
    runtime: dict[str, tuple[str, str]],
    dev: dict[str, tuple[str, str]],
    pilot: dict[str, tuple[str, str]],
    typesafe: dict[str, tuple[str, str]],
) -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = tuple(data["project"]["dependencies"])
    optional_dev = tuple(data["project"]["optional-dependencies"]["dev"])
    optional_pilot = tuple(data["project"]["optional-dependencies"]["nautilus-pilot"])
    optional_typesafe = tuple(data["project"]["optional-dependencies"]["decision-model-typesafe"])
    build = tuple(data["build-system"]["requires"])
    for requirement in (*project, *optional_dev, *optional_pilot, *optional_typesafe, *build):
        if not PIN_RE.fullmatch(requirement):
            raise SystemExit(f"pyproject dependency is not exactly pinned: {requirement}")
    missing_runtime = [
        requirement
        for requirement in project
        if runtime.get(_pin(requirement)[0], (None, None))[0] != _pin(requirement)[1]
    ]
    missing_dev = [
        requirement
        for requirement in (*project, *optional_dev, *build)
        if dev.get(_pin(requirement)[0], (None, None))[0] != _pin(requirement)[1]
    ]
    if missing_runtime:
        raise SystemExit("runtime lock mismatch: " + ", ".join(missing_runtime))
    if missing_dev:
        raise SystemExit("dev lock mismatch: " + ", ".join(missing_dev))
    if optional_pilot != (PILOT_REQUIREMENT,):
        raise SystemExit("nautilus-pilot optional dependency must contain only the exact rc5 pin")
    expected_pilot = {_pin(PILOT_REQUIREMENT)[0]: (_pin(PILOT_REQUIREMENT)[1], PILOT_WHEEL_SHA256)}
    if pilot != expected_pilot:
        raise SystemExit("pilot lock must contain only the exact authorized rc5 Linux wheel")
    if optional_typesafe != (DECISION_MODEL_TYPESAFE_REQUIREMENT,):
        raise SystemExit(
            "decision-model-typesafe optional dependency must contain only the exact "
            "typesafe-sdk 0.7.0 pin"
        )
    typesafe_name, typesafe_version = _pin(DECISION_MODEL_TYPESAFE_REQUIREMENT)
    if typesafe.get(typesafe_name, (None, None))[0] != typesafe_version:
        raise SystemExit(
            "TypeSafe decision-model lock does not contain the exact accepted "
            "typesafe-sdk pin"
        )
    shared = sorted(set(dev) & set(typesafe))
    mismatched_shared = [name for name in shared if dev[name] != typesafe[name]]
    if mismatched_shared:
        raise SystemExit(
            "TypeSafe decision-model lock conflicts with the accepted dev closure: "
            + ", ".join(mismatched_shared)
        )


def _verify_runtime_subset(
    runtime: dict[str, tuple[str, str]],
    dev: dict[str, tuple[str, str]],
) -> None:
    mismatches = [name for name, entry in runtime.items() if dev.get(name) != entry]
    if mismatches:
        raise SystemExit(
            "runtime lock is not an exact hashed subset of dev lock: " + ", ".join(mismatches)
        )


def _verify_installed(
    dev: dict[str, tuple[str, str]],
    extra: dict[str, tuple[str, str]] | None = None,
) -> None:
    installed: dict[str, str] = {}
    for distribution in distributions():
        name = distribution.metadata.get("Name")
        if name:
            installed[_normalized_name(name)] = distribution.version
    expected = dev if extra is None else {**dev, **extra}
    expected_names = set(expected) | {"trader-assist-v0"}
    actual_names = set(installed)
    missing = sorted(expected_names - actual_names)
    extra_names = sorted(actual_names - expected_names)
    wrong_versions = sorted(
        name
        for name, (version, _digest) in expected.items()
        if installed.get(name) is not None and installed[name] != version
    )
    failures: list[str] = []
    if missing:
        failures.append("missing installed distributions: " + ", ".join(missing))
    if extra_names:
        failures.append("unlocked installed distributions: " + ", ".join(extra_names))
    if wrong_versions:
        failures.append("installed version mismatch: " + ", ".join(wrong_versions))
    if failures:
        raise SystemExit("; ".join(failures))


def main() -> int:
    parser = argparse.ArgumentParser()
    installed_mode = parser.add_mutually_exclusive_group()
    installed_mode.add_argument("--verify-installed", action="store_true")
    installed_mode.add_argument("--verify-pilot-installed", action="store_true")
    installed_mode.add_argument("--verify-decision-model-typesafe-installed", action="store_true")
    args = parser.parse_args()
    runtime = _read_lock("requirements-runtime.lock")
    dev = _read_lock("requirements-dev.lock")
    pilot = _read_lock("requirements-nautilus-pilot.lock")
    typesafe = _read_lock("requirements-decision-model-typesafe.lock")
    _verify_direct_pins(runtime, dev, pilot, typesafe)
    _verify_runtime_subset(runtime, dev)
    if args.verify_installed:
        _verify_installed(dev)
    if args.verify_pilot_installed:
        _verify_installed(dev, pilot)
    if args.verify_decision_model_typesafe_installed:
        _verify_installed(dev, typesafe)
    print(
        "dependency locks: complete, hashed, and consistent "
        f"({len(runtime)} runtime, {len(dev)} CI/dev, {len(pilot)} pilot, "
        f"{len(typesafe)} TypeSafe decision-model adapter)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
