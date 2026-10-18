"""Decisive official rc7 wheel/API proof; never loads exchange credentials or runs a node."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

VERSION = "2.0.0rc7"
WHEEL = "nautilus_trader-2.0.0rc7-cp313-cp313-manylinux_2_34_x86_64.whl"
SHA256 = "b3928f37d75d57508030a421dc762186ad1f9ffc5d5420d7daf1d2c6badb8044"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assert sys.version_info[:2] == (3, 13)
    assert platform.system() == "Linux" and platform.machine() == "x86_64"
    with urllib.request.urlopen(f"https://pypi.org/pypi/nautilus_trader/{VERSION}/json", timeout=60) as response:
        metadata = json.load(response)
    artifact = next(item for item in metadata["urls"] if item["filename"] == WHEEL)
    assert artifact["digests"]["sha256"] == SHA256
    wheel = args.output / WHEEL
    urllib.request.urlretrieve(artifact["url"], wheel)
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == SHA256
    # Stubs make decisive evidence available on the development platform lacking this wheel.
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.endswith((".pyi", ".py", "METADATA")):
                archive.extract(name, args.output / "api")
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", str(wheel)], check=True)
    subprocess.run([sys.executable, "-m", "pip", "check"], check=True)
    from importlib.metadata import version
    from nautilus_trader.adapters.hyperliquid import HyperliquidExecutionClientFactory
    from nautilus_trader.adapters.sandbox import SandboxExecutionClientFactory
    from nautilus_trader.backtest import BacktestNode
    from nautilus_trader.live import LiveNode
    from nautilus_trader.persistence import ParquetDataCatalog, StreamingConfig

    assert version("nautilus-trader") == VERSION
    assert all((HyperliquidExecutionClientFactory, SandboxExecutionClientFactory,
                BacktestNode, LiveNode, ParquetDataCatalog, StreamingConfig))
    proof = {"version": VERSION, "wheel": WHEEL, "sha256": SHA256,
             "python": platform.python_version(), "platform": platform.platform(),
             "wheel_api": "PASS", "external_order_writes": 0}
    (args.output / "proof.json").write_text(json.dumps(proof, indent=2) + "\n")
    wheel.unlink()
    print(json.dumps(proof))


if __name__ == "__main__":
    main()
