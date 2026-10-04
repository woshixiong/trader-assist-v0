"""Synthetic metadata only; acceptance proof never opens a dataset locator."""

import builtins
import hashlib
import io
import json
import os
import socket
import subprocess
import urllib.request
from pathlib import Path

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.research_data.contracts import (
    REQUIRED_DATASET_METADATA,
    DatasetManifest,
    SourceRightsProvenance,
)
from trader_assist_v0.research_inventory import (
    AllocationItem,
    CountState,
    CutIdentity,
    DatasetBinding,
    InventoryAllocationSpec,
    InventoryCountKind,
    InventoryRole,
    InventoryState,
    NonOutcomeInventoryFact,
    build_inventory_manifest,
    inventory_manifest_bytes,
    inventory_manifest_from_bytes,
    validate_inventory_manifest,
)

H = "a" * 64
BASE = "6b8b6dae0850237166de0e1c28b1baa6773850b8"
ALLOWED = {
    "src/trader_assist_v0/research_inventory/__init__.py",
    "src/trader_assist_v0/research_inventory/contracts.py",
    "src/trader_assist_v0/research_inventory/builder.py",
    "tests/test_research_inventory_manifest.py",
    "docs/research/DEV_DATASET_INVENTORY_RESERVE_MANIFEST_V1.md",
}
R2_PATHS = {
    *(f"src/trader_assist_v0/research_replay/{n}.py" for n in (
        "contracts", "evidence", "harness", "__init__", "dev_contracts", "dev_evidence",
        "dev_lifecycle", "dev_reporting", "dev_harness", "alignment", "paths", "microstructure",
        "profiles",
    )),
    "src/trader_assist_v0/research_data/admission.py",
    "src/trader_assist_v0/research_data/storage.py",
    "tests/test_research_data_contracts.py",
    *(f"tests/test_research_replay_{n}.py" for n in (
        "contracts", "lifecycle", "harness", "paths", "dev_access", "dev_evidence",
        "dev_lifecycle", "dev_reporting", "dev_harness",
    )),
    "docs/research/CAUSAL_RESEARCH_REPLAY_FOUNDATION_V1.md",
}


def install_no_io(patch, calls):
    def forbidden(*args, **kwargs):
        calls.append("I/O")
        raise AssertionError("inventory performed I/O")

    for owner, names in (
        (builtins, ("open",)), (io, ("open",)),
        (os, ("open", "stat", "lstat", "listdir", "scandir", "read")),
        (Path, ("open", "resolve", "stat", "lstat", "read_bytes", "read_text",
                "iterdir", "glob", "rglob")),
        (socket, ("socket", "create_connection")),
        (urllib.request, ("urlopen",)), (subprocess, ("Popen", "run")),
        (DatasetManifest, ("require_access",)),
    ):
        for name in names:
            patch.setattr(owner, name, forbidden)


@pytest.fixture(autouse=True)
def every_inventory_api_call_is_guarded(monkeypatch):
    # Fixtures/imports and repository observation stay outside the API interval.
    def guard(function):
        def guarded(*args, **kwargs):
            calls = []
            with pytest.MonkeyPatch.context() as patch:
                install_no_io(patch, calls)
                try:
                    return function(*args, **kwargs)
                finally:
                    assert calls == []
        return guarded

    for name in ("build_inventory_manifest", "validate_inventory_manifest",
                 "inventory_manifest_bytes", "inventory_manifest_from_bytes"):
        monkeypatch.setitem(globals(), name, guard(globals()[name]))


def rights(**updates):
    values = dict(
        version="synthetic-v1", terms_locator="synthetic://terms", observed_version="v1",
        observed_date="2026-10-05", terms_hash=H, intended_use="STRATEGY_DEV_RESEARCH",
        eligibility="ALLOWED", decision_locator="synthetic://decision",
        attribution_constraints=(), retention_constraints=(), synthetic=True,
    )
    values.update(updates)
    return SourceRightsProvenance.create(**values)


