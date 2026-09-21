from __future__ import annotations

from dataclasses import replace

from trader_assist_v0.fast_decision_model_lab.contracts import (
    STATE_SCHEMA_VERSION,
    DecisionRequest,
    ModelTarget,
)
from trader_assist_v0.fast_decision_model_lab.questions import model_native_question_pack
from trader_assist_v0.fast_decision_model_lab.serialization import (
    canonical_roundtrip,
    canonical_sha256,
)


def _request() -> DecisionRequest:
    pack = model_native_question_pack()
    target = ModelTarget("target-a", "fake-a", "model-a", "rev-a", "adapter-a", "1")
    return DecisionRequest(
        "event-1",
        "inv-1",
        "sha256:snapshot",
        "snapshot",
        123,
        STATE_SCHEMA_VERSION,
        {"b": 2, "a": {"z": 3, "y": 4}},
        pack.arm,
        pack,
        "ctx-v1",
        "exp-v1",
        target,
    )


def test_canonical_hash_stable_under_roundtrip_and_mapping_order() -> None:
    request = _request()
    assert canonical_sha256(request) == canonical_sha256(canonical_roundtrip(request))
    assert canonical_sha256({"b": 2, "a": 1}) == canonical_sha256({"a": 1, "b": 2})


def test_hash_changes_on_snapshot_model_checkpoint_and_config_mutation() -> None:
    request = _request()
    base = canonical_sha256(request)
    assert canonical_sha256(replace(request, snapshot_hash="other")) != base
    assert canonical_sha256(replace(request, experiment_config_id="exp-v2")) != base
    assert canonical_sha256(
        replace(request, model_target=replace(request.model_target, requested_model_id="model-z"))
    ) != base
    assert canonical_sha256(
        replace(
            request,
            model_target=replace(request.model_target, requested_checkpoint_or_revision="rev-z"),
        )
    ) != base
