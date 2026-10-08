from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
import tomllib
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT_REQUIREMENT = "nautilus-trader==2.0.0rc5"
PILOT_WHEEL_SHA256 = "eab45fafd2312deda1236554c49a9798bfc76bc8465af864878e2f70189ebebe"
OPERATOR_REQUIREMENTS = (
    "fastapi==0.141.1",
    "starlette==1.7.0",
    "jinja2==3.1.6",
    "uvicorn==0.54.0",
)
OPERATOR_CLOSURE = frozenset(
    {
        "annotated-doc", "annotated-types", "anyio", "click", "fastapi", "h11",
        "idna", "jinja2", "markupsafe", "pydantic", "pydantic-core", "starlette",
        "typing-extensions", "typing-inspection", "uvicorn", "websockets",
    }
)
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
    operator: dict[str, tuple[str, str]],
) -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = tuple(data["project"]["dependencies"])
    optional_dev = tuple(data["project"]["optional-dependencies"]["dev"])
    optional_pilot = tuple(data["project"]["optional-dependencies"]["nautilus-pilot"])
    optional_typesafe = tuple(data["project"]["optional-dependencies"]["decision-model-typesafe"])
    optional_operator = tuple(data["project"]["optional-dependencies"]["operator"])
    build = tuple(data["build-system"]["requires"])
    for requirement in (
        *project,
        *optional_dev,
        *optional_pilot,
        *optional_typesafe,
        *optional_operator,
        *build,
    ):
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
    if optional_operator != OPERATOR_REQUIREMENTS:
        raise SystemExit("operator optional dependencies differ from frozen pins")
    if set(operator) != OPERATOR_CLOSURE:
        raise SystemExit("operator lock differs from frozen complete closure")
    for requirement in (*project, *optional_operator):
        name, version = _pin(requirement)
        if operator.get(name, (None, None))[0] != version:
            raise SystemExit("operator direct dependency mismatch: " + requirement)
        if dev.get(name) != operator.get(name):
            raise SystemExit("operator/dev exact wheel hash mismatch: " + requirement)
    if not set(runtime).issubset(operator):
        raise SystemExit("operator lock omits core runtime dependency")
    if any(dev.get(name) != entry for name, entry in operator.items()):
        raise SystemExit("operator lock is not an exact hashed subset of dev lock")
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
            "TypeSafe decision-model lock does not contain the exact accepted typesafe-sdk pin"
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
    *,
    project_distribution_expected: bool = True,
) -> None:
    installed: dict[str, str] = {}
    for distribution in distributions():
        name = distribution.metadata.get("Name")
        if name:
            normalized = _normalized_name(name)
            if normalized in installed:
                raise SystemExit(f"duplicate installed distribution: {normalized}")
            installed[normalized] = distribution.version
    expected = dev if extra is None else {**dev, **extra}
    expected_names = set(expected) | (
        {"trader-assist-v0"} if project_distribution_expected else set()
    )
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


def _verify_target_import(staged_source: Path) -> None:
    expected = staged_source.resolve(strict=True)
    spec = importlib.util.find_spec("trader_assist_v0")
    if spec is None or spec.origin is None:
        raise SystemExit("target project import is unavailable")
    actual = Path(spec.origin).resolve(strict=True)
    if not actual.is_relative_to(expected):
        raise SystemExit("target project import resolves outside exact staged source")


def _pip_check(host_python: Path) -> None:
    """Use the explicitly selected pip provider to check this target Python."""
    command = (str(host_python), "-m", "pip", "--python", sys.executable, "check")
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as exc:
        raise SystemExit(f"target pip check provider unavailable: {host_python}: {exc}") from exc
    if result.returncode:
        details = (result.stderr.strip() + "\n" + result.stdout.strip()).strip()
        raise SystemExit(
            f"target pip check failed (provider={host_python}, target={sys.executable}, "
            f"exit={result.returncode}): {details}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    installed_mode = parser.add_mutually_exclusive_group()
    installed_mode.add_argument("--verify-installed", action="store_true")
    installed_mode.add_argument("--verify-pilot-installed", action="store_true")
    installed_mode.add_argument("--verify-decision-model-typesafe-installed", action="store_true")
    installed_mode.add_argument("--verify-target-runtime-installed", action="store_true")
    installed_mode.add_argument("--verify-operator-installed", action="store_true")
    parser.add_argument("--staged-source", type=Path)
    parser.add_argument("--pip-check-with", type=Path)
    args = parser.parse_args()
    runtime = _read_lock("requirements-runtime.lock")
    pilot = _read_lock("requirements-nautilus-pilot.lock")
    expected_pilot = {_pin(PILOT_REQUIREMENT)[0]: (_pin(PILOT_REQUIREMENT)[1], PILOT_WHEEL_SHA256)}
    if pilot != expected_pilot:
        raise SystemExit("pilot lock must contain only the exact authorized rc5 Linux wheel")
    if args.verify_target_runtime_installed:
        if args.staged_source is None or args.pip_check_with is None:
            parser.error("target mode requires --staged-source and --pip-check-with")
        _verify_installed(runtime, pilot, project_distribution_expected=False)
        _verify_target_import(args.staged_source)
        _pip_check(args.pip_check_with)
        print("target dependency closure: exact runtime + rc5 pilot; pip check PASS")
        return 0
    operator = _read_lock("requirements-operator.lock")
    dev = _read_lock("requirements-dev.lock")
    typesafe = _read_lock("requirements-decision-model-typesafe.lock")
    _verify_direct_pins(runtime, dev, pilot, typesafe, operator)
    _verify_runtime_subset(runtime, dev)
    if args.verify_installed:
        _verify_installed(dev)
    if args.verify_operator_installed:
        _verify_installed(operator, project_distribution_expected=False)
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
