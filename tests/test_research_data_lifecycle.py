"""Two lifecycle axes and usage eligibility cannot be conflated."""

import pytest
from test_research_data_contracts import dataset, rights

from trader_assist_v0.research_data.contracts import DatasetManifest


@pytest.mark.parametrize("tier", ["R0", "R1", "R2", "R3", "R4", "R5", "R6"])
def test_source_tier_does_not_grant_exposure_or_performance_use(tier):
    value = dataset(source_tier=tier)
    value.require_access("PIPELINE_CORRECTNESS_ONLY")
    with pytest.raises(PermissionError):
        value.require_access("STRATEGY_PERFORMANCE")
    with pytest.raises(PermissionError):
        dataset(source_tier=tier, exposure_state="UNSEEN_SEALED").require_access(
            "PIPELINE_CORRECTNESS_ONLY"
        )


@pytest.mark.parametrize(
    "state",
    [
        "UNSEEN_SEALED",
        "DEV_EXPOSED",
        "VALIDATION_SEALED",
        "VALIDATION_USED",
        "FINAL_LOCKBOX_SEALED",
        "FINAL_LOCKBOX_USED",
        "RETIRED",
    ],
)
def test_no_unauthorized_lifecycle_open_or_transition(state):
    value = dataset(exposure_state=state)
    with pytest.raises(PermissionError):
        value.require_access("PIPELINE_CORRECTNESS_ONLY")
    assert not hasattr(value, "transition")
    with pytest.raises(ValueError):
        value.exposure_state = "SACRIFICIAL"


def test_required_lifecycle_metadata_and_immutable_role_specific_rights():
    value = dataset()
    for metadata in (value.metadata[:-1], (*value.metadata, value.metadata[0])):
        with pytest.raises(ValueError):
            dataset(metadata=metadata)
    with pytest.raises(PermissionError):
        dataset(rights=rights(eligibility="UNKNOWN")).require_access("PIPELINE_CORRECTNESS_ONLY")
    forged = value.model_dump(mode="json")
    forged["exposure_state"] = "UNSEEN_SEALED"
    with pytest.raises(ValueError):
        DatasetManifest.model_validate(forged)
    assert rights(eligibility="ALLOWED").record_hash != rights(eligibility="PROHIBITED").record_hash
