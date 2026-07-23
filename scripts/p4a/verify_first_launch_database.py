#!/usr/bin/env python3
"""Read-only SQLite evidence verifier for the approved First Launch state root."""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote

PUBLIC_ENV = Path("/etc/trader-assist-v0/public.env")
STATE_ROOT = Path("/var/lib/trader-assist-v0")
DATABASE_KEY = "TRADER_ASSIST_V0_DATABASE_PATH"
PHASES = {
    "existing-before-smoke": True,
    "fresh-pre-start": False,
    "fresh-post-creation": True,
    "final-post-smoke": True,
}
ASSIGNMENT = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")


class VerificationError(Exception):
    """A required offline evidence condition was not proven."""


def database_path(env_file: Path) -> Path:
    if not env_file.is_file() or env_file.is_symlink():
        raise VerificationError("public environment unavailable")
    values: list[str] = []
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"):
            continue
        match = ASSIGNMENT.fullmatch(raw)
        if match is None:
            if raw.startswith(DATABASE_KEY):
                raise VerificationError("malformed database assignment")
            continue
        key, value = match.groups()
        if key == DATABASE_KEY:
            if "=" in value:
                raise VerificationError("malformed database assignment")
            values.append(value)
    if len(values) != 1 or not values[0]:
        raise VerificationError("duplicate or missing database assignment")
    return Path(values[0])


def checked_target(path: Path, root: Path) -> Path:
    if not path.is_absolute() or ".." in path.parts or path.name in {"", ".", ".."}:
        raise VerificationError("database path is malformed")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise VerificationError("database target is not a regular file")
    try:
        root_real = root.resolve(strict=True)
        parent_real = path.parent.resolve(strict=True)
    except OSError as exc:
        raise VerificationError("state root or database parent unavailable") from exc
    if not root_real.is_dir() or os.path.commonpath((root_real, parent_real)) != str(root_real):
        raise VerificationError("database path escapes state root")
    return parent_real / path.name


def integrity(path: Path) -> None:
    try:
        connection = sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True)
        try:
            rows = connection.execute("PRAGMA integrity_check").fetchall()
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise VerificationError("read-only SQLite open or integrity check failed") from exc
    if rows != [("ok",)]:
        raise VerificationError("SQLite integrity result is not exactly one ok")


def verify(phase: str, env_file: Path = PUBLIC_ENV, state_root: Path = STATE_ROOT) -> None:
    expected_exists = PHASES[phase]
    target = checked_target(database_path(env_file), state_root)
    if target.exists() != expected_exists:
        raise VerificationError("database existence does not match evidence phase")
    if expected_exists:
        integrity(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=sorted(PHASES))
    args = parser.parse_args(argv)
    try:
        verify(args.phase)
    except VerificationError as exc:
        print(f"SAFE_STOP: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {args.phase}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
