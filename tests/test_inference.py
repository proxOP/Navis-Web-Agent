"""Tests for the baseline inference script."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

ROOT = os.path.join(os.path.dirname(__file__), "..")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import inference


class FakeCompletions:
    def __init__(self, choices: list[str]) -> None:
        self._choices = choices
        self._index = 0

    def create(self, **_: object) -> SimpleNamespace:
        choice = self._choices[self._index]
        self._index += 1
        message = SimpleNamespace(content=f'{{"click_link_id": "{choice}"}}')
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    def __init__(self, choices: list[str]) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions(choices))


def test_run_task_completes_with_mocked_openai_client():
    client = FakeClient(["home_support", "support_contact"])
    result = inference.run_task(client, "fake-model", "easy")

    assert result["task_id"] == "easy"
    assert result["score"] == 1.0
    assert result["summary"]["reached_target"] is True
