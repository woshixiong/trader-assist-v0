"""Bind the existing approved evaluator to immutable decision evidence.

The registered package emits strategy research decisions, not approved native
order intents. Preserve every outcome and reject execution until that mapping
is qualified; do not invent sizing, entry economics or another strategy.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from trader_assist_v0.multi_asset_shadow.models import ClosedBar
from trader_assist_v0.nautilus_pilot.contracts import PilotEvaluationEnvelope, StrategyInputEvent
from trader_assist_v0.nautilus_pilot.strategy_package import (
    PilotStrategyEvaluator,
    StrategyPackageManifest,
)

from .shadow_ledger import ShadowLedger


class RegisteredShadowEvaluator:
    def __init__(
        self,
        *,
        manifest: StrategyPackageManifest,
        market_id: str,
        minimum_tick: Decimal,
        ledger: ShadowLedger,
    ) -> None:
        if (
            ledger.strategy_id != manifest.package_version
            or ledger.strategy_version != manifest.strategy_version
        ):
            raise ValueError("ledger and approved strategy identity differ")
        self.evaluator = PilotStrategyEvaluator(
            manifest=manifest, market_id=market_id, minimum_tick=minimum_tick
        )
        self.ledger = ledger

    def evaluate(self, bar: ClosedBar, *, now_ns: int) -> PilotEvaluationEnvelope | None:
        if bar.close_time_ms * 1_000_000 > now_ns:
            raise ValueError("no lookahead: bar has not closed")
        event = StrategyInputEvent.create(
            strategy_package_hash=self.evaluator.manifest.manifest_hash, closed_bar=bar
        )
        decision_id = f"evaluation:{event.canonical_hash}"
        # A replayed input must not mutate strategy state or inflate its denominator.
        if self.ledger.db.execute(
            "SELECT 1 FROM events WHERE event_id=?", (f"decision:{decision_id}",)
        ).fetchone():
            return None
        try:
            output = self.evaluator.evaluate(event)
        except Exception as exc:
            self.ledger.decision(
                decision_id=decision_id,
                ts_ns=now_ns,
                source_identity=event.canonical_hash,
                source_ts_ns=event.ts_event,
                outcome="REJECT",
                details={"reason": "STRATEGY_EVALUATION_FAILED", "error_type": type(exc).__name__},
            )
            raise
        details: dict[str, Any]
        if output is None:
            outcome, details = "WAIT", {"reason": "STRATEGY_CONTEXT_INSUFFICIENT"}
        else:
            outcome = "REJECT" if output.kernel_result.decisions else "PASS"
            details = {
                "evaluation": output.model_dump(mode="json"),
                "execution_status": "NATIVE_ORDER_MAPPING_NOT_QUALIFIED",
            }
        self.ledger.decision(
            decision_id=decision_id,
            ts_ns=now_ns,
            source_identity=event.canonical_hash,
            source_ts_ns=event.ts_event,
            outcome=outcome,
            details=details,
        )
        return output
