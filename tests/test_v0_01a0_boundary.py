from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_IMPORTS = {
    "eth_account",
    "httpx",
    "hyperliquid",
    "requests",
    "socket",
    "urllib.request",
    "websockets",
}
FORBIDDEN_RUNTIME_TEXT = (
    "api.hyperliquid.xyz",
    "testnet",
    "/exchange",
)


def test_a0_runtime_has_no_network_or_exchange_write_capability() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    files = [
        *sorted((repository_root / "src/trader_assist_v0/data").glob("*.py")),
        repository_root / "src/trader_assist_v0/contracts/source_catalog.py",
        repository_root / "scripts/replay_v0_01_bronze.py",
    ]
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
        lowered = text.lower()
        assert all(marker not in lowered for marker in FORBIDDEN_RUNTIME_TEXT), path
