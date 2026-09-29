"""Launch the isolated zero-write operator process; no runtime service control."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from trader_assist_v0.operator.contracts import OperatorConfig, OperatorCredential
from trader_assist_v0.operator.service import create_app


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = OperatorConfig.load(args.config)
    if config.tls_cert_path is None or config.tls_key_path is None:
        parser.error("direct TLS certificate/key required for operator process")
    credential = OperatorCredential.load(config.credential_path)
    app = create_app(config, credential)
    uvicorn.run(
        app,
        host=config.bind_host,
        port=config.bind_port,
        workers=1,
        proxy_headers=False,
        access_log=False,
        ssl_certfile=str(config.tls_cert_path),
        ssl_keyfile=str(config.tls_key_path),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
