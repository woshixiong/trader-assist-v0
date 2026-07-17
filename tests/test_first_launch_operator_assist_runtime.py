from __future__ import annotations

import ast
import asyncio
from pathlib import Path

import pytest

from trader_assist_v0.runtime.first_launch_operator_assist import (
    OperatorAssistError,
    PermitError,
    run_first_launch_operator_assist,
)


def test_missing_permit_stops_before_any_public_transport(tmp_path: Path) -> None:
    calls = {"http": 0, "websocket": 0}

    def http_post(_body: str) -> object:
        calls["http"] += 1
        raise AssertionError("transport must not run")

    async def websocket() -> object:
        calls["websocket"] += 1
        raise AssertionError("transport must not run")

    with pytest.raises(PermitError):
        asyncio.run(
            run_first_launch_operator_assist(
                permit_path=tmp_path / "missing-permit.json",
                shadow_output=tmp_path / "record.json",
                http_post=http_post,  # type: ignore[arg-type]
                websocket_factory=websocket,  # type: ignore[arg-type]
            )
        )
    assert calls == {"http": 0, "websocket": 0}


def test_cli_surface_is_exactly_two_public_arguments() -> None:
    source = Path("scripts/run_first_launch_operator_assist.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    options = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_argument"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    assert options == {"--permit", "--shadow-output"}
    assert "--submit" not in source


def test_runtime_is_default_off_at_import_and_has_no_execution_client() -> None:
    source = Path("src/trader_assist_v0/runtime/first_launch_operator_assist.py").read_text(
        encoding="utf-8"
    )
    assert "api.hyperliquid.xyz/info" in source
    assert "api.hyperliquid.xyz/ws" in source
    assert "private_key" not in source
    assert "sign(" not in source
    assert "cancel" not in source.lower()
    assert issubclass(PermitError, OperatorAssistError)
