from __future__ import annotations

import ast
from pathlib import Path


def test_neutral_core_has_no_typesafe_import_except_adapter_and_no_jev_core() -> None:
    root = Path(__file__).parents[1] / "src" / "trader_assist_v0"
    neutral = root / "fast_decision_model_lab"
    for path in neutral.rglob("*.py"):
        if path.as_posix().endswith("adapters/typesafe.py"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".", 1)[0] != "typesafe_sdk" for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".", 1)[0] != "typesafe_sdk"
    assert not (root / "jev").exists()


def test_no_custom_network_exchange_write_or_credential_injection_surface() -> None:
    root = Path(__file__).parents[1] / "src" / "trader_assist_v0" / "fast_decision_model_lab"
    forbidden = {"httpx", "httpx2", "requests", "socket", "websockets"}
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not ({alias.name.split(".", 1)[0] for alias in node.names} & forbidden)
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".", 1)[0] not in forbidden
    adapter = (root / "adapters" / "typesafe.py").read_text(encoding="utf-8").lower()
    assert "api_key=" not in adapter
    assert "wallet" not in adapter
    assert "signing" not in adapter
