"""Tests for feedback recording policy."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "navis-backend"))

from domain.models import Intent
from repositories.memory import InMemoryFeedbackRepository
from services.policy_service import PolicyService


def test_policy_service_records_feedback():
    repository = InMemoryFeedbackRepository()
    service = PolicyService(repository)
    intent = Intent(
        goal="click login button",
        action_type="click",
        target="login button",
        keywords=["login", "button"],
        element_types=["button", "link"],
        requires_confirmation=False,
        confidence=0.7,
    )
    event = service.record_feedback(
        session_id="session-1",
        intent=intent,
        selected={"selector": "#login"},
        outcome="success",
        notes="worked",
    )
    assert event["outcome"] == "success"
    assert len(repository.list_all()) == 1


def test_policy_service_direct_action_for_scroll():
    repository = InMemoryFeedbackRepository()
    service = PolicyService(repository)
    intent = Intent(
        goal="scroll down",
        action_type="scroll_down",
        target="scroll down",
        keywords=["scroll", "down"],
        element_types=[],
        requires_confirmation=False,
        confidence=0.8,
    )
    decision = service.select(intent, [])
    assert decision["selected"]["action_type"] == "scroll_down"
    assert decision["requires_confirmation"] is False
