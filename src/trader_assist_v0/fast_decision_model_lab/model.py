from __future__ import annotations

from dataclasses import dataclass

from .contracts import DecisionArm, DecisionRequest, DecisionResult
from .serialization import canonical_sha256


@dataclass(frozen=True, slots=True)
class DecisionBatch:
    decision_event_id: str
    snapshot_id: str
    snapshot_hash: str
    data_cutoff_ns: int
    requests: tuple[DecisionRequest, ...]

    def __post_init__(self) -> None:
        if not self.requests:
            raise ValueError("decision batch requires at least one request")
        seen: set[tuple[str, DecisionArm]] = set()
        for request in self.requests:
            if (
                request.decision_event_id != self.decision_event_id
                or request.snapshot_id != self.snapshot_id
                or request.snapshot_hash != self.snapshot_hash
                or request.data_cutoff_ns != self.data_cutoff_ns
            ):
                raise ValueError("all batch requests must share event/snapshot/hash/cutoff")
            cell = (request.model_target.model_target_id, request.arm)
            if cell in seen:
                raise ValueError("duplicate model_target x arm cell")
            seen.add(cell)


@dataclass(frozen=True, slots=True)
class DecisionMatrixCell:
    model_target_id: str
    arm: DecisionArm
    invocation_id: str
    result: DecisionResult

    def __post_init__(self) -> None:
        if self.result.model_target.model_target_id != self.model_target_id:
            raise ValueError("matrix cell model target does not match result")
        if self.result.arm is not self.arm or self.result.invocation_id != self.invocation_id:
            raise ValueError("matrix cell arm/invocation does not match result")


@dataclass(frozen=True, slots=True)
class DecisionBatchResult:
    decision_event_id: str
    snapshot_id: str
    snapshot_hash: str
    data_cutoff_ns: int
    cells: tuple[DecisionMatrixCell, ...]

    def __post_init__(self) -> None:
        expected = tuple(sorted(self.cells, key=_cell_sort_key))
        if self.cells != expected:
            raise ValueError("DecisionBatchResult cells must be in deterministic order")
        seen: set[tuple[str, DecisionArm]] = set()
        for cell in self.cells:
            result = cell.result
            if (
                result.decision_event_id != self.decision_event_id
                or result.snapshot_id != self.snapshot_id
                or result.snapshot_hash != self.snapshot_hash
                or result.data_cutoff_ns != self.data_cutoff_ns
            ):
                raise ValueError("batch result cell does not match batch identity")
            key = (cell.model_target_id, cell.arm)
            if key in seen:
                raise ValueError("duplicate result matrix cell")
            seen.add(key)

    @property
    def batch_hash(self) -> str:
        return canonical_sha256(self)


def _cell_sort_key(cell: DecisionMatrixCell) -> tuple[str, str, str]:
    return (cell.model_target_id, cell.arm.value, cell.invocation_id)


def build_batch_result(
    batch: DecisionBatch, results: tuple[DecisionResult, ...]
) -> DecisionBatchResult:
    by_invocation = {result.invocation_id: result for result in results}
    if len(by_invocation) != len(results):
        raise ValueError("duplicate invocation result")
    if set(by_invocation) != {request.invocation_id for request in batch.requests}:
        raise ValueError("batch results must cover exactly the planned invocations")
    cells = tuple(
        sorted(
            (
                DecisionMatrixCell(
                    model_target_id=request.model_target.model_target_id,
                    arm=request.arm,
                    invocation_id=request.invocation_id,
                    result=by_invocation[request.invocation_id],
                )
                for request in batch.requests
            ),
            key=_cell_sort_key,
        )
    )
    return DecisionBatchResult(
        decision_event_id=batch.decision_event_id,
        snapshot_id=batch.snapshot_id,
        snapshot_hash=batch.snapshot_hash,
        data_cutoff_ns=batch.data_cutoff_ns,
        cells=cells,
    )