def dataset(dataset_id="dev", metadata_updates=None, **updates):
    metadata = dict.fromkeys(REQUIRED_DATASET_METADATA, "UNKNOWN_SYNTHETIC")
    metadata.update(strategy_version_allowed="strategy-v1", primary_research_question="question-v1",
                    current_evidence_role="DEV", permitted_output_visibility="DEV_ONLY")
    metadata.update(metadata_updates or {})
    values = dict(
        version="synthetic-v1", dataset_id=dataset_id, source="SYNTHETIC_PROVIDER",
        source_tier="R3", exposure_state="DEV_EXPOSED", venue="SYNTHETIC_VENUE",
        asset_class="CRYPTO", instruments=("SYNTHETIC-PERP",), start_ns=100, end_ns=200,
        resolution="1m", datatypes=("BAR",), timezone="UTC", session_semantics="24x7",
        checksum=H, source_locator="sentinel://sealed/outcomes/raw", mapping_hash=H,
        metadata=tuple(sorted(metadata.items())), rights=rights(),
    )
    values.update(updates)
    return DatasetManifest.create(**values)


def binding(d):
    metadata = dict(d.metadata)
    return DatasetBinding(
        dataset_id=d.dataset_id, dataset_manifest_hash=d.record_hash, checksum=d.checksum,
        cut=CutIdentity(**{name: getattr(d, name) for name in CutIdentity.model_fields}),
        source_tier=d.source_tier, exposure_state=d.exposure_state,
        current_evidence_role=metadata["current_evidence_role"],
        rights_hash=d.rights.record_hash if d.rights else None,
        rights_state="PRESENT" if d.rights else "MISSING",
        strategy_version=metadata["strategy_version_allowed"],
        primary_research_question=metadata["primary_research_question"],
    )


def item(d, role=InventoryRole.CURRENT_DEV, **updates):
    values = dict(
        binding=binding(d), role=role, block_id="block-1", intended_use="STRATEGY_DEV_RESEARCH",
        inventory_state=InventoryState.AVAILABLE, reason="synthetic caller-frozen allocation",
    )
    values.update(updates)
    return AllocationItem(**values)


def spec(*items, **updates):
    values = dict(
        spec_id="allocation-v1", freeze_evidence_locator="synthetic://freeze",
        freeze_evidence_hash=H, strategy_version="strategy-v1",
        primary_research_question="question-v1", items=items,
    )
    values.update(updates)
    return InventoryAllocationSpec.create(**values)


def fact(d, **updates):
    values = dict(
        kind=InventoryCountKind.INDEPENDENT_EVENT, state=CountState.KNOWN, value=10,
        binding=binding(d), method_version="synthetic-inventory-v1",
        evidence_locator="synthetic://non-outcome-count", evidence_hash=H,
    )
    values.update(updates)
    return NonOutcomeInventoryFact(**values)


def build(d=None, **updates):
    d = d or dataset()
    return build_inventory_manifest(datasets=(d,), allocation=spec(item(d)), **updates)


def rehash_wire(raw):
    raw["record_hash"] = hashlib.sha256(
        b"DatasetInventoryManifest\0" + canonical_json_bytes(
            {k: v for k, v in raw.items() if k != "record_hash"},
        ),
    ).hexdigest()
    return canonical_json_bytes(raw)


def test_deterministic_normalization_roundtrip_and_two_hash_reference():
    a, b = dataset(), dataset("reserve", start_ns=200, end_ns=300)
    ia, ib = item(a), item(b, InventoryRole.FUTURE_DEV_RESERVE, block_id="future")
    fa, fb = fact(a), fact(b, kind=InventoryCountKind.CORRELATION_CLUSTER)
    left = build_inventory_manifest(datasets=(a, b), allocation=spec(ia, ib), facts=(fa, fb))
    right = build_inventory_manifest(datasets=(b, a), allocation=spec(ib, ia), facts=(fb, fa))
    wire = inventory_manifest_bytes(left)
    assert wire == inventory_manifest_bytes(right)
    assert wire == inventory_manifest_bytes(inventory_manifest_from_bytes(wire))
    assert left.record_hash == right.record_hash
    assert left.allocation_spec.record_hash == right.allocation_spec.record_hash
    assert left.entries[0].dataset == a
    assert left.sufficiency_assessment == "NOT_ASSESSED"
    ref = {"inventory_manifest_hash": left.record_hash,
           "allocation_spec_hash": left.allocation_spec.record_hash}
    assert ref["inventory_manifest_hash"] == inventory_manifest_from_bytes(wire).record_hash
    assert ref["allocation_spec_hash"] == left.allocation_spec.record_hash
    changed = build_inventory_manifest(datasets=(a, b), allocation=spec(ia, ib, spec_id="v2"))
    assert changed.record_hash != ref["inventory_manifest_hash"]
    assert changed.allocation_spec.record_hash != ref["allocation_spec_hash"]
    raw = left.model_dump(mode="json", exclude={"record_hash"})
    assert left.record_hash == hashlib.sha256(
        b"DatasetInventoryManifest\0" + canonical_json_bytes(raw),
    ).hexdigest()
    raw = left.allocation_spec.model_dump(mode="json", exclude={"record_hash"})
    assert left.allocation_spec.record_hash == hashlib.sha256(
        b"InventoryAllocationSpec\0" + canonical_json_bytes(raw),
    ).hexdigest()
    with pytest.raises(ValidationError):
        left.sufficiency_assessment = "SUFFICIENT"


