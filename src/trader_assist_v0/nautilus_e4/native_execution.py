"""Default-off native execution construction. No live client is built or run here.

The returned config/factory is evidence of the supported technical seam, not
permission to load a signer, connect a private API, or submit an order.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .contracts import GuardDecision, GuardInputs
from .guard import evaluate_entry_guard
from .safety import assert_public_only


@dataclass(frozen=True)
class SubmitCertificate:
    instrument_id: str
    epoch: int
    valid_until_ns: int
    signal_valid_until_ns: int
    account_reconciled: bool
    price_known: bool
    native_connected: bool
    feed_health: str
    generated_ns: int


def final_submit_reasons(
    *,
    certificate: SubmitCertificate | None,
    instrument_id: str,
    epoch: int,
    now_ns: int,
    inputs: GuardInputs,
) -> tuple[str, ...]:
    reasons = list(evaluate_entry_guard(inputs).reason_codes)
    if certificate is None:
        return (*reasons, "NO_HEALTH_CERTIFICATE")
    if certificate.instrument_id != instrument_id:
        reasons.append("WRONG_INSTRUMENT")
    if certificate.epoch != epoch:
        reasons.append("CONTINUITY_EPOCH_CHANGED")
    if (
        not certificate.generated_ns
        <= now_ns
        <= min(certificate.valid_until_ns, certificate.signal_valid_until_ns)
    ):
        reasons.append("STALE_CERTIFICATE_OR_SIGNAL")
    if certificate.feed_health != "HEALTHY" or not certificate.native_connected:
        reasons.append("FEED_NOT_LIVE")
    if not certificate.account_reconciled:
        reasons.append("ACCOUNT_UNKNOWN_OR_UNRECONCILED")
    if not certificate.price_known:
        reasons.append("PRICE_UNKNOWN")
    return tuple(reasons)


def native_execution_contract(*, env: Mapping[str, str]) -> tuple[Any, Any, Any, Any]:
    """Construct inert official config/factory only, with no credential resolution."""
    assert_public_only(env=env)
    from nautilus_trader.adapters.hyperliquid import (
        HyperliquidEnvironment,
        HyperliquidExecutionClientConfig,
        HyperliquidExecutionClientFactory,
    )
    from nautilus_trader.live import LiveExecutionEngineConfig, LiveRiskEngineConfig
    from nautilus_trader.model import AccountId

    config = HyperliquidExecutionClientConfig(
        account_id=AccountId("HYPERLIQUID-001"),
        environment=HyperliquidEnvironment.MAINNET,
        private_key=None,
        account_address=None,
        vault_address=None,
    )
    risk = LiveRiskEngineConfig(bypass=False)
    execution = LiveExecutionEngineConfig(reconciliation=True)
    if risk.bypass or not execution.reconciliation:
        raise RuntimeError("native risk/reconciliation invariant violated")
    return config, HyperliquidExecutionClientFactory(), risk, execution


def require_entry_certificate(**kwargs: Any) -> None:
    reasons = final_submit_reasons(**kwargs)
    if reasons:
        raise PermissionError("NO_SUBMIT:" + ",".join(reasons))
    if evaluate_entry_guard(kwargs["inputs"]).decision is not GuardDecision.PASS:
        raise PermissionError("NO_SUBMIT:ENTRY_GUARD")
