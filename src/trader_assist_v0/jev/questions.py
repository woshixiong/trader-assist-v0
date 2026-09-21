from __future__ import annotations

from collections.abc import Mapping
from typing import Final, Protocol, cast

from .contracts import (
    ArmAResponse,
    ArmBResponse,
    ChoiceDistribution,
    EntryAction,
    SetupDirection,
    SetupFamily,
    SetupState,
)

SETUP_FAMILY: Final = "SETUP_FAMILY"
SETUP_DIRECTION: Final = "SETUP_DIRECTION"
SETUP_STATE: Final = "SETUP_STATE"
ENTRY_ACTION_NOW: Final = "ENTRY_ACTION_NOW"

SETUP_FAMILY_LABELS: Final = tuple(item.value for item in SetupFamily)
SETUP_DIRECTION_LABELS: Final = tuple(item.value for item in SetupDirection)
SETUP_STATE_LABELS: Final = tuple(item.value for item in SetupState)
ENTRY_ACTION_LABELS: Final = tuple(item.value for item in EntryAction)

type ChoiceQuestion = dict[str, object]
type QuestionSet = dict[str, ChoiceQuestion]


class _ChoiceAnswer(Protocol):
    choice: str
    probabilities: Mapping[str, float]


class _SystemOneResponse(Protocol):
    choices: Mapping[str, _ChoiceAnswer]


def _question(instructions: str, labels: tuple[str, ...]) -> ChoiceQuestion:
    return {
        "type": "choice",
        "instructions": instructions,
        "criteria": {label: None for label in labels},
    }


def arm_b_questions() -> QuestionSet:
    return {
        ENTRY_ACTION_NOW: _question(
            "Choose the justified immediate entry action from the bounded current market state.",
            ENTRY_ACTION_LABELS,
        )
    }


def arm_a_questions() -> QuestionSet:
    return {
        SETUP_FAMILY: _question(
            "Classify the current canonical setup family, or NONE.", SETUP_FAMILY_LABELS
        ),
        SETUP_DIRECTION: _question(
            "Classify the current canonical setup direction, or NONE.", SETUP_DIRECTION_LABELS
        ),
        SETUP_STATE: _question(
            "Classify the current canonical setup state, or NONE.", SETUP_STATE_LABELS
        ),
        ENTRY_ACTION_NOW: _question(
            "Choose the justified immediate entry action from the bounded current market state.",
            ENTRY_ACTION_LABELS,
        ),
    }


def extract_choice(answer: _ChoiceAnswer, allowed_labels: tuple[str, ...]) -> ChoiceDistribution:
    probabilities = dict(answer.probabilities)
    if set(probabilities) != set(allowed_labels):
        missing = sorted(set(allowed_labels) - set(probabilities))
        extra = sorted(set(probabilities) - set(allowed_labels))
        raise ValueError(f"incomplete Choice probabilities: missing={missing}, extra={extra}")
    return ChoiceDistribution(
        selected=answer.choice,
        probabilities=tuple((label, probabilities[label]) for label in allowed_labels),
    )


def extract_arm_a(response: object) -> ArmAResponse:
    choices = cast(_SystemOneResponse, response).choices
    required = {SETUP_FAMILY, SETUP_DIRECTION, SETUP_STATE, ENTRY_ACTION_NOW}
    if set(choices) != required:
        raise ValueError("ARM A response must contain exactly the four frozen Choice answers")
    return ArmAResponse(
        setup_family=extract_choice(choices[SETUP_FAMILY], SETUP_FAMILY_LABELS),
        setup_direction=extract_choice(choices[SETUP_DIRECTION], SETUP_DIRECTION_LABELS),
        setup_state=extract_choice(choices[SETUP_STATE], SETUP_STATE_LABELS),
        entry_action_now=extract_choice(choices[ENTRY_ACTION_NOW], ENTRY_ACTION_LABELS),
    )


def extract_arm_b(response: object) -> ArmBResponse:
    choices = cast(_SystemOneResponse, response).choices
    if set(choices) != {ENTRY_ACTION_NOW}:
        raise ValueError("ARM B response must contain exactly ENTRY_ACTION_NOW")
    return ArmBResponse(
        entry_action_now=extract_choice(choices[ENTRY_ACTION_NOW], ENTRY_ACTION_LABELS)
    )