def test_zero_io_success_and_rejection(monkeypatch):
    dev = dataset()
    validation = dataset("validation", exposure_state="VALIDATION_SEALED", start_ns=200, end_ns=300)
    lockbox = dataset("lockbox", exposure_state="FINAL_LOCKBOX_SEALED", start_ns=300, end_ns=400)
    allocation = spec(item(dev), item(validation, InventoryRole.SEALED_VALIDATION),
                      item(lockbox, InventoryRole.FINAL_LOCKBOX))
    bad = spec(item(validation))
    tampered = dev.model_copy(update={"checksum": "b" * 64})
    calls = []

    with monkeypatch.context() as patch:
        install_no_io(patch, calls)
        value = build_inventory_manifest(datasets=(dev, validation, lockbox), allocation=allocation)
        wire = inventory_manifest_bytes(value)
        assert validate_inventory_manifest(inventory_manifest_from_bytes(wire)) == value
        for datasets, allocation_value in (((validation,), bad), ((tampered,), spec(item(dev)))):
            with pytest.raises((ValueError, PermissionError)):
                build_inventory_manifest(datasets=datasets, allocation=allocation_value)
        with pytest.raises(ValueError):
            inventory_manifest_from_bytes(wire.replace(b'"NOT_ASSESSED"', b'"SUFFICIENT"'))
    assert calls == []
    assert dev.exposure_state == "DEV_EXPOSED"
    assert validation.exposure_state == "VALIDATION_SEALED"
    assert lockbox.exposure_state == "FINAL_LOCKBOX_SEALED"


@pytest.mark.parametrize("field,value", [
    ("dataset_id", "different"), ("dataset_manifest_hash", "b" * 64),
    ("checksum", "b" * 64), ("rights_hash", "b" * 64),
    ("source_tier", "R4"), ("exposure_state", "UNSEEN_SEALED"),
    ("current_evidence_role", "CERTIFICATION"), ("strategy_version", "other-version"),
    ("primary_research_question", "other-question"),
])
def test_exact_binding_mismatches(field, value):
    d = dataset()
    row = item(d).model_copy(update={"binding": binding(d).model_copy(update={field: value})})
    with pytest.raises(ValueError):
        build_inventory_manifest(datasets=(d,), allocation=spec(row))


@pytest.mark.parametrize("field,value", [
    ("source", "OTHER"), ("venue", "OTHER"), ("asset_class", "OTHER"),
    ("instruments", ("OTHER",)), ("start_ns", 101), ("end_ns", 201),
    ("resolution", "5m"), ("datatypes", ("TRADE",)), ("timezone", "OTHER"),
    ("session_semantics", "OTHER"), ("mapping_hash", "b" * 64),
])
def test_exact_cut_mismatches(field, value):
    d = dataset()
    changed = binding(d).model_copy(update={
        "cut": binding(d).cut.model_copy(update={field: value}),
    })
    with pytest.raises(ValueError):
        build_inventory_manifest(datasets=(d,), allocation=spec(item(d, binding=changed)))


