#!/usr/bin/env python3
"""Operator entry point for the bounded Restic recovery adapter."""

from __future__ import annotations

import argparse
from pathlib import Path

from trader_assist_v0.operations.backup_recovery import (
    FIRST_LAUNCH_PROFILE,
    FULL_MULTI_ASSET_PROFILE,
    THREE_SETUP_PROFILE,
    RecoveryPaths,
    backup_recovery,
    check_repository,
    verify_snapshot,
)


def _paths(arguments: argparse.Namespace) -> RecoveryPaths:
    return RecoveryPaths(
        multi_asset_evidence=(
            Path(arguments.multi_asset_evidence) if arguments.multi_asset_evidence else None
        ),
        multi_asset_registry=(
            Path(arguments.multi_asset_registry) if arguments.multi_asset_registry else None
        ),
    )


def _add_credentials(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--restic-password-file")
    group.add_argument("--restic-password-command")


def _add_profile(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--profile",
        choices=(FIRST_LAUNCH_PROFILE, FULL_MULTI_ASSET_PROFILE, THREE_SETUP_PROFILE),
        required=True,
    )
    parser.add_argument("--multi-asset-evidence")
    parser.add_argument("--multi-asset-registry")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup")
    backup.add_argument("--repository", required=True)
    backup.add_argument("--deployed-git-sha", required=True)
    _add_profile(backup)
    _add_credentials(backup)
    verify = commands.add_parser("verify")
    verify.add_argument("--repository", required=True)
    verify.add_argument("--snapshot-id", required=True)
    verify.add_argument("--expected-git-sha", required=True)
    verify.add_argument(
        "--profile",
        choices=(FIRST_LAUNCH_PROFILE, FULL_MULTI_ASSET_PROFILE, THREE_SETUP_PROFILE),
        required=True,
    )
    _add_credentials(verify)
    check = commands.add_parser("check")
    check.add_argument("--repository", required=True)
    check.add_argument("--read-data", action="store_true")
    _add_credentials(check)
    arguments = parser.parse_args()
    password_file = Path(arguments.restic_password_file) if arguments.restic_password_file else None
    password_command = arguments.restic_password_command
    if arguments.command == "backup":
        evidence = backup_recovery(
            profile=arguments.profile,
            paths=_paths(arguments),
            deployed_git_sha=arguments.deployed_git_sha,
            repository=arguments.repository,
            password_file=password_file,
            password_command=password_command,
        )
        print(f"RESTIC_SNAPSHOT_ID={evidence.snapshot_id}")
    elif arguments.command == "verify":
        print(
            verify_snapshot(
                snapshot_id=arguments.snapshot_id,
                repository=arguments.repository,
                expected_git_sha=arguments.expected_git_sha,
                expected_profile=arguments.profile,
                password_file=password_file,
                password_command=password_command,
            )
        )
    else:
        check_repository(
            repository=arguments.repository,
            password_file=password_file,
            password_command=password_command,
            read_data=arguments.read_data,
        )
        print("RESTIC_REPOSITORY_CHECK_PASSED")


if __name__ == "__main__":
    main()
