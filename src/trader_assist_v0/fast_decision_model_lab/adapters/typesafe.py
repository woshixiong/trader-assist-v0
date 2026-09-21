from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol, cast

from typesafe_sdk import (
    AsyncTypeSafeClient,
    RetryPolicy,
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeAPIResponseValidationError,
    TypeSafeAPITimeoutError,
)

from ..contracts import (
    ChoiceDistribution,
    DecisionRequest,
    DecisionResult,
    InputFitEvidence,
    ModelIdentity,
    ModelInvocationStatus,
    NormalizedUsage,
)

TYPESAFE_API_KEY_ENV = "TYPESAFE_API_KEY"
TYPESAFE_SDK_PACKAGE = "typesafe-sdk"
TYPESAFE_SDK_VERSION = "0.7.0"


class _ChoiceLike(Protocol):
    choice: str
    probabilities: Mapping[str, float]


class _UsageLike(Protocol):
    input_tokens: int | None
    output_tokens: int | None


class _ResponseLike(Protocol):
    model: str
    usage: _UsageLike
    choices: Mapping[str, _ChoiceLike]


class _ModelLike(Protocol):
    name: str
    description: str
    release_date: str


class _ModelsResponseLike(Protocol):
    models: tuple[_ModelLike, ...]


class _ModelsResource(Protocol):
    async def list(self, *, retry: RetryPolicy, timeout: float) -> _ModelsResponseLike: ...


class _AsyncClient(Protocol):
    @property
    def models(self) -> _ModelsResource: ...

    async def system_one(
        self,
        state: object,
        questions: Mapping[str, object],
        *,
        model: str,
        retry: RetryPolicy,
        timeout: float,
    ) -> _ResponseLike: ...

    async def aclose(self) -> None: ...


type ClientFactory = Callable[[RetryPolicy, float], _AsyncClient]


@dataclass(frozen=True, slots=True)
class TypeSafeModelMetadata:
    name: str
    description: str
    release_date: str


def _official_client_factory(retry: RetryPolicy, timeout: float) -> _AsyncClient:
    return cast(_AsyncClient, AsyncTypeSafeClient(retry=retry, timeout=timeout))


def _wire_questions(request: DecisionRequest) -> dict[str, object]:
    return {
        question.name: {
            "type": "choice",
            "instructions": question.instructions,
            "criteria": {label: None for label in question.allowed_labels},
        }
        for question in request.question_pack.questions
    }


def _extract_choices(
    response: _ResponseLike, request: DecisionRequest
) -> tuple[tuple[str, ChoiceDistribution], ...]:
    expected = {
        question.name: question.allowed_labels for question in request.question_pack.questions
    }
    if set(response.choices) != set(expected):
        raise ValueError("TypeSafe response Choice set does not match submitted questions")
    normalized: list[tuple[str, ChoiceDistribution]] = []
    for question in request.question_pack.questions:
        answer = response.choices[question.name]
        probabilities = dict(answer.probabilities)
        if set(probabilities) != set(question.allowed_labels):
            raise ValueError("TypeSafe Choice probabilities are incomplete or invalid")
        normalized.append(
            (
                question.name,
                ChoiceDistribution(
                    selected=answer.choice,
                    probabilities=tuple(
                        (label, probabilities[label]) for label in question.allowed_labels
                    ),
                ),
            )
        )
    return tuple(normalized)


