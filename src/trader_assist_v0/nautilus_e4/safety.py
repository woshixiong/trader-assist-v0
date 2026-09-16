"""Hard credential-negative boundary for public-only E4 Capture."""

from __future__ import annotations

from collections.abc import Mapping

from .contracts import ZeroWriteProof

# rc4 adapter config names plus common environment spellings are rejected.
FORBIDDEN_CONFIG_KEYS = frozenset(
    {
        "api_key",
        "api_secret",
        "private_key",
        "wallet_address",
        "vault_address",
        "account_address",
        "account_id",
        "exec_clients",
        "execution_client",
        "signer",
    }
)
FORBIDDEN_ENV_KEYS = frozenset(
    {
        "HYPERLIQUID_API_KEY",
        "HYPERLIQUID_API_SECRET",
        "HYPERLIQUID_PRIVATE_KEY",
        "HYPERLIQUID_PK",
        "HYPERLIQUID_TESTNET_PK",
        "HYPERLIQUID_VAULT",
        "HYPERLIQUID_TESTNET_VAULT",
        "HYPERLIQUID_ACCOUNT_ADDRESS",
        "HYPERLIQUID_WALLET_ADDRESS",
        "HYPERLIQUID_VAULT_ADDRESS",
        "NAUTILUS_HYPERLIQUID_API_KEY",
        "NAUTILUS_HYPERLIQUID_API_SECRET",
        "NAUTILUS_HYPERLIQUID_PRIVATE_KEY",
        "NAUTILUS_HYPERLIQUID_WALLET_ADDRESS",
    }
)


def _configured(value: object) -> bool:
    return value is not None and value is not False and value != "" and value != {} and value != ()


def _walk_forbidden(config: Mapping[str, object], *, path: str = "config") -> list[str]:
    found: list[str] = []
    for key, value in config.items():
        normalized = key.strip().lower().replace("-", "_")
        current = f"{path}.{key}"
        if normalized in FORBIDDEN_CONFIG_KEYS and _configured(value):
            found.append(current)
        if isinstance(value, Mapping):
            found.extend(_walk_forbidden(value, path=current))
    return found


def assert_public_only(
    *, env: Mapping[str, str], config: Mapping[str, object] | None = None
) -> ZeroWriteProof:
    present_env = sorted(key for key in FORBIDDEN_ENV_KEYS if _configured(env.get(key)))
    present_config = [] if config is None else sorted(_walk_forbidden(config))
    if present_env or present_config:
        names = present_env + present_config
        raise RuntimeError(
            "forbidden exchange credential/write configuration present: " + ", ".join(names)
        )
    return ZeroWriteProof()
