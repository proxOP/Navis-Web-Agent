"""Top-level orchestration service for simple navigation flows."""

from __future__ import annotations

from typing import Any, Dict, List

from domain.models import Intent
from repositories.memory import InMemorySessionRepository
from services.intent_service import IntentService
from services.policy_service import PolicyService
from services.semantic_service import SemanticService


class NavigationService:
    def __init__(
        self,
        intent_service: IntentService,
        semantic_service: SemanticService,
        policy_service: PolicyService,
        session_repository: InMemorySessionRepository,
    ) -> None:
        self.intent_service = intent_service
        self.semantic_service = semantic_service
        self.policy_service = policy_service
        self.session_repository = session_repository

    async def process(self, session_id: str, goal: str, page_context: Dict[str, Any], elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        intent = await self.intent_service.parse(goal, page_context)
        self.session_repository.update(session_id, {"last_goal": intent.goal})
        scored = self.semantic_service.score(elements, intent)
        decision = self.policy_service.select(intent, scored)
        return {
            "session_id": session_id,
            "intent": {
                "goal": intent.goal,
                "action_type": intent.action_type,
                "target": intent.target,
                "keywords": intent.keywords,
                "element_types": intent.element_types,
                "requires_confirmation": intent.requires_confirmation,
                "confidence": intent.confidence,
            },
            "decision": decision,
            "candidates": [candidate.to_dict() for candidate in scored[:5]],
            "recommended_action": decision.get("selected"),
        }
