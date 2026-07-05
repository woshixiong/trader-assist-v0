import json
from pathlib import Path

from trader_assist_v0.contracts import SeedProvenanceEntryV0


def test_no_historical_runtime_files_imported():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads(
        (root / "archive/manifests/seed_provenance.json").read_text(encoding="utf-8")
    )
    assert manifest["imported_files"] == []
    assert manifest["reviewed_entries"]
    for item in manifest["reviewed_entries"]:
        entry = SeedProvenanceEntryV0.model_validate(item)
        assert entry.target_paths == ()