class TypeSafeAdapter:
    def __init__(self, *, client_factory: ClientFactory = _official_client_factory) -> None:
        self._retry = RetryPolicy(max_retries=0)
        self._client_factory = client_factory
        self._clients: list[_AsyncClient] = []

    async def __aenter__(self) -> "TypeSafeAdapter":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        for client in reversed(self._clients):
            await client.aclose()
        self._clients.clear()

    def _client(self, timeout: float) -> _AsyncClient:
        client = self._client_factory(self._retry, timeout)
        self._clients.append(client)
        return client

    async def list_models(
        self, *, deadline_seconds: float = 3.0
    ) -> tuple[TypeSafeModelMetadata, ...]:
        client = self._client(deadline_seconds)
        async with asyncio.timeout(deadline_seconds):
            response = await client.models.list(retry=self._retry, timeout=deadline_seconds)
        return tuple(
            TypeSafeModelMetadata(model.name, model.description, model.release_date)
            for model in response.models
        )

    async def invoke(self, request: DecisionRequest) -> DecisionResult:
        started = time.time_ns()
        client = self._client(request.deadline_seconds)
        identity = ModelIdentity(
            provider=request.model_target.provider,
            requested_model_id=request.model_target.requested_model_id,
            checkpoint_revision_or_digest=request.model_target.requested_checkpoint_or_revision,
            sdk_package=TYPESAFE_SDK_PACKAGE,
            sdk_version=TYPESAFE_SDK_VERSION,
        )
        try:
            async with asyncio.timeout(request.deadline_seconds):
                response = await client.system_one(
                    request.state_payload,
                    _wire_questions(request),
                    model=request.model_target.requested_model_id,
                    retry=self._retry,
                    timeout=request.deadline_seconds,
                )
            choices = _extract_choices(response, request)
            state_truncated = bool(getattr(response, "state_truncated", False))
            finished = time.time_ns()
            returned = getattr(response, "model", None)
            model_identity = ModelIdentity(
                provider=request.model_target.provider,
                requested_model_id=request.model_target.requested_model_id,
                returned_model_or_checkpoint_id=returned,
                checkpoint_revision_or_digest=(
                    getattr(response, "checkpoint_revision", None)
                    or request.model_target.requested_checkpoint_or_revision
                ),
                sdk_package=TYPESAFE_SDK_PACKAGE,
                sdk_version=TYPESAFE_SDK_VERSION,
                inference_runtime=getattr(response, "runtime", None),
                inference_runtime_version=getattr(response, "runtime_version", None),
                calibration_config_id=getattr(response, "calibration_config_id", None),
                inference_device=getattr(response, "device", None),
            )
            input_fit = InputFitEvidence(state_truncated=state_truncated)
            if state_truncated:
                return DecisionResult.failure_for(
                    request,
                    status=ModelInvocationStatus.VALIDATION_ERROR,
                    request_ts_ns=started,
                    response_ts_ns=finished,
                    error_code="STATE_TRUNCATED",
                    error_class="InputFitValidationError",
                    model_identity=model_identity,
                    input_fit=input_fit,
                )
            return DecisionResult(
                decision_event_id=request.decision_event_id,
                invocation_id=request.invocation_id,
                snapshot_id=request.snapshot_id,
                snapshot_hash=request.snapshot_hash,
                data_cutoff_ns=request.data_cutoff_ns,
                model_target=request.model_target,
                arm=request.arm,
                question_pack_id=request.question_pack.question_pack_id,
                question_pack_version=request.question_pack.version,
                experiment_config_id=request.experiment_config_id,
                status=ModelInvocationStatus.SUCCESS,
                model_identity=model_identity,
                choices=choices,
                request_ts_ns=started,
                response_ts_ns=finished,
                latency_ms=(finished - started) / 1_000_000.0,
                usage=NormalizedUsage(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                ),
                input_fit=input_fit,
            )
        except (TypeSafeAPITimeoutError, TimeoutError):
            finished = time.time_ns()
            return DecisionResult.failure_for(
                request,
                status=ModelInvocationStatus.TIMEOUT,
                request_ts_ns=started,
                response_ts_ns=finished,
                error_code="TYPESAFE_TIMEOUT",
                error_class="TypeSafeTimeout",
                model_identity=identity,
            )
        except TypeSafeAPIResponseValidationError:
            finished = time.time_ns()
            return DecisionResult.failure_for(
                request,
                status=ModelInvocationStatus.VALIDATION_ERROR,
                request_ts_ns=started,
                response_ts_ns=finished,
                error_code="TYPESAFE_RESPONSE_VALIDATION",
                error_class="TypeSafeAPIResponseValidationError",
                model_identity=identity,
            )
        except (TypeSafeAPIError, TypeSafeAPIConnectionError) as error:
            finished = time.time_ns()
            return DecisionResult.failure_for(
                request,
                status=ModelInvocationStatus.PROVIDER_ERROR,
                request_ts_ns=started,
                response_ts_ns=finished,
                error_code="TYPESAFE_PROVIDER_ERROR",
                error_class=type(error).__name__,
                model_identity=identity,
            )
        except (KeyError, ValueError) as error:
            finished = time.time_ns()
            return DecisionResult.failure_for(
                request,
                status=ModelInvocationStatus.VALIDATION_ERROR,
                request_ts_ns=started,
                response_ts_ns=finished,
                error_code="TYPESAFE_NORMALIZATION_ERROR",
                error_class=type(error).__name__,
                model_identity=identity,
            )
