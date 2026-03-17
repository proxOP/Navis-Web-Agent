"""Intent parsing service with local heuristics and optional OpenAI usage."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Dict, List

from openai import OpenAI

from domain.models import Intent


logger = logging.getLogger(__name__)


class IntentService:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        self._client = OpenAI(api_key=api_key) if api_key else None

    def is_ready(self) -> bool:
        return True

    async def parse(self, user_goal: str, page_context: Dict[str, str]) -> Intent:
        if self._client:
            try:
                return await self._parse_with_model(user_goal, page_context)
            except Exception as exc:
                logger.warning(f"Falling back to heuristic intent parsing: {exc}")
        return self._parse_heuristically(user_goal)

    async def _parse_with_model(self, user_goal: str, page_context: Dict[str, str]) -> Intent:
        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only JSON for web navigation intent parsing. "
                        "Use keys: goal, action_type, target, keywords, element_types, "
                        "requires_confirmation, confidence."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "user_goal": user_goal,
                            "page_context": page_context,
                        }
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=250,
        )
        content = response.choices[0].message.content or "{}"
        if content.startswith("```"):
            content = content.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        return self._from_mapping(data, fallback_goal=user_goal)

    def _parse_heuristically(self, user_goal: str) -> Intent:
        text = user_goal.strip()
        lowered = text.lower()
        keywords = self._extract_keywords(lowered)

        action_type = "click"
        element_types = ["button", "link"]
        requires_confirmation = False

        if any(term in lowered for term in ["scroll up", "go up", "move up"]):
            action_type = "scroll_up"
            element_types = []
        elif any(term in lowered for term in ["scroll down", "go down", "move down"]):
            action_type = "scroll_down"
            element_types = []
        elif any(term in lowered for term in ["go back", "navigate back", "previous page"]):
            action_type = "navigate_back"
            element_types = []
        elif any(term in lowered for term in ["go forward", "navigate forward", "next page"]):
            action_type = "navigate_forward"
            element_types = []
        elif any(term in lowered for term in ["highlight", "show me", "focus on"]):
            action_type = "highlight"
            element_types = ["button", "link", "input", "select", "textarea"]
        elif any(term in lowered for term in ["search", "find", "look for"]):
            action_type = "search"
            element_types = ["input", "button", "link"]
        elif any(term in lowered for term in ["fill", "enter", "type"]):
            action_type = "fill_form"
            element_types = ["input", "textarea", "select"]
            requires_confirmation = True
        elif any(term in lowered for term in ["select", "choose", "pick"]):
            action_type = "select"
            element_types = ["select", "option", "button"]
        elif any(term in lowered for term in ["go to", "open", "navigate"]):
            action_type = "navigate"
            element_types = ["link", "button"]

        return Intent(
            goal=text or "Complete the requested navigation action",
            action_type=action_type,
            target=text or "requested target",
            keywords=keywords,
            element_types=element_types,
            requires_confirmation=requires_confirmation,
            confidence=0.66 if text else 0.3,
        )

    def _extract_keywords(self, lowered_goal: str) -> List[str]:
        terms = re.findall(r"[a-z0-9]+", lowered_goal)
        stop_words = {"the", "a", "an", "to", "for", "on", "in", "my", "me", "please"}
        keywords = [term for term in terms if term not in stop_words]
        return keywords[:6] or ["target"]

    def _from_mapping(self, data: Dict[str, object], fallback_goal: str) -> Intent:
        keywords = [str(item) for item in data.get("keywords", []) if str(item).strip()]
        element_types = [str(item) for item in data.get("element_types", []) if str(item).strip()]
        return Intent(
            goal=str(data.get("goal") or fallback_goal),
            action_type=str(data.get("action_type") or "click"),
            target=str(data.get("target") or fallback_goal),
            keywords=keywords or self._extract_keywords(fallback_goal.lower()),
            element_types=element_types or ["button", "link"],
            requires_confirmation=bool(data.get("requires_confirmation", False)),
            confidence=float(data.get("confidence", 0.6)),
        )
