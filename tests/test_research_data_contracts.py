"""Synthetic contract factories; these are never production mapping evidence."""

import pytest

from trader_assist_v0.research_data.contracts import (
    REQUIRED_DATASET_METADATA,
    DatasetManifest,
    SourceRightsProvenance,
    TimestampProvenance,
)

H = "a" * 64


def rights(**updates):
    values = dict(
        version="synthetic-v1",
        terms_locator="synthetic://terms",
        observed_version="v1",
        observed_date="2026-10-04",
        terms_hash=H,
        intended_use="PIPELINE_CORRECTNESS_ONLY",
        eligibility="ALLOWED",
        decision_locator="synthetic://decision",
        attribution_constraints=(),
        retention_constraints=(),
        synthetic=True,
    )
    values.update(updates)
    return SourceRightsProvenance.create(**values)


def dataset(**updates):
    values = dict(
        version="synthetic-v1",
        dataset_id="toy",
        source="OKX",
        source_tier="R0",
        exposure_state="SACRIFICIAL",
        venue="OKX",
        asset_class="CRYPTO",
        instruments=("ETH-USDT-SWAP",),
        start_ns=1,
        end_ns=10**18,
        resolution="SNAPSHOT",
        datatypes=("OI",),
        timezone="UTC",
        session_semantics="24x7",
        checksum=H,
        source_locator="synthetic://response",
        mapping_hash=H,
        metadata=tuple((k, "UNKNOWN_SYNTHETIC") for k in sorted(REQUIRED_DATASET_METADATA)),
        rights=rights(),
    )
    values.update(updates)
    return DatasetManifest.create(**values)


def test_manifest_roundtrip_and_tamper():
    value = dataset()
    assert DatasetManifest.model_validate_json(value.model_dump_json()) == value
    raw = value.model_dump(mode="json")
    raw["dataset_id"] = "tamper"
    with pytest.raises(ValueError, match="hash"):
        DatasetManifest.model_validate(raw)


def test_receive_not_fabricated_and_conversion_bound():
    args = dict(
        source_ts="100",
        source_unit="ms",
        ts_event=100_000_000,
        observed_at_ns=200_000_000,
        receive_provenance="NOT_EXPOSED",
    )
    assert TimestampProvenance(**args).true_network_receive_ts is None
    with pytest.raises(ValueError):
        TimestampProvenance(**{**args, "ts_event": 100})
