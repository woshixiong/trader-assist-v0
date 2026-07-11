from __future__ import annotations

from trader_assist_v0.contracts.candle_reconciliation import (
    CandleCrossSourceReconciliationV0,
)
from trader_assist_v0.contracts.candles import CandlePayloadExtractionV0


class CandleCrossSourceReconciliationError(ValueError):
    pass


def reconcile_candle_extractions(
    *,
    ws_extraction: CandlePayloadExtractionV0,
    info_extraction: CandlePayloadExtractionV0,
) -> CandleCrossSourceReconciliationV0:
    try:
        return CandleCrossSourceReconciliationV0.bind(
            ws_extraction=ws_extraction,
            info_extraction=info_extraction,
        )
    except TypeError:
        raise
    except (AttributeError, ValueError) as exc:
        raise CandleCrossSourceReconciliationError(
            "A6 extraction authority revalidation or reconciliation derivation failed: "
            f"{exc}"
        ) from exc
