"""Tests for semantic scoring and selection flow."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "navis-backend"))

from repositories.memory import InMemoryFeedbackRepository, InMemorySessionRepository
from services.intent_service import IntentService
from services.navigation_service import NavigationService
from services.policy_service import PolicyService
from services.semantic_service import SemanticService


async def _run_flow():
    session_repository = InMemorySessionRepository()
    session = session_repository.create()
    navigation_service = NavigationService(
        intent_service=IntentService(),
        semantic_service=SemanticService(),
        policy_service=PolicyService(InMemoryFeedbackRepository()),
        session_repository=session_repository,
    )
    return await navigation_service.process(
        session_id=session.session_id,
        goal="click login button",
        page_context={"title": "Example", "url": "https://example.com"},
        elements=[
            {"selector": "#login", "tag": "button", "text": "Login", "is_visible": True, "is_enabled": True, "position": {"y": 100}},
            {"selector": "#help", "tag": "a", "text": "Help", "is_visible": True, "is_enabled": True, "position": {"y": 700}},
        ],
    )


def test_navigation_flow_selects_login_button():
    import asyncio

    result = asyncio.run(_run_flow())
    assert result["decision"]["selected"]["selector"] == "#login"
    assert result["candidates"][0]["text"] == "Login"
