from datetime import timedelta

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts import EnvironmentV0, EvidenceBundleManifestV0, EvidenceFileV0, RawEventV0


def test_raw_event_rejects_invalid_hash(now):
    with pytest.raises(ValidationError):
        RawEventV0(schema_version="0.1.0", source_event_id="event-001", source_id="hyperliquid", connection_id="conn-001", endpoint="ws", subscription="trades:ETH", environment=EnvironmentV0.READ_ONLY, collector_version="collector.0.1", collector_receive_time=now, receive_sequence=1, payload_sha256="BAD", payload_size_bytes=10, payload_encoding="json", payload_ref="s3://bucket/key")


def test_evidence_paths_cannot_traverse(now, h):
    with pytest.raises(ValidationError):
        EvidenceFileV0(relative_path="../secret", sha256=h, size_bytes=1)


def test_bundle_rejects_duplicate_paths(now, h):
    item = EvidenceFileV0(relative_path="gold/events.parquet", sha256=h, size_bytes=1)
    with pytest.raises(ValidationError, match="unique"):
        EvidenceBundleManifestV0(bundle_schema_version="0.1.0", dataset_id="dataset-001", environment=EnvironmentV0.SHADOW, account_alias="account-redacted", instrument="ETH", start_time=now, end_time=now + timedelta(hours=1), source_versions={"hl": "v1"}, collector_versions={"hl": "v1"}, normalizer_version="v1", strategy_versions={"LQS-FR": "v1"}, parameter_versions={"LQS-FR": "v1"}, risk_policy_version="v1", model_versions={"explain": "none"}, prompt_versions={"explain": "none"}, code_commit_oid="46f53dba95b0f5e83d73f406d752754bad939539", quality_status="PASS", known_gaps=(), files=(item, item), created_at=now)
