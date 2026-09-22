from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Prediction = Literal["UP", "DOWN", "FLAT"]
ActualOutcome = Literal["UP", "DOWN", "FLAT"]


class OutcomeRecord(BaseModel):
    """Future market observation used for deterministic FDML evaluation."""

    experiment_id: str
    observation_timestamp: datetime
    evaluation_window: int = Field(gt=0)
    reference_price: float = Field(gt=0)
    future_price: float = Field(gt=0)
    price_change: float
    volatility_change: float


class EvaluationResult(BaseModel):
    """Deterministic evaluation output for a recorded prediction."""

    experiment_id: str
    prediction: Prediction
    actual_outcome: ActualOutcome
    correctness: bool
    confidence: float = Field(ge=0.0, le=1.0)
    evaluation_timestamp: datetime


def classify_outcome(price_change: float, threshold: float = 0.0) -> ActualOutcome:
    """Classify observed price movement without external state."""

    if price_change > threshold:
        return "UP"
    if price_change < -threshold:
        return "DOWN"
    return "FLAT"


def evaluate_prediction(
    *,
    experiment_id: str,
    prediction: Prediction,
    outcome: OutcomeRecord,
    confidence: float,
    evaluation_timestamp: datetime,
) -> EvaluationResult:
    """Evaluate a prediction against a fixed future observation.

    This function is intentionally deterministic and has no market, exchange,
    strategy, or model dependencies.
    """

    actual = classify_outcome(outcome.price_change)
    return EvaluationResult(
        experiment_id=experiment_id,
        prediction=prediction,
        actual_outcome=actual,
        correctness=prediction == actual,
        confidence=confidence,
        evaluation_timestamp=evaluation_timestamp,
    )
