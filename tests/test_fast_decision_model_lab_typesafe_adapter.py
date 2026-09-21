from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace

from typesafe_sdk import RetryPolicy

from trader_assist_v0.fast_decision_model_lab.adapters.typesafe import TypeSafeAdapter
from trader_assist_v0.fast_decision_model_lab.contracts import (
    STATE_SCHEMA_VERSION,
    DecisionRequest,
    ModelInvocationStatus,
    ModelTarget,
)
from trader_assist_v0.fast_decision_model_lab.questions import model_native_question_pack


def _request() -> DecisionRequest:
    pack = model_native_question_pack()
    return DecisionRequest(
        "event-1",
        "inv-1",
        "sha256:snapshot",
        "snapshot",
        123,
        STATE_SCHEMA_VERSION,
        {"x": 1},
        pack.arm,
        pack,
        "ctx-v1",
        "exp-v1",
        ModelTarget("target-a", "typesafe", "model-a", "rev-a", "typesafe-0.7.0", "1"),
    )


class FakeModels:
    async def list(self, *, retry: RetryPolicy, timeout: float):
        assert retry.max_retries == 0
        return SimpleNamespace(
            models=(SimpleNamespace(name="m", description="d", release_date="2026-09-18"),)
        )


class FakeClient:
    def __init__(
        self,
        retry: RetryPolicy,
        timeout: float,
        *,
        sleep: float = 0.0,
        truncated: bool = False,
    ) -> None:
        self.constructor_retry = retry.max_retries
        self.constructor_timeout = timeout
        self.sleep = sleep
        self.truncated = truncated
        self.calls = []
        self.models = FakeModels()
        self.closed = False

    async def system_one(self, state, questions, *, model, retry, timeout):
        self.calls.append((model, retry.max_retries, timeout, tuple(questions)))
        if self.sleep:
            await asyncio.sleep(self.sleep)
        choices = {}
        for name, spec in questions.items():
            labels = tuple(spec["criteria"])
            p = 1.0 / len(labels)
            choices[name] = SimpleNamespace(choice=labels[-1], probabilities={x: p for x in labels})
        return SimpleNamespace(
            model="returned-model",
            usage=SimpleNamespace(input_tokens=11, output_tokens=3),
            choices=choices,
            state_truncated=self.truncated,
        )

    async def aclose(self):
        self.closed = True


def test_typesafe_adapter_zero_retry_deadline_and_complete_probabilities() -> None:
    created = []

    def factory(retry, timeout):
        client = FakeClient(retry, timeout)
        created.append(client)
        return client

    async def run() -> None:
        async with TypeSafeAdapter(client_factory=factory) as adapter:
            result = await adapter.invoke(_request())
            assert result.status is ModelInvocationStatus.SUCCESS
            assert result.model_identity.returned_model_or_checkpoint_id == "returned-model"
            labels = tuple(label for label, _ in result.choices[0][1].probabilities)
            assert labels == _request().question_pack.questions[0].allowed_labels

    asyncio.run(run())
    assert created[0].constructor_retry == 0
    assert created[0].constructor_timeout == 3.0
    assert created[0].calls[0][1] == 0
    assert created[0].closed


def test_typesafe_timeout_and_truncation_are_typed_failures() -> None:
    async def run_timeout() -> None:
        adapter = TypeSafeAdapter(
            client_factory=lambda retry, timeout: FakeClient(retry, timeout, sleep=0.02)
        )
        result = await adapter.invoke(replace(_request(), deadline_seconds=0.001))
        await adapter.aclose()
        assert result.status is ModelInvocationStatus.TIMEOUT

    async def run_truncated() -> None:
        adapter = TypeSafeAdapter(
            client_factory=lambda retry, timeout: FakeClient(retry, timeout, truncated=True)
        )
        result = await adapter.invoke(_request())
        await adapter.aclose()
        assert result.status is ModelInvocationStatus.VALIDATION_ERROR
        assert result.error_code == "STATE_TRUNCATED"

    asyncio.run(run_timeout())
    asyncio.run(run_truncated())