@pytest.mark.parametrize("exposure", [
    "UNSEEN_SEALED", "SACRIFICIAL", "DEV_EXPOSED", "VALIDATION_SEALED", "VALIDATION_USED",
    "FINAL_LOCKBOX_SEALED", "FINAL_LOCKBOX_USED", "CONTAMINATED", "RETIRED",
])
def test_current_dev_exposure_matrix(exposure):
    d = dataset(exposure_state=exposure)
    if exposure == "DEV_EXPOSED":
        assert build(d).entries[0].dataset.exposure_state == exposure
    else:
        with pytest.raises(ValueError):
            build(d)
    excluded = build_inventory_manifest(
        datasets=(d,), allocation=spec(item(d, InventoryRole.METADATA_ONLY_EXCLUDED)),
    )
    assert excluded.entries[0].dataset.exposure_state == exposure


@pytest.mark.parametrize("role,exposure", [
    (InventoryRole.FUTURE_DEV_RESERVE, "DEV_EXPOSED"),
    (InventoryRole.FUTURE_DEV_RESERVE, "UNSEEN_SEALED"),
    (InventoryRole.CERTIFICATION_RESERVE, "UNSEEN_SEALED"),
    (InventoryRole.CERTIFICATION_RESERVE, "VALIDATION_SEALED"),
    (InventoryRole.SEALED_VALIDATION, "VALIDATION_SEALED"),
    (InventoryRole.FINAL_LOCKBOX, "FINAL_LOCKBOX_SEALED"),
])
def test_reserved_metadata_identity(role, exposure):
    d = dataset(exposure_state=exposure)
    out = build_inventory_manifest(datasets=(d,), allocation=spec(item(d, role)))
    assert out.entries[0].dataset == d


@pytest.mark.parametrize("role", [InventoryRole.FUTURE_DEV_RESERVE,
                                 InventoryRole.CERTIFICATION_RESERVE, InventoryRole.FINAL_LOCKBOX])
def test_contaminated_cannot_regain_reserve_credit(role):
    d = dataset(exposure_state="CONTAMINATED")
    with pytest.raises(ValueError):
        build_inventory_manifest(datasets=(d,), allocation=spec(item(d, role)))


@pytest.mark.parametrize("tier", ["R0", "R6"])
def test_infrastructure_and_forward_not_current_dev(tier):
    with pytest.raises(ValueError):
        build(dataset(source_tier=tier))


@pytest.mark.parametrize("value", [None, rights(eligibility="UNKNOWN"),
                                 rights(eligibility="PROHIBITED")])
def test_wrong_rights_only_excluded(value):
    d = dataset(rights=value)
    for role in InventoryRole:
        if role == InventoryRole.METADATA_ONLY_EXCLUDED:
            out = build_inventory_manifest(datasets=(d,), allocation=spec(item(d, role)))
            assert out.entries[0].dataset.rights == value
        else:
            with pytest.raises((ValueError, PermissionError)):
                build_inventory_manifest(datasets=(d,), allocation=spec(item(d, role)))


def test_intended_use_constraints_and_strategy_question():
    d = dataset(rights=rights(intended_use="PIPELINE_CORRECTNESS_ONLY"))
    with pytest.raises(PermissionError):
        build(d)
    d = dataset(rights=rights(attribution_constraints=("ATTR",), retention_constraints=("RET",)))
    with pytest.raises(PermissionError):
        build(d)
    out = build_inventory_manifest(datasets=(d,), allocation=spec(
        item(d, satisfied_constraints=("RET", "ATTR")),
    ))
    assert out.entries[0].allocation.satisfied_constraints == ("ATTR", "RET")
    for change in ({"strategy_version": "wrong"}, {"primary_research_question": "wrong"}):
        with pytest.raises(ValueError):
            build_inventory_manifest(
                datasets=(dataset(),), allocation=spec(item(dataset()), **change),
            )


@pytest.mark.parametrize("role", [InventoryRole.FUTURE_DEV_RESERVE,
                                 InventoryRole.CERTIFICATION_RESERVE,
                                 InventoryRole.SEALED_VALIDATION, InventoryRole.FINAL_LOCKBOX])
