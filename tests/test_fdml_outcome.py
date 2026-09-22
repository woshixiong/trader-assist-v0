from datetime import datetime

from trader_assist_v0.fast_decision_model_lab.outcome import (
    OutcomeRecord,
    classify_outcome,
    evaluate_prediction,
)


def test_classify_outcome_is_deterministic():
    assert classify_outcome(1.0) == "UP"
    assert classify_outcome(-1.0) == "DOWN"
    assert classify_outcome(0.0) == "FLAT"


def test_evaluate_prediction_matches_future_observation():
    record = OutcomeRecord(
        experiment_id="exp-1",
        observation_timestamp=datetime(2026, 1, 1),
        evaluation_window=5,
        reference_price=100.0,
        future_price=102.0,
        price_change=2.0,
        volatility_change=0.1,
    )

    result = evaluate_prediction(
        experiment_id="exp-1",
        prediction="UP",
        outcome=record,
        confidence=0.8,
        evaluation_timestamp=datetime(2026, 1, 1, 0, 5),
    )

    assert result.actual_outcome == "UP"
    assert result.correctness is True
