"""Selection and feedback policy for basic actions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from domain.models import Candidate, Intent
from repositories.memory import InMemoryFeedbackRepository


class PolicyService:
    def __init__(self, feedback_repository: InMemoryFeedbackRepository, confidence_threshold: float = 0.72) -> None:
        self.feedback_repository = feedback_repository
        self.confidence_threshold = confidence_threshold

    def select(self, intent: Intent, candidates: List[Candidate]) -> Dict[str, Any]:
        direct_action = self._direct_action_for(intent)
        if direct_action is not None:
            return {
                "requires_confirmation": intent.requires_confirmation,
                "reason": "direct_action",
                "selected": direct_action,
                "alternatives": [],
            }

        if not candidates:
            return {
                "requires_confirmation": True,
                "reason": "no_candidates",
                "selected": None,
                "alternatives": [],
            }

        top = candidates[0]
        alternatives = [candidate.to_dict() for candidate in candidates[1:4]]
        return {
            "requires_confirmation": intent.requires_confirmation or top.confidence < self.confidence_threshold,
            "reason": "sensitive_action" if intent.requires_confirmation else "low_confidence" if top.confidence < self.confidence_threshold else "high_confidence",
            "selected": top.to_dict(),
            "alternatives": alternatives,
        }

    def record_feedback(
        self,
        session_id: str,
        intent: Intent,
        selected: Optional[Dict[str, Any]],
        outcome: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        event = {
            "session_id": session_id,
            "goal": intent.goal,
            "action_type": intent.action_type,
            "selected": selected,
            "outcome": outcome,
            "notes": notes,
        }
        self.feedback_repository.add(event)
        return event

    def _direct_action_for(self, intent: Intent) -> Optional[Dict[str, Any]]:
        if intent.action_type in {"scroll_up", "scroll_down", "navigate_back", "navigate_forward"}:
            return {
                "action_type": intent.action_type,
                "selector": None,
                "text": intent.target,
                "confidence": intent.confidence,
            }
        return None