def test_reserve_overlap_even_with_other_datatype_resolution(role):
    a = dataset()
    exposure = {InventoryRole.FUTURE_DEV_RESERVE: "UNSEEN_SEALED",
                InventoryRole.CERTIFICATION_RESERVE: "UNSEEN_SEALED",
                InventoryRole.SEALED_VALIDATION: "VALIDATION_SEALED",
                InventoryRole.FINAL_LOCKBOX: "FINAL_LOCKBOX_SEALED"}[role]
    b = dataset("reserve", start_ns=150, end_ns=250, datatypes=("TRADE",),
                resolution="TICK", exposure_state=exposure)
    with pytest.raises(ValueError, match="overlapping"):
        build_inventory_manifest(datasets=(a, b), allocation=spec(item(a), item(b, role)))


def test_cut_adjacency_disjoint_instrument_and_compatible_complement():
    a = dataset()
    for b in (dataset("adjacent", start_ns=200, end_ns=300),
              dataset("other", instruments=("OTHER-PERP",)),
              dataset("complement", datatypes=("TRADE",), resolution="TICK")):
        out = build_inventory_manifest(datasets=(a, b), allocation=spec(item(a), item(b)))
        assert len(out.entries) == 2
        assert out.sufficiency_assessment == "NOT_ASSESSED"
    b = dataset("block-2", datatypes=("TRADE",))
    with pytest.raises(ValueError, match="overlapping"):
        build_inventory_manifest(
            datasets=(a, b), allocation=spec(item(a), item(b, block_id="block-2")),
        )
    for instruments in (("UNKNOWN",), ("SYNTHETIC-PERP",)):
        b = dataset("unknown-venue", venue="UNKNOWN", instruments=instruments,
                    exposure_state="UNSEEN_SEALED")
        with pytest.raises(ValueError, match="overlapping"):
            build_inventory_manifest(datasets=(a, b), allocation=spec(
                item(a), item(b, InventoryRole.FUTURE_DEV_RESERVE),
            ))


def test_duplicate_dataset_allocation_and_coverage():
    a, b = dataset(), dataset("other", start_ns=200, end_ns=300)
    cases = (((a, a), spec(item(a))), ((a,), spec(item(a), item(a))),
             ((a, b), spec(item(a))), ((a,), spec(item(a), item(b))))
    for rows, allocation in cases:
        with pytest.raises(ValueError):
            build_inventory_manifest(datasets=rows, allocation=allocation)
    with pytest.raises(TypeError):
        build_inventory_manifest(datasets=[a], allocation=spec(item(a)))


def test_nested_duplicates_and_unknown_states_are_not_normalized_away():
    for updates in ({"instruments": ("SYNTHETIC-PERP", "SYNTHETIC-PERP")},
                    {"datatypes": ("BAR", "BAR")}):
        d = dataset(**updates)
        with pytest.raises(ValueError, match="duplicate"):
            build_inventory_manifest(datasets=(d,), allocation=spec(item(dataset())))
    d = dataset()
    for updates in ({"satisfied_constraints": ("ATTR", "ATTR")},
                    {"limitations": ("UNKNOWN", "UNKNOWN")},
                    {"inventory_state": InventoryState.INCOMPLETE}):
        with pytest.raises(ValueError):
            build_inventory_manifest(datasets=(d,), allocation=spec(item(d, **updates)))
    out = build_inventory_manifest(datasets=(d,), allocation=spec(item(
        d, inventory_state=InventoryState.INCOMPLETE, limitations=("missing inventory cells",),
    )))
    assert out.entries[0].inventory_state == InventoryState.INCOMPLETE
    assert out.sufficiency_assessment == "NOT_ASSESSED"


def test_immutable_upstream_wire_identity_and_normalized_limitations():
    d = dataset()
    before = d.model_dump_json()
    one = item(d, limitations=("B", "A"))
    two = item(d, limitations=("A", "B"))
    out = build_inventory_manifest(datasets=(d,), allocation=spec(one))
    twin = build_inventory_manifest(datasets=(d,), allocation=spec(two))
    assert inventory_manifest_bytes(out) == inventory_manifest_bytes(twin)
    assert d.model_dump_json() == before
    assert out.entries[0].dataset.model_dump_json() == before
    assert one.limitations == ("B", "A")
    with pytest.raises(ValidationError):
        out.entries[0].dataset.exposure_state = "UNSEEN_SEALED"


