"""Semantic element scoring based on the design spec."""

from __future__ import annotations

from typing import Any, Dict, List

from domain.models import Candidate, Intent


class SemanticService:
    def __init__(self) -> None:
        self.weights = {
            "text_match": 0.4,
            "element_type": 0.25,
            "context": 0.2,
            "interactivity": 0.15,
        }

    def score(self, elements: List[Dict[str, Any]], intent: Intent) -> List[Candidate]:
        candidates: List[Candidate] = []
        for raw in elements:
            candidate = Candidate(
                selector=raw.get("selector", ""),
                tag=str(raw.get("tag", "")).lower(),
                text=raw.get("text", "") or "",
                aria_label=raw.get("aria_label", "") or "",
                role=str(raw.get("role", "")).lower(),
                type=str(raw.get("type", "")).lower(),
                placeholder=raw.get("placeholder", "") or "",
                nearby_text=raw.get("nearby_text", "") or "",
                is_visible=bool(raw.get("is_visible", True)),
                is_enabled=bool(raw.get("is_enabled", True)),
                position=raw.get("position", {}) or {},
            )
            candidate.scores = {
                "text_match": self._text_match(candidate, intent),
                "element_type": self._element_type_match(candidate, intent),
                "context": self._context_match(candidate, intent),
                "interactivity": self._interactivity(candidate),
            }
            candidate.total_score = sum(
                candidate.scores[name] * weight for name, weight in self.weights.items()
            )
            candidate.confidence = round(min(1.0, candidate.total_score + 0.1), 3)
            candidates.append(candidate)
        candidates.sort(key=lambda item: item.total_score, reverse=True)
        return candidates

    def _text_match(self, candidate: Candidate, intent: Intent) -> float:
        haystack = " ".join(
            [
                candidate.text.lower(),
                candidate.aria_label.lower(),
                candidate.placeholder.lower(),
                candidate.nearby_text.lower(),
            ]
        )
        if not haystack.strip():
            return 0.0
        matches = sum(1 for keyword in intent.keywords if keyword.lower() in haystack)
        return min(1.0, matches / max(len(intent.keywords), 1))

    def _element_type_match(self, candidate: Candidate, intent: Intent) -> float:
        if candidate.tag in intent.element_types or candidate.type in intent.element_types:
            return 1.0
        if candidate.role in {"button", "link", "textbox", "searchbox"}:
            return 0.7
        return 0.2

    def _context_match(self, candidate: Candidate, intent: Intent) -> float:
        if intent.target.lower() and intent.target.lower() in candidate.nearby_text.lower():
            return 1.0
        y_pos = float(candidate.position.get("y", 9999) or 9999)
        return 0.8 if y_pos < 400 else 0.4

    def _interactivity(self, candidate: Candidate) -> float:
        if candidate.is_visible and candidate.is_enabled:
            return 1.0
        if candidate.is_visible:
            return 0.5
        return 0.0
