#!/usr/bin/env python3
"""Build or verify the deterministic Three Setup exact-release identity manifest."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Final

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow.production import THREE_SETUP_CONFIG_SCHEMA

RELEASE_MANIFEST_SCHEMA: Final = "trader-assist-v0/three-setup-exact-release/v1"
REQUIRED_FILES: Final = (
    "pyproject.toml",
    "requirements-runtime.lock",
    "requirements-dev.lock",
    "scripts/run_three_setup_shadow_runtime.py",
    "scripts/p4a/run_three_setup_shadow_runtime.sh",
    "deploy/p4a/config/three-setup-shadow.json.example",
    "deploy/p4a/systemd/trader-assist-v0-three-setup.env.example",
    "deploy/p4a/systemd/trader-assist-v0-three-setup.service",
)
SOURCE_SUFFIXES: Final = frozenset({".py", ".sh"})


class ExactReleaseError(ValueError):
    """The candidate cannot be bound to one exact release identity."""


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(root), *arguments),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ExactReleaseError("exact release Git identity is unavailable")
    return result.stdout.strip()


def exact_clean_head(root: Path, *, expected_head: str) -> str:
    """Prove the exact clean candidate; no nearby or dirty tree is accepted."""
    head = _git(root, "rev-parse", "HEAD")
    if head != expected_head or len(head) != 40:
        raise ExactReleaseError("exact release HEAD does not match expected candidate")
    if _git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ExactReleaseError("exact release tree must be clean")
    return head


def release_paths(root: Path) -> tuple[Path, ...]:
    """Select source and fixed release surfaces without a second package format."""
    selected = {root / name for name in REQUIRED_FILES}
    for base_name in ("src",):
        base = root / base_name
        if base.exists():
            selected.update(
                path
                for path in base.rglob("*")
                if path.is_file()
                and path.suffix in SOURCE_SUFFIXES
                and "__pycache__" not in path.parts
            )
    missing = [path.relative_to(root).as_posix() for path in selected if not path.is_file()]
    if missing:
        raise ExactReleaseError("release surface is incomplete: " + ", ".join(sorted(missing)))
    return tuple(sorted(selected, key=lambda path: path.relative_to(root).as_posix()))


def build_release_manifest(root: Path, *, release_sha: str) -> dict[str, object]:
    """Bind source/locks/deployment/config semantics to one canonical digest."""
    if len(release_sha) != 40 or any(ch not in "0123456789abcdef" for ch in release_sha):
        raise ExactReleaseError("release SHA must be exact lowercase Git identity")
    config_path = root / "deploy/p4a/config/three-setup-shadow.json.example"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExactReleaseError("Three Setup release config example is invalid") from exc
    if config.get("schema") != THREE_SETUP_CONFIG_SCHEMA:
        raise ExactReleaseError("release config schema contradicts production authority")
    files = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_hex(path.read_bytes()),
            "size": path.stat().st_size,
        }
        for path in release_paths(root)
    ]
    payload: dict[str, object] = {
        "schema": RELEASE_MANIFEST_SCHEMA,
        "release_sha": release_sha,
        "config_schema": THREE_SETUP_CONFIG_SCHEMA,
        "runtime_lock_sha256": sha256_hex((root / "requirements-runtime.lock").read_bytes()),
        "dev_lock_sha256": sha256_hex((root / "requirements-dev.lock").read_bytes()),
        "source_file_count": len(files),
        "files": files,
    }
    payload["manifest_sha256"] = sha256_hex(canonical_json_bytes(payload))
    return payload


def verify_manifest(root: Path, manifest: object, *, release_sha: str) -> None:
    expected = build_release_manifest(root, release_sha=release_sha)
    if manifest != expected:
        raise ExactReleaseError("release manifest does not match the exact staged artifact")


def verify_staged_release(
    staged_root: Path,
    manifest: dict[str, object],
    *,
    expected_release_sha: str,
) -> None:
    """Verify a staged exact-release artifact against its retained manifest.

    This MUST NOT require .git in the staged root.  Identity comes exclusively
    from the retained canonical manifest and the explicit expected release SHA.
    """
    if len(expected_release_sha) != 40 or any(
        ch not in "0123456789abcdef" for ch in expected_release_sha
    ):
        raise ExactReleaseError("expected release SHA must be exact lowercase Git identity")

    if not isinstance(manifest, dict):
        raise ExactReleaseError("retained manifest is not a valid object")

    # Manifest schema
    if manifest.get("schema") != RELEASE_MANIFEST_SCHEMA:
        raise ExactReleaseError("retained manifest schema is invalid or missing")

    # Embedded release SHA must match explicit expected SHA
    if manifest.get("release_sha") != expected_release_sha:
        raise ExactReleaseError(
            "retained manifest embedded release SHA does not match expected release SHA"
        )

    # Config schema
    if manifest.get("config_schema") != THREE_SETUP_CONFIG_SCHEMA:
        raise ExactReleaseError(
            "retained manifest config schema contradicts production authority"
        )

    # Manifest digest integrity — proves the manifest has not been tampered with
    stored_digest = manifest.get("manifest_sha256")
    if not isinstance(stored_digest, str):
        raise ExactReleaseError("retained manifest digest is missing or invalid")
    payload = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    recomputed = sha256_hex(canonical_json_bytes(payload))
    if recomputed != stored_digest:
        raise ExactReleaseError(
            "retained manifest digest does not match canonical recomputation"
        )

    # File entries — verify each selected file exists with correct hash and size
    files = manifest.get("files")
    if not isinstance(files, list):
        raise ExactReleaseError("retained manifest file list is missing or invalid")

    manifest_paths: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise ExactReleaseError("retained manifest file entry is invalid")
        rel = entry.get("path")
        if not isinstance(rel, str):
            raise ExactReleaseError("retained manifest file entry path is invalid")
        manifest_paths.add(rel)

        staged_file = staged_root / rel
        if not staged_file.is_file():
            raise ExactReleaseError(
                f"staged artifact is missing selected content: {rel}"
            )
        actual_hash = sha256_hex(staged_file.read_bytes())
        if actual_hash != entry.get("sha256"):
            raise ExactReleaseError(f"staged artifact content is mutated: {rel}")
        actual_size = staged_file.stat().st_size
        if actual_size != entry.get("size"):
            raise ExactReleaseError(f"staged artifact size mismatch: {rel}")

    # Exact selected path set — staged surface must match manifest exactly
    staged_paths = {
        p.relative_to(staged_root).as_posix() for p in release_paths(staged_root)
    }
    if staged_paths != manifest_paths:
        raise ExactReleaseError(
            "staged artifact selected path set does not match retained manifest"
        )

    # source_file_count consistency
    if manifest.get("source_file_count") != len(files):
        raise ExactReleaseError("retained manifest source_file_count is inconsistent")


def main(argv: tuple[str, ...] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--expected-head")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--verify-staged", type=Path, dest="verify_staged")
    parser.add_argument("--expected-release-sha", dest="expected_release_sha")
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()

    if arguments.verify_staged is not None:
        # Staged artifact verification — no .git required
        if arguments.expected_release_sha is None:
            parser.error("--expected-release-sha is required with --verify-staged")
        try:
            retained = json.loads(
                arguments.verify_staged.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise ExactReleaseError("retained release manifest is unavailable") from exc
        verify_staged_release(
            root, retained, expected_release_sha=arguments.expected_release_sha
        )
        print(f"EXACT_RELEASE_SHA={arguments.expected_release_sha}")
        print("EXACT_RELEASE_STAGED_VERIFY=PASS")
        return 0

    # Manifest creation / Git-based verification — .git required
    if arguments.expected_head is None:
        parser.error("--expected-head is required for manifest creation")
    head = exact_clean_head(root, expected_head=arguments.expected_head)
    manifest = build_release_manifest(root, release_sha=head)
    if arguments.verify is not None:
        try:
            retained = json.loads(arguments.verify.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ExactReleaseError("retained release manifest is unavailable") from exc
        verify_manifest(root, retained, release_sha=head)
    if arguments.output is not None:
        arguments.output.write_bytes(canonical_json_bytes(manifest))
    print(f"EXACT_RELEASE_SHA={head}")
    print(f"EXACT_RELEASE_MANIFEST_SHA256={manifest['manifest_sha256']}")
    print(f"EXACT_RELEASE_SOURCE_FILE_COUNT={manifest['source_file_count']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ExactReleaseError as exc:
        print(f"EXACT_RELEASE_VERIFY_FAILED={exc}")
        raise SystemExit(2) from None