@pytest.mark.parametrize("change", [
    {"value": 11}, {"evidence_hash": "b" * 64}, {"method_version": "inventory-v2"},
])
def test_valid_fact_change_changes_manifest_fingerprint(change):
    d = dataset()
    before = build(d, facts=(fact(d),))
    after = build(d, facts=(fact(d, **change),))
    assert before.record_hash != after.record_hash
    assert before.allocation_spec.record_hash == after.allocation_spec.record_hash


@pytest.mark.parametrize("state", [CountState.UNKNOWN, CountState.REQUIRES_SEPARATE_INVENTORY])
def test_unknown_counts_never_sufficient(state):
    d = dataset()
    f = fact(d, state=state, value=None)
    for facts in ((), (f,), (fact(d, value=0),)):
        out = build(d, facts=facts)
        assert out.sufficiency_assessment == "NOT_ASSESSED"
        assert inventory_manifest_from_bytes(inventory_manifest_bytes(out)) == out
    with pytest.raises(ValidationError):
        fact(d, state=state, value=0)


@pytest.mark.parametrize("value", [-1, True, 1.0, "10", None])
def test_invalid_known_count(value):
    with pytest.raises(ValidationError):
        fact(dataset(), value=value)


def test_fact_provenance_orphan_duplicate_cell_and_outcome_fields():
    d = dataset()
    f = fact(d, kind=InventoryCountKind.REQUIRED_CELL, cell_id="SETUP/REGIME")
    with pytest.raises(ValueError, match="duplicate"):
        build(d, facts=(f, f))
    with pytest.raises(ValueError, match="orphan"):
        build(d, facts=(fact(dataset("orphan")),))
    for field in ("method_version", "evidence_locator"):
        with pytest.raises(ValueError, match="provenance"):
            build(d, facts=(fact(d, **{field: "UNKNOWN"}),))
    for extra in ({"pnl": 10}, {"mfe": 2}, {"mae": 1}, {"candidate_performance": 100},
                  {"evidence_type": "OUTCOME"}):
        with pytest.raises(ValidationError):
            fact(d, **extra)
    with pytest.raises(ValidationError):
        fact(d, kind=InventoryCountKind.REQUIRED_CELL)


@pytest.mark.parametrize("state", [InventoryState.MISSING, InventoryState.UNAVAILABLE,
                                 InventoryState.UNKNOWN])
def test_missing_unknown_inventory_is_metadata_only(state):
    d = dataset()
    row = item(d, inventory_state=state, limitations=("UNKNOWN supplied metadata",))
    with pytest.raises(ValueError):
        build_inventory_manifest(datasets=(d,), allocation=spec(row))
    row = row.model_copy(update={"role": InventoryRole.METADATA_ONLY_EXCLUDED})
    out = build_inventory_manifest(datasets=(d,), allocation=spec(row))
    assert out.entries[0].inventory_state == state
    assert out.sufficiency_assessment == "NOT_ASSESSED"


@pytest.mark.parametrize("key", ["strategy_version_allowed", "primary_research_question",
                               "current_evidence_role"])
def test_unknown_critical_metadata(key):
    d = dataset(metadata_updates={key: "UNKNOWN"})
    with pytest.raises(ValueError, match="unknown"):
        build(d)


def test_missing_metadata_and_forged_concrete_models():
    d = dataset()
    for forged in (
        d.model_copy(update={"metadata": d.metadata[:-1]}),
        d.model_copy(update={"exposure_state": "UNSEEN_SEALED"}),
        d.model_copy(update={"checksum": "b" * 64}),
        d.model_copy(update={"start_ns": True}),
        d.model_copy(update={"pnl": 100}),
        DatasetManifest.model_construct(**{**d.model_dump(), "record_hash": ""}),
    ):
        with pytest.raises((ValueError, TypeError)):
            build_inventory_manifest(datasets=(forged,), allocation=spec(item(d)))

    class ForgedDataset(DatasetManifest):
        pass

    forged = ForgedDataset.create(**d.model_dump(exclude={"record_hash"}))
    with pytest.raises(TypeError, match="concrete"):
        build(forged)
    forged_rights = d.rights.model_copy(update={"intended_use": "other"})
    with pytest.raises(ValueError):
        build(d.model_copy(update={"rights": forged_rights}))


