#!/usr/bin/env python3
"""Read-only exact Three Setup release, E4, Registry and host preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from scripts.check_dependency_lock import PILOT_WHEEL_SHA256


class PreflightError(ValueError):
    """One required candidate identity or prerequisite is unproven."""


def verify_host_prerequisites(wheel: Path) -> None:
    if platform.system() != "Linux":
        raise PreflightError("target OS must be Linux")
    if platform.machine().lower() not in {"x86_64", "amd64"}:
        raise PreflightError("target architecture must be x86_64")
    if sys.version_info[:2] != (3, 12):
        raise PreflightError("target Python must be 3.12")
    name = wheel.name
    match = re.fullmatch(
        r"nautilus_trader-2\.0\.0rc5-(?:[^-]+-)?cp312-cp312-([^.]+(?:\.[^.]+)*)\.whl",
        name,
    )
    if match is None:
        raise PreflightError("exact rc5 wheel tag is incompatible")
    libc, current = platform.libc_ver()
    if libc != "glibc" or not current:
        raise PreflightError("target glibc version is unavailable")
    try:
        host_version = tuple(int(part) for part in current.split(".")[:2])
    except ValueError as exc:
        raise PreflightError("target glibc version is invalid") from exc
    platform_tags = match.group(1).split(".")
    minimums = []
    for tag in platform_tags:
        modern = re.fullmatch(r"manylinux_(\d+)_(\d+)_x86_64", tag)
        if modern:
            minimums.append((int(modern.group(1)), int(modern.group(2))))
        elif tag == "manylinux2014_x86_64":
            minimums.append((2, 17))
    if not minimums:
        raise PreflightError("exact rc5 wheel tag is incompatible")
    if not any(host_version >= minimum for minimum in minimums):
        raise PreflightError("target glibc is incompatible with rc5 wheel")
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != PILOT_WHEEL_SHA256:
        raise PreflightError("exact rc5 wheel lock hash mismatch")


def verify_candidate(
    *,
    root: Path,
    release_manifest: Path,
    config_path: Path,
    expected_sha: str,
    expected_tree: str,
    expected_manifest_digest: str,
    pip_check_with: Path,
) -> None:
    from scripts import check_dependency_lock as locks
    from scripts.verify_exact_release import verify_staged_release
    from trader_assist_v0.multi_asset_shadow.production import (
        THREE_SETUP_E4_CONFIG_SCHEMA,
        load_three_setup_config,
        validate_three_setup_e4_identity,
    )
    from trader_assist_v0.nautilus_e4.contracts import RunManifest

    manifest = json.loads(release_manifest.read_text(encoding="utf-8"))
    verify_staged_release(
        root,
        manifest,
        expected_release_sha=expected_sha,
        expected_release_tree=expected_tree,
        expected_manifest_digest=expected_manifest_digest,
    )
    raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    if raw_config.get("schema") != THREE_SETUP_E4_CONFIG_SCHEMA:
        raise PreflightError("deploy config must be active E4 v2")
    config = load_three_setup_config(config_path)
    if config.release_sha != expected_sha:
        raise PreflightError("config release SHA differs from exact release")
    validate_three_setup_e4_identity(config)
    assert config.e4_manifest_path is not None
    e4 = RunManifest.model_validate_json(config.e4_manifest_path.read_bytes())
    if e4.git_sha != expected_sha or e4.git_tree != expected_tree:
        raise PreflightError("E4 run release SHA/TREE differs")
    if e4.nautilus_version != "2.0.0rc5" or any(
        (e4.private_api, e4.exchange_write, e4.real_exec_client_registered)
    ):
        raise PreflightError("E4 rc5 or zero-write identity differs")
    try:
        installed = version("nautilus-trader")
    except PackageNotFoundError as exc:
        raise PreflightError("installed Nautilus rc5 is missing") from exc
    if installed != "2.0.0rc5":
        raise PreflightError("installed Nautilus is not exact rc5")
    runtime = locks._read_lock("requirements-runtime.lock")
    pilot = locks._read_lock("requirements-nautilus-pilot.lock")
    if pilot != {"nautilus-trader": ("2.0.0rc5", PILOT_WHEEL_SHA256)}:
        raise PreflightError("pilot lock pin or wheel hash differs")
    locks._verify_installed(runtime, pilot, project_distribution_expected=False)
    locks._verify_target_import(root / "src")
    locks._pip_check(pip_check_with)


def main(argv: tuple[str, ...] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--release-manifest", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--expected-sha")
    parser.add_argument("--expected-tree")
    parser.add_argument("--expected-manifest-digest")
    parser.add_argument("--pip-check-with", type=Path)
    parser.add_argument("--host-wheel", type=Path)
    parser.add_argument("--host-only", action="store_true")
    args = parser.parse_args(argv)
    if args.host_only:
        if args.host_wheel is None:
            parser.error("--host-wheel is required for --host-only")
        verify_host_prerequisites(args.host_wheel)
    else:
        if None in (
            args.root,
            args.release_manifest,
            args.config,
            args.expected_sha,
            args.expected_tree,
            args.expected_manifest_digest,
            args.pip_check_with,
        ):
            parser.error(
                "candidate preflight requires root, release manifest, config, SHA and TREE"
            )
        verify_candidate(
            root=args.root,
            release_manifest=args.release_manifest,
            config_path=args.config,
            expected_sha=args.expected_sha,
            expected_tree=args.expected_tree,
            expected_manifest_digest=args.expected_manifest_digest,
            pip_check_with=args.pip_check_with,
        )
    print("THREE_SETUP_PREFLIGHT=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f"THREE_SETUP_PREFLIGHT=FAIL:{type(exc).__name__}")
        raise SystemExit(2) from None
