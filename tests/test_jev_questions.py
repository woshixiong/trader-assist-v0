from __future__ import annotations

from types import SimpleNamespace

import pytest

from trader_assist_v0.jev.questions import (
    ENTRY_ACTION_LABELS,
    ENTRY_ACTION_NOW,
    SETUP_DIRECTION,
    SETUP_DIRECTION_LABELS,
    SETUP_FAMILY,
    SETUP_FAMILY_LABELS,
    SETUP_STATE,
    SETUP_STATE_LABELS,
    arm_a_questions,
    arm_b_questions,
    extract_arm_a,
    extract_arm_b,
)


def _answer(labels: tuple[str, ...], selected: str) -> SimpleNamespace:
    probability = 1.0 / len(labels)
    probs = {label: probability for label in labels}
    return SimpleNamespace(choice=selected, probabilities=probs)


def test_question_names_and_labels_are_exact() -> None:
    arm_b = arm_b_questions()
    assert tuple(arm_b) == (ENTRY_ACTION_NOW,)
    assert tuple(arm_b[ENTRY_ACTION_NOW]["criteria"]) == ENTRY_ACTION_LABELS
    arm_a = arm_a_questions()
    assert tuple(arm_a) == (SETUP_FAMILY, SETUP_DIRECTION, SETUP_STATE, ENTRY_ACTION_NOW)
    assert tuple(arm_a[SETUP_FAMILY]["criteria"]) == SETUP_FAMILY_LABELS
    assert tuple(arm_a[SETUP_DIRECTION]["criteria"]) == SETUP_DIRECTION_LABELS
    assert tuple(arm_a[SETUP_STATE]["criteria"]) == SETUP_STATE_LABELS
    assert tuple(arm_a[ENTRY_ACTION_NOW]["criteria"]) == ENTRY_ACTION_LABELS


def test_complete_choice_probabilities_are_retained_in_frozen_order() -> None:
    response = SimpleNamespace(
        choices={ENTRY_ACTION_NOW: _answer(ENTRY_ACTION_LABELS, "WAIT")}
    )
    extracted = extract_arm_b(response).entry_action_now
    assert extracted.selected == "WAIT"
    assert tuple(label for label, _ in extracted.probabilities) == ENTRY_ACTION_LABELS
    assert sum(probability for _, probability in extracted.probabilities) == pytest.approx(1.0)


def test_incomplete_choice_distribution_fails_closed() -> None:
    answer = _answer(ENTRY_ACTION_LABELS, "WAIT")
    del answer.probabilities["PASS"]
    with pytest.raises(ValueError, match="incomplete Choice probabilities"):
        extract_arm_b(SimpleNamespace(choices={ENTRY_ACTION_NOW: answer}))


def test_arm_a_extracts_all_four_choices() -> None:
    response = SimpleNamespace(
        choices={
            SETUP_FAMILY: _answer(SETUP_FAMILY_LABELS, "NONE"),
            SETUP_DIRECTION: _answer(SETUP_DIRECTION_LABELS, "NONE"),
            SETUP_STATE: _answer(SETUP_STATE_LABELS, "NONE"),
            ENTRY_ACTION_NOW: _answer(ENTRY_ACTION_LABELS, "PASS"),
        }
    )
    extracted = extract_arm_a(response)
    assert extracted.setup_family.selected == "NONE"
    assert extracted.entry_action_now.selected == "PASS"
