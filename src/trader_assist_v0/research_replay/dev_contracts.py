"""Sibling DEV identities. These records grant no production or sealed access."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Self

from pydantic import Field, model_validator

from trader_assist_v0.contracts.common import GitCommitOid, Sha256Hex
from trader_assist_v0.research_data.contracts import BoundRecord, DatasetManifest

from .contracts import CostModel, _ObservationFields

if TYPE_CHECKING:
    from .dev_lifecycle import DevPreregistration


class DevAccessAuthority(BoundRecord):
    use: Literal["STRATEGY_DEV_RESEARCH"] = "STRATEGY_DEV_RESEARCH"
    dataset_hash: Sha256Hex
    dataset_id: str = Field(min_length=1)
    cut: tuple[int, int]
    instruments: tuple[str, ...] = Field(min_length=1)
    checksum: Sha256Hex
    mapping_hash: Sha256Hex
    rights_hash: Sha256Hex
    strategy_version: str = Field(min_length=1)
    strategy_hash: Sha256Hex
    question: str = Field(min_length=1)
    role: Literal["DEV"] = "DEV"
    visibility: Literal["DEV_LOCAL_AND_AGGREGATE", "DEV_AGGREGATE_ONLY"]
    preregistration_hash: Sha256Hex
    run_authority_ref: str = Field(min_length=1)
    satisfied_constraints: tuple[str, ...]

    def require(
        self, dataset: DatasetManifest, preregistration: DevPreregistration
    ) -> DatasetManifest:
        from .dev_lifecycle import DevPreregistration

        if type(self) is not DevAccessAuthority or type(dataset) is not DatasetManifest:
            raise TypeError("concrete DEV authority and manifest required")
        if type(preregistration) is not DevPreregistration:
            raise TypeError("concrete DEV preregistration required")
        a = DevAccessAuthority.model_validate_json(self.model_dump_json())
        ds = DatasetManifest.model_validate_json(dataset.model_dump_json())
        pre = DevPreregistration.model_validate_json(preregistration.model_dump_json())
        if ds.exposure_state != "DEV_EXPOSED":
            raise PermissionError("DEV_EXPOSED only; sealed/S0/retired access prohibited")
        metadata = dict(ds.metadata)
        if ds.source_tier == "R6" or any(
            "FORWARD" in metadata[k].upper()
            for k in ("current_evidence_role", "open_reason", "result_visibility_state")
        ):
            raise PermissionError("Forward/R6 reclassification is outside this package")
        if ds.rights is None:
            raise PermissionError("DEV rights UNKNOWN")
        ds.rights.require_allowed(a.use, frozenset(a.satisfied_constraints))
        if (
            a.dataset_hash != ds.record_hash
            or a.dataset_id != ds.dataset_id
            or a.cut != (ds.start_ns, ds.end_ns)
            or a.instruments != ds.instruments
            or a.checksum != ds.checksum
            or a.mapping_hash != ds.mapping_hash
            or a.rights_hash != ds.rights.record_hash
        ):
            raise PermissionError("DEV dataset/rights/cut binding mismatch")
        expected = {
            "strategy_version_allowed": a.strategy_version,
            "primary_research_question": a.question,
            "current_evidence_role": a.role,
            "permitted_output_visibility": a.visibility,
            "result_visibility_state": "DEV",
        }
        if any(
            metadata[k] != v
            or v.strip().upper().startswith(("UNKNOWN", "N/A", "NOT_APPLICABLE"))
            or "*" in v
            for k, v in expected.items()
        ):
            raise PermissionError("DEV Strategy/question/role/visibility mismatch")
        if (
            a.preregistration_hash != pre.record_hash
            or a.run_authority_ref != pre.run_authority_ref
            or a.strategy_hash != pre.strategy_hash
            or a.strategy_version != pre.strategy_version
            or a.question != pre.question
            or ds.record_hash not in pre.dataset_hashes
            or ds.record_hash in pre.reserve_hashes
        ):
            raise PermissionError("DEV frozen run authority/preregistration mismatch")
        if ds.source_tier == "R0" and pre.evidence_kind != "SYNTHETIC_ENGINEERING":
            raise PermissionError("R0 cannot establish performance evidence")
        if ds.rights.synthetic != (pre.evidence_kind == "SYNTHETIC_ENGINEERING"):
            raise PermissionError("synthetic and real run authority cannot be mixed")
        return ds


class DevObservation(_ObservationFields):
    authority: DevAccessAuthority

    @model_validator(mode="after")
    def dev_binding(self) -> Self:
        a, ref = self.authority, self.evidence
        if ref.exposure_state != "DEV_EXPOSED" or ref.source_tier == "R6":
            raise PermissionError("DEV observation exposure forbidden")
        if (
            ref.dataset_hash != a.dataset_hash
            or ref.rights_hash != a.rights_hash
            or ref.instrument not in a.instruments
            or not a.cut[0] <= self.ts_event < a.cut[1]
            or (ref.coverage_start, ref.coverage_end) != a.cut
        ):
            raise ValueError("DEV observation authority mismatch")
        return self


class DevRunSpec(BoundRecord):
    package: Literal["R2_DEV_RESEARCH_EXECUTION_ENABLEMENT_1"]
    base: GitCommitOid
    release: GitCommitOid
    code_tree: GitCommitOid
    runtime: str = Field(min_length=1)
    strategy_hash: Sha256Hex
    strategy_version: str = Field(min_length=1)
    strategy_package_hash: Sha256Hex
    dataset_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)
    feature_hashes: tuple[Sha256Hex, ...]
    policy_hashes: tuple[Sha256Hex, ...] = Field(min_length=1, max_length=64)
    parameter_hashes: tuple[Sha256Hex, ...]
    roster_hash: Sha256Hex
    cost: CostModel
    horizon_ns: int = Field(gt=0)
    max_observations: int = Field(gt=0, le=100_000)
    max_candidates: int = Field(gt=0, le=64)
    trial_ledger_hash: Sha256Hex
    block_plan_hash: Sha256Hex
    visibility_hash: Sha256Hex
    preregistration_hash: Sha256Hex
    correlation_method: str = Field(min_length=1)
    seed: int
    claim: Literal["DEV_RESEARCH_ONLY"] = "DEV_RESEARCH_ONLY"
    ambiguity: Literal["CONSERVATIVE_STOP_FIRST"] = "CONSERVATIVE_STOP_FIRST"
    consumption: Literal["REPLAY"] = "REPLAY"
    promotion: Literal["PROHIBITED"] = "PROHIBITED"
    dependency_lock_hash: Sha256Hex
    config_hash: Sha256Hex
    python_version: str = Field(min_length=1)
    os: str = Field(min_length=1)
    architecture: str = Field(min_length=1)
    backtest_version: Literal["2.0.0rc5"]
    report_code_hash: Sha256Hex
    universe_hash: Sha256Hex
    registry_hash: Sha256Hex
    taxonomy_hash: Sha256Hex
    execution_hash: Sha256Hex
    funding_hash: Sha256Hex
    friction_hash: Sha256Hex


def dev_material_identity(run: DevRunSpec, candidate_hash: str) -> str:
    from .contracts import digest

    return digest(
        "DEV_MATERIAL_TRIAL_V1",
        (
            candidate_hash,
            run.strategy_hash,
            run.dataset_hashes,
            run.feature_hashes,
            run.parameter_hashes,
            run.roster_hash,
            run.cost.record_hash,
            run.horizon_ns,
            run.seed,
            run.block_plan_hash,
            run.visibility_hash,
            run.ambiguity,
            run.funding_hash,
            run.friction_hash,
            run.execution_hash,
        ),
    )


class DevEvidenceBundle(BoundRecord):
    """Authenticated local evidence envelope; canonical egress is a separate allowlist."""

    run: DevRunSpec
    preregistration: DevPreregistration
    ledger: DevTrialLedger
    datasets: tuple[DatasetManifest, ...]
    authorities: tuple[DevAccessAuthority, ...]
    roster: tuple[Opportunity, ...]
    original_risks: tuple[tuple[str, FiniteDecimal], ...]
    results: tuple[CandidateResult, ...]
    pairs: tuple[Pair, ...]
    counterfactuals: tuple[CounterfactualPathRef, ...]
    artifacts: tuple[tuple[str, Sha256Hex], ...]
    fingerprint: Sha256Hex
    claim: Literal["DEV_RESEARCH_ONLY"] = "DEV_RESEARCH_ONLY"
    promotion: Literal["PROHIBITED"] = "PROHIBITED"

    @model_validator(mode="after")
    def bound(self) -> Self:
        from .contracts import digest

        pre = self.preregistration
        if (
            self.run.strategy_hash != pre.strategy_hash
            or self.run.strategy_version != pre.strategy_version
            or self.run.cost.record_hash != pre.cost_hash
            or self.run.policy_hashes != pre.candidate_order
            or self.run.parameter_hashes != pre.parameter_hashes
            or self.run.horizon_ns > pre.max_horizon_ns
            or self.run.block_plan_hash != pre.block_plan_hash
            or self.run.visibility_hash != pre.visibility_hash
            or self.run.taxonomy_hash != pre.taxonomy_hash
            or self.ledger.history != "COMPLETE"
        ):
            raise ValueError("bundle changed frozen research assumptions")
        material = {e.semantic_hash for e in self.ledger.entries if type(e) is DevTrial}
        if not {dev_material_identity(self.run, c) for c in self.run.policy_hashes} <= material:
            raise ValueError("bundle contains unlogged material execution")
        if type(self.run) is not DevRunSpec:
            raise TypeError("concrete DEV run required")
        if tuple(a.dataset_hash for a in self.authorities) != self.run.dataset_hashes:
            raise ValueError("bundle access roster mismatch")
        if tuple(d.record_hash for d in self.datasets) != self.run.dataset_hashes:
            raise ValueError("bundle dataset roster mismatch")
        for ds, a in zip(self.datasets, self.authorities, strict=True):
            a.require(ds, self.preregistration)
        if (
            self.run.preregistration_hash != self.preregistration.record_hash
            or self.ledger.preregistration != self.preregistration
            or self.run.trial_ledger_hash != self.ledger.record_hash
            or self.run.dataset_hashes != self.preregistration.dataset_hashes
        ):
            raise ValueError("bundle preregistration/ledger binding mismatch")
        if (
            digest("DEV_ORIGINAL_THESIS_RISK_V1", self.original_risks)
            != self.preregistration.original_risk_hash
        ):
            raise ValueError("original Thesis risk denominator changed")
        if len(dict(self.original_risks)) != len(self.original_risks) or any(
            r <= 0 for _, r in self.original_risks
        ):
            raise ValueError("unique positive original Thesis risk required")
        if not {o.thesis_id for o in self.roster} <= dict(self.original_risks).keys():
            raise ValueError("original Thesis risk missing")
        if digest("B_ROSTER", tuple(o.record_hash for o in self.roster)) != self.run.roster_hash:
            raise ValueError("bundle opportunity roster mismatch")
        opportunities = {o.record_hash: o for o in self.roster}
        for result in self.results:
            op = opportunities.get(result.opportunity_hash)
            if op is None or (
                result.market_event_id,
                result.thesis_id,
                result.cluster_id,
                result.setup,
                result.regime,
                result.cost_hash,
            ) != (
                op.market_event_id,
                op.thesis_id,
                op.cluster_id,
                op.setup,
                op.regime,
                self.run.cost.record_hash,
            ):
                raise ValueError("result domain/cost lineage mismatch")
        expected = {(o.record_hash, c) for o in self.roster for c in self.run.policy_hashes}
        if {(r.opportunity_hash, r.candidate_hash) for r in self.results} != expected or len(
            self.results
        ) != len(expected):
            raise ValueError("incomplete/duplicate candidate denominator")
        from .reporting import pair

        result_by_key = {(r.opportunity_hash, r.candidate_hash): r for r in self.results}
        expected_pairs = tuple(
            pair(
                result_by_key[(op.record_hash, self.run.policy_hashes[0])],
                result_by_key[(op.record_hash, c)],
            )
            for op in self.roster
            for c in self.run.policy_hashes[1:]
        )
        if self.pairs != expected_pairs:
            raise ValueError("bundle matched pairing identity mismatch")
        if tuple(sorted(self.artifacts)) != self.artifacts or len(dict(self.artifacts)) != len(
            self.artifacts
        ):
            raise ValueError("sorted unique artifact identities required")
        for key, domain, values in (
            ("results", "B_RESULTS", self.results),
            ("pairs", "B_PAIRS", self.pairs),
            ("counterfactuals", "B_COUNTERFACTUALS", self.counterfactuals),
        ):
            if dict(self.artifacts).get(key) != digest(
                domain, tuple(v.record_hash for v in values)
            ):
                raise ValueError("bundle output artifact mismatch")
        if "fingerprint" in dict(self.artifacts) or self.fingerprint != dev_fingerprint(
            self.model_dump(mode="json", exclude={"fingerprint", "record_hash"})
        ):
            raise ValueError("DEV evidence fingerprint mismatch")
        return self


def dev_fingerprint(payload: object) -> str:
    from .contracts import digest

    return digest("DEV_EVIDENCE_BUNDLE_V1", payload)


# Explicit contract dependencies; no native engine or I/O is imported here.
from trader_assist_v0.contracts.common import FiniteDecimal  # noqa: E402

from .contracts import Opportunity  # noqa: E402
from .dev_lifecycle import DevPreregistration, DevTrial, DevTrialLedger  # noqa: E402
from .reporting import CandidateResult, CounterfactualPathRef, Pair  # noqa: E402

DevEvidenceBundle.model_rebuild()
