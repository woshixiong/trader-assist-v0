#!/usr/bin/env python3
"""Default-off production entrypoint for the public-only Three Setup shadow release."""

from __future__ import annotations

import argparse
import asyncio
import signal
from pathlib import Path

from scripts.run_first_launch_public_runtime import CredentialFileError, _load_credential_file
from trader_assist_v0.multi_asset_shadow.integration import mature_discord_delivery_adapter
from trader_assist_v0.multi_asset_shadow.production import (
    THREE_SETUP_CONFIG_PATH,
    THREE_SETUP_RELEASE_MODE,
    ThreeSetupProductionError,
    compose_three_setup_application,
    load_three_setup_config,
)
from trader_assist_v0.runtime.first_launch_notification import HttpsWebhookTransport


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable-three-setup-shadow-runtime", action="store_true")
    parser.add_argument("--mode", default="")
    parser.add_argument("--config-path", type=Path, default=THREE_SETUP_CONFIG_PATH)
    parser.add_argument("--notification-credential-file", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    return parser


async def _run(arguments: argparse.Namespace) -> None:
    config = load_three_setup_config(arguments.config_path)
    notification = _load_credential_file(
        arguments.notification_credential_file, timeout_seconds=10.0
    )
    if arguments.validate_only:
        return
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
