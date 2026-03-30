"""Tests for the baseline inference script."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

ROOT = os.path.join(os.path.dirname(__file__), "..")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import inference


class FakeModels:
    def __init__(self, choices: list[str]) -> None:
        self._choices = choices
        self._index = 0

    def generate_content(self, **_: object) -> SimpleNamespace:
        choice = self._choices[self._index]
        self._index += 1
        return SimpleNamespace(text=f'{{"click_link_id": "{choice}"}}')


class FakeClient:
    def __init__(self, choices: list[str]) -> None:
        self.models = FakeModels(choices)


def test_run_task_completes_with_mocked_google_genai_client():
    client = FakeClient(["home_support", "support_contact"])
    result = inference.run_task(client, "fake-model", "easy", mode="google_genai")

    assert result["task_id"] == "easy"
    assert result["score"] == 1.0
    assert result["summary"]["reached_target"] is True


def test_heuristic_policy_completes_easy_task_without_llm():
    result = inference.run_task(None, None, "easy", mode="heuristic")

    assert result["task_id"] == "easy"
    assert result["score"] >= 0.7
    assert result["summary"]["reached_target"] is True


def test_heuristic_selects_support_link_for_easy_start_page():
    env = inference.NavisWebEnvironment(default_task_id="easy")
    observation = env.reset(task_id="easy")

    click_link_id = inference.choose_action_with_heuristic(observation)

    assert click_link_id == "home_support"