@pytest.mark.parametrize("field", list(DatasetManifest.model_fields))
def test_every_dataset_wire_field_tamper_rejected(field):
    raw = build().model_dump(mode="json")
    value = raw["entries"][0]["dataset"][field]
    raw["entries"][0]["dataset"][field] = "TAMPER" if isinstance(value, str) else None
    with pytest.raises(ValueError):
        inventory_manifest_from_bytes(rehash_wire(raw))


@pytest.mark.parametrize("field", list(AllocationItem.model_fields))
def test_every_allocation_wire_field_tamper_rejected(field):
    raw = build().model_dump(mode="json")
    raw["allocation_spec"]["items"][0][field] = "TAMPER"
    with pytest.raises(ValueError):
        inventory_manifest_from_bytes(rehash_wire(raw))


@pytest.mark.parametrize("field", list(NonOutcomeInventoryFact.model_fields))
def test_every_fact_wire_field_tamper_rejected(field):
    d = dataset()
    raw = build(d, facts=(fact(d),)).model_dump(mode="json")
    raw["entries"][0]["facts"][0][field] = "TAMPER"
    with pytest.raises(ValueError):
        inventory_manifest_from_bytes(canonical_json_bytes(raw))


def test_semantically_invalid_rehashed_manifest_and_noncanonical_order():
    value = build()
    raw = value.model_dump(mode="json")
    raw["entries"][0]["inventory_state"] = "UNKNOWN"
    with pytest.raises(ValueError, match="inconsistent"):
        inventory_manifest_from_bytes(rehash_wire(raw))
    a, b = dataset(), dataset("other", start_ns=200, end_ns=300)
    value = build_inventory_manifest(datasets=(a, b), allocation=spec(item(a), item(b)))
    raw = value.model_dump(mode="json")
    raw["entries"].reverse()
    with pytest.raises(ValueError, match="noncanonical"):
        inventory_manifest_from_bytes(rehash_wire(raw))


def test_duplicate_json_extra_version_hash_and_nonfinite_rejected():
    wire = inventory_manifest_bytes(build())
    for payload in (
        wire.replace(b'{', b'{"record_hash":"fake",', 1),
        wire.replace(b'"R2B_INVENTORY_V1"', b'"R2B_INVENTORY_V2"'),
        wire.replace(b'{', b'{"pnl":10,', 1),
        wire.replace(b'{', b'{"pnl":NaN,', 1),
        wire.replace(b'"NOT_ASSESSED"', b'"SUFFICIENT"'),
    ):
        with pytest.raises(ValueError):
            inventory_manifest_from_bytes(payload)
    raw = json.loads(wire)
    raw.pop("record_hash")
    with pytest.raises(ValueError):
        inventory_manifest_from_bytes(canonical_json_bytes(raw))


def test_builder_imports_do_not_duplicate_r2_or_io_owners():
    import ast

    root = Path(__file__).resolve().parents[1]
    for path in (root / "src/trader_assist_v0/research_inventory").glob("*.py"):
        tree = ast.parse(path.read_text())
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
                    for alias in node.names]
        assert not any(name and ("research_replay" in name or name.split(".")[0] in {
            "os", "pathlib", "socket", "subprocess", "urllib", "io",
        }) for name in imports)


def test_exact_changed_path_allowlist():
    root = Path(__file__).resolve().parents[1]

    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args], check=True,
                              capture_output=True).stdout

    tracked = set(filter(None, git("diff", "--name-only", BASE, "--").decode().splitlines()))
    untracked = set(filter(None, git(
        "ls-files", "--others", "--exclude-standard",
    ).decode().splitlines()))
    assert tracked | untracked == ALLOWED
    base_paths = set(git("ls-tree", "-r", "--name-only", BASE).decode().splitlines())
    assert not ALLOWED & base_paths
    assert len(R2_PATHS) == 26
    assert not (tracked | untracked) & R2_PATHS
    assert all((root / name).is_file() for name in ALLOWED)
    assert not git("diff", "--diff-filter=DMRT", "--name-only", BASE, "--").strip()
