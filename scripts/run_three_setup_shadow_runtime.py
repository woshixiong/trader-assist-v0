#!/usr/bin/env python3
"""Default-off production entrypoint for the public-only Three Setup shadow release."""

from __future__ import annotations

import argparse
import asyncio
import signal
from pathlib import Path

from scripts.run_first_launch_public_runtime import CredentialFileError, _load_credential_file
from scripts.three_setup_shadow_preflight import verify_candidate
from trader_assist_v0.multi_asset_shadow.integration import mature_discord_delivery_adapter
from trader_assist_v0.multi_asset_shadow.production import (
    THREE_SETUP_CONFIG_PATH,
    THREE_SETUP_RELEASE_MODE,
    ThreeSetupProductionError,
    compose_three_setup_application,
    load_three_setup_config,
    validate_three_setup_e4_identity,
)
from trader_assist_v0.runtime.first_launch_notification import HttpsWebhookTransport


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable-three-setup-shadow-runtime", action="store_true")
    parser.add_argument("--mode", default="")
    parser.add_argument("--config-path", type=Path, default=THREE_SETUP_CONFIG_PATH)
    parser.add_argument("--notification-credential-file", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--release-manifest", type=Path)
    parser.add_argument("--staged-root", type=Path)
    parser.add_argument("--expected-release-sha")
    parser.add_argument("--expected-release-tree")
    parser.add_argument("--expected-manifest-digest")
    parser.add_argument("--pip-check-with", type=Path)
    return parser


async def _run(arguments: argparse.Namespace) -> None:
    if arguments.validate_only:
        if None in (
            arguments.release_manifest,
            arguments.staged_root,
            arguments.expected_release_sha,
            arguments.expected_release_tree,
            arguments.expected_manifest_digest,
            arguments.pip_check_with,
        ):
            raise ThreeSetupProductionError("validate-only requires exact release identity")
        verify_candidate(
            root=arguments.staged_root,
            release_manifest=arguments.release_manifest,
            config_path=arguments.config_path,
            expected_sha=arguments.expected_release_sha,
            expected_tree=arguments.expected_release_tree,
            expected_manifest_digest=arguments.expected_manifest_digest,
            pip_check_with=arguments.pip_check_with,
        )
        return
    if arguments.notification_credential_file is None:
        raise ThreeSetupProductionError("normal runtime requires notification credential file")
    config = load_three_setup_config(arguments.config_path)
    validate_three_setup_e4_identity(config)
    notification = _load_credential_file(
        arguments.notification_credential_file, timeout_seconds=10.0
    )
    application = compose_three_setup_application(
        config=config,
        notification_adapter=mature_discord_delivery_adapter(
            config=notification, transport=HttpsWebhookTransport()
        ),
    )
    shutdown = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, shutdown.set)
    await application.run(shutdown)


def main(argv: tuple[str, ...] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if (
        not arguments.enable_three_setup_shadow_runtime
        or arguments.mode != THREE_SETUP_RELEASE_MODE
    ):
        raise ThreeSetupProductionError("Three Setup activation is default-off")
    asyncio.run(_run(arguments))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CredentialFileError, OSError, ValueError, ThreeSetupProductionError) as exc:
        print(f"Three Setup runtime configuration failed: {type(exc).__name__}")
        raise SystemExit(2) from None
