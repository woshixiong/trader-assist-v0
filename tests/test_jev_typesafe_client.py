from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from typesafe_sdk import RetryPolicy

from trader_assist_v0.jev.contracts import MODEL_DEADLINE_SECONDS, ModelMetadata
from trader_assist_v0.jev.questions import ENTRY_ACTION_LABELS, ENTRY_ACTION_NOW, arm_b_questions
from trader_assist_v0.jev.typesafe_client import (
    JevModelTimeout,
    TypeSafeAdapter,
)


class FakeModels:
    def __init__(self, owner: FakeClient) -> None:
        self.owner = owner

    async def list(self, *, retry: RetryPolicy, timeout: float) -> object:
        self.owner.calls.append(("models", retry.max_retries, timeout))
        return SimpleNamespace(
            models=(
                SimpleNamespace(
                    name="model-a", description="test model", release_date="2026-09-18"
                ),
            )
        )


class FakeClient:
    def __init__(self, retry: RetryPolicy, timeout: float, *, sleep: float = 0.0) -> None:
        self.constructor_retry = retry.max_retries
        self.constructor_timeout = timeout
        self.sleep = sleep
        self.calls: list[tuple[str, int, float]] = []
        self.models = FakeModels(self)
        self.closed = False

    async def system_one(
        self,
        state: object,
        questions: object,
        *,
        model: str,
        retry: RetryPolicy,
        timeout: float,
    ) -> object:
        self.calls.append(("system_one", retry.max_retries, timeout))
        if self.sleep:
            await asyncio.sleep(self.sleep)
        probability = 1.0 / len(ENTRY_ACTION_LABELS)
        answer = SimpleNamespace(
            choice="WAIT",
            probabilities={label: probability for label in ENTRY_ACTION_LABELS},
        )
        return SimpleNamespace(
            model="model-returned",
            usage=SimpleNamespace(input_tokens=17, output_tokens=3),
            choices={ENTRY_ACTION_NOW: answer},
        )

    async def aclose(self) -> None:
        self.closed = True


def test_retry_policy_zero_deadline_identity_metadata_and_probabilities() -> None:
    created: list[FakeClient] = []

    def factory(retry: RetryPolicy, timeout: float) -> FakeClient:
        client = FakeClient(retry, timeout)
        created.append(client)
        return client

    async def run() -> None:
        async with TypeSafeAdapter(client_factory=factory) as adapter:
            models = await adapter.list_models()
            assert models.models == (
                ModelMetadata("model-a", "test model", "2026-09-18"),
            )
            result = await adapter.system_one(
                state={"x": 1},
                questions=arm_b_questions(),
                expected_labels={ENTRY_ACTION_NOW: ENTRY_ACTION_LABELS},
                requested_model="model-requested",
                model_metadata=models.models[0],
            )
            assert result.identity.requested_model == "model-requested"
            assert result.identity.returned_model == "model-returned"
            assert result.identity.metadata == models.models[0]
            assert result.usage.input_tokens == 17
            labels = tuple(label for label, _ in result.choices[0][1].probabilities)
            assert labels == ENTRY_ACTION_LABELS

    asyncio.run(run())
    client = created[0]
    assert client.constructor_retry == 0
    assert client.constructor_timeout == MODEL_DEADLINE_SECONDS
    assert client.calls == [
        ("models", 0, MODEL_DEADLINE_SECONDS),
        ("system_one", 0, MODEL_DEADLINE_SECONDS),
    ]
    assert client.closed


def test_total_deadline_maps_to_model_timeout_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import trader_assist_v0.jev.typesafe_client as module

    created: list[FakeClient] = []

    def factory(retry: RetryPolicy, timeout: float) -> FakeClient:
        client = FakeClient(retry, timeout, sleep=0.02)
        created.append(client)
        return client

    monkeypatch.setattr(module, "MODEL_DEADLINE_SECONDS", 0.001)

    async def run() -> None:
        adapter = TypeSafeAdapter(client_factory=factory)
        with pytest.raises(JevModelTimeout):
            await adapter.system_one(
                state={},
                questions=arm_b_questions(),
                expected_labels={ENTRY_ACTION_NOW: ENTRY_ACTION_LABELS},
                requested_model="model-requested",
            )
        await adapter.aclose()

    asyncio.run(run())
    assert created[0].calls == [("system_one", 0, 0.001)]
