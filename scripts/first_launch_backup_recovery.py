"""Operator-invoked, encrypted off-host backup and restore verification helper.

This script never starts or stops a service, creates storage, reads credentials,
or deletes snapshots.  It requires separately-authorized existing ``age`` and
``rclone`` installations and deliberately prints only paths and hashes.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import cast

from trader_assist_v0.operations.backup_recovery import (
    BackupAsset,
    BackupRecoveryError,
    BackupRequest,
    create_encrypted_backup,
    upload_encrypted_backup,
    verify_remote_backup,
)


def _named_path(value: str) -> tuple[str, Path]:
    name, separator, raw_path = value.partition("=")
    if not separator or not name or not raw_path:
        raise argparse.ArgumentTypeError("value must be NAME=PATH")
    return name, Path(raw_path)


def _create_command(args: argparse.Namespace) -> int:
    assets = [
        BackupAsset("sqlite", "runtime", args.database),
        BackupAsset("config", "public-env", args.public_env),
        BackupAsset("config", "risk-configuration", args.risk_configuration),
    ]
    assets.extend(BackupAsset("sqlite", name, path) for name, path in args.additional_database)
    assets.extend(BackupAsset("config", name, path) for name, path in args.additional_config)
    artifact = create_encrypted_backup(
        BackupRequest(
            assets=tuple(assets),
            encrypted_output=args.output,
            repository=args.repository,
            deployed_sha=args.deployed_sha,
            service_name=args.service_name,
            python_executable=args.python_executable,
            storage_destination_class=args.storage_destination_class,
            age_recipient=args.age_recipient,
        )
    )
    print(f"encrypted_artifact={artifact.encrypted_path}")
    print(f"encrypted_sha256={artifact.encrypted_sha256}")
    print(f"manifest_sha256={artifact.manifest_sha256}")
    return 0


def _upload_command(args: argparse.Namespace) -> int:
    upload_encrypted_backup(args.artifact, args.remote_destination)
    print("off_host_upload=PASS")
    return 0


def _verify_remote_command(args: argparse.Namespace) -> int:
    result = verify_remote_backup(
        remote_source=args.remote_source,
        expected_encrypted_sha256=args.expected_encrypted_sha256,
        age_identity_file=args.age_identity_file,
        workspace_parent=args.workspace_parent,
    )
    print(f"restore_verification={result['restore_verification']}")
    print(f"database_count={result['database_count']}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="create an encrypted local artifact")
    create.add_argument("--database", type=Path, required=True)
    create.add_argument("--public-env", type=Path, required=True)
    create.add_argument("--risk-configuration", type=Path, required=True)
    create.add_argument("--additional-database", type=_named_path, action="append", default=[])
    create.add_argument("--additional-config", type=_named_path, action="append", default=[])
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--repository", required=True)
    create.add_argument("--deployed-sha", required=True)
    create.add_argument("--service-name", required=True)
    create.add_argument("--python-executable", required=True)
    create.add_argument("--storage-destination-class", required=True)
    create.add_argument("--age-recipient", required=True)
    create.set_defaults(handler=_create_command)
    upload = commands.add_parser("upload", help="upload an existing encrypted artifact")
    upload.add_argument("--artifact", type=Path, required=True)
    upload.add_argument("--remote-destination", required=True)
    upload.set_defaults(handler=_upload_command)
    verify = commands.add_parser("verify-remote", help="download and verify an encrypted backup")
    verify.add_argument("--remote-source", required=True)
    verify.add_argument("--expected-encrypted-sha256", required=True)
    verify.add_argument("--age-identity-file", type=Path, required=True)
    verify.add_argument("--workspace-parent", type=Path, required=True)
    verify.set_defaults(handler=_verify_remote_command)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        handler = cast(Callable[[argparse.Namespace], int], args.handler)
        return handler(args)
    except BackupRecoveryError as exc:
        raise SystemExit(f"backup recovery: FAIL: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
