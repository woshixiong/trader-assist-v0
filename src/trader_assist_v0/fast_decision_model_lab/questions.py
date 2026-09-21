from __future__ import annotations

from typing import Final

from .contracts import (
    DecisionArm,
    DecisionQuestion,
    EntryAction,
    QuestionPack,
    SetupDirection,
    SetupFamily,
    SetupState,
)

SETUP_FAMILY: Final = "SETUP_FAMILY"
SETUP_DIRECTION: Final = "SETUP_DIRECTION"
SETUP_STATE: Final = "SETUP_STATE"
ENTRY_ACTION_NOW: Final = "ENTRY_ACTION_NOW"
QUESTION_PACK_VERSION: Final = "FAST_DECISION_QUESTIONS_V0"

SETUP_FAMILY_LABELS: Final = tuple(item.value for item in SetupFamily)
SETUP_DIRECTION_LABELS: Final = tuple(item.value for item in SetupDirection)
SETUP_STATE_LABELS: Final = tuple(item.value for item in SetupState)
ENTRY_ACTION_LABELS: Final = tuple(item.value for item in EntryAction)


def model_native_question_pack() -> QuestionPack:
    return QuestionPack(
        question_pack_id="MODEL_NATIVE_ENTRY_V0",
        version=QUESTION_PACK_VERSION,
        arm=DecisionArm.MODEL_NATIVE,
        questions=(
            DecisionQuestion(
                name=ENTRY_ACTION_NOW,
                instructions=(
                    "Choose the justified immediate entry action from the bounded "
                    "current market state."
                ),
                allowed_labels=ENTRY_ACTION_LABELS,
            ),
        ),
    )


def strategy_informed_question_pack() -> QuestionPack:
    return QuestionPack(
        question_pack_id="STRATEGY_INFORMED_ENTRY_V0",
        version=QUESTION_PACK_VERSION,
        arm=DecisionArm.STRATEGY_INFORMED,
        questions=(
            DecisionQuestion(
                name=SETUP_FAMILY,
                instructions="Classify the current canonical setup family, or NONE.",
                allowed_labels=SETUP_FAMILY_LABELS,
            ),
            DecisionQuestion(
                name=SETUP_DIRECTION,
                instructions="Classify the current canonical setup direction, or NONE.",
                allowed_labels=SETUP_DIRECTION_LABELS,
            ),
            DecisionQuestion(
                name=SETUP_STATE,
                instructions="Classify the current canonical setup state, or NONE.",
                allowed_labels=SETUP_STATE_LABELS,
            ),
            DecisionQuestion(
                name=ENTRY_ACTION_NOW,
                instructions=(
                    "Choose the justified immediate entry action from the bounded "
                    "current market state."
                ),
                allowed_labels=ENTRY_ACTION_LABELS,
            ),
        ),
    )
