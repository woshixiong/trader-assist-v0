from __future__ import annotations

import ast
from pathlib import Path

import trader_assist_v0.data as data
from trader_assist_v0.contracts import (
    BronzeReplayReportV0,
    RawEventV0,
    RawManifestEntryV0,
)

FORBIDDEN_IMPORTS = {
    "eth_account",
    "httpx",
    "hyperliquid",
    "requests",
    "socket",
    "urllib.request",
    "websockets",
}
FORBIDDEN_TEXT = ("api.hyperliquid.xyz", "testnet", "/exchange")


def test_package_exports() -> None:
    assert data.BronzeStore and data.ManifestWriter and data.replay_segment
    assert RawEventV0 and RawManifestEntryV0 and BronzeReplayReportV0


def test_runtime_and_cli_have_no_network_or_write_capability() -> None:
    base = Path(__file__).resolve().parents[1]
    files = list((base / "src/trader_assist_v0/data").glob("*.py"))
    cli = base / "scripts/replay_v0_01_bronze.py"
    if cli.exists():
        files.append(cli)
    for path in files:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        assert not any(
            any(name == bad or name.startswith(bad + ".") for bad in FORBIDDEN_IMPORTS)
            for name in imports
        ), path
        assert all(token not in text.lower() for token in FORBIDDEN_TEXT), path
