from __future__ import annotations

import asyncio
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

from .contracts import (
    MODEL_DEADLINE_SECONDS,
    ChoiceDistribution,
    ModelCallIdentity,
    ModelMetadata,
    UsageTelemetry,
)
from .questions import extract_choice

TYPESAFE_API_KEY_ENV = "TYPESAFE_API_KEY"


class JevModelError(RuntimeError):
    """Base deterministic JEV model-adapter error."""


class JevModelTimeout(JevModelError):
    """The frozen total model deadline elapsed."""


class JevModelAPIError(JevModelError):
    """The SDK reported an API or connection failure."""


class JevModelValidationError(JevModelError):
    """The SDK/provider response did not satisfy the required response contract."""


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
class TypeSafeCallResult:
    identity: ModelCallIdentity
    choices: tuple[tuple[str, ChoiceDistribution], ...]
    usage: UsageTelemetry


@dataclass(frozen=True, slots=True)
class TypeSafeModelsResult:
    models: tuple[ModelMetadata, ...]


def _official_client_factory(retry: RetryPolicy, timeout: float) -> _AsyncClient:
    # No api_key argument is accepted by this adapter. The official SDK resolves TYPESAFE_API_KEY.
    return cast(_AsyncClient, AsyncTypeSafeClient(retry=retry, timeout=timeout))


class TypeSafeAdapter:
    def __init__(self, *, client_factory: ClientFactory = _official_client_factory) -> None:
        self._retry = RetryPolicy(max_retries=0)
        self._client = client_factory(self._retry, MODEL_DEADLINE_SECONDS)

    async def __aenter__(self) -> TypeSafeAdapter:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def list_models(self) -> TypeSafeModelsResult:
        try:
            async with asyncio.timeout(MODEL_DEADLINE_SECONDS):
                response = await self._client.models.list(
                    retry=self._retry, timeout=MODEL_DEADLINE_SECONDS
                )
        except TypeSafeAPITimeoutError as error:
            raise JevModelTimeout("TypeSafe models request exceeded the 3s deadline") from error
        except TimeoutError as error:
            raise JevModelTimeout("TypeSafe models request exceeded the 3s deadline") from error
        except TypeSafeAPIResponseValidationError as error:
            raise JevModelValidationError("TypeSafe models response validation failed") from error
        except (TypeSafeAPIError, TypeSafeAPIConnectionError) as error:
            raise JevModelAPIError("TypeSafe models API request failed") from error
        return TypeSafeModelsResult(
            models=tuple(
                ModelMetadata(
                    name=model.name,
                    description=model.description,
                    release_date=model.release_date,
                )
                for model in response.models
            )
        )

    async def system_one(
        self,
        *,
        state: object,
        questions: Mapping[str, object],
        expected_labels: Mapping[str, tuple[str, ...]],
        requested_model: str,
        model_metadata: ModelMetadata | None = None,
    ) -> TypeSafeCallResult:
        if set(questions) != set(expected_labels):
            raise ValueError("expected_labels must cover exactly the submitted questions")
        try:
            async with asyncio.timeout(MODEL_DEADLINE_SECONDS):
                response = await self._client.system_one(
                    state,
                    questions,
                    model=requested_model,
                    retry=self._retry,
                    timeout=MODEL_DEADLINE_SECONDS,
                )
        except TypeSafeAPITimeoutError as error:
            raise JevModelTimeout("TypeSafe System One request exceeded the 3s deadline") from error
        except TimeoutError as error:
            raise JevModelTimeout("TypeSafe System One request exceeded the 3s deadline") from error
        except TypeSafeAPIResponseValidationError as error:
            raise JevModelValidationError(
                "TypeSafe System One response validation failed"
            ) from error
        except (TypeSafeAPIError, TypeSafeAPIConnectionError) as error:
            raise JevModelAPIError("TypeSafe System One API request failed") from error

        if set(response.choices) != set(expected_labels):
            raise JevModelValidationError(
                "TypeSafe response Choice set does not match the submitted questions"
            )
        choices: list[tuple[str, ChoiceDistribution]] = []
        try:
            for name in questions:
                choices.append(
                    (name, extract_choice(response.choices[name], expected_labels[name]))
                )
        except (KeyError, ValueError) as error:
            raise JevModelValidationError(
                "TypeSafe Choice probabilities are incomplete or invalid"
            ) from error
        return TypeSafeCallResult(
            identity=ModelCallIdentity(
                requested_model=requested_model,
                returned_model=response.model,
                metadata=model_metadata,
            ),
            choices=tuple(choices),
            usage=UsageTelemetry(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
        )
