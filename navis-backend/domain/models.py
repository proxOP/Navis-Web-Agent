"""Core domain models for the minimal Navis backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Intent:
    goal: str
    action_type: str
    target: str
    keywords: List[str]
    element_types: List[str]
    requires_confirmation: bool
    confidence: float


@dataclass
class Candidate:
    selector: str
    tag: str = ""
    text: str = ""
    aria_label: str = ""
    role: str = ""
    type: str = ""
    placeholder: str = ""
    nearby_text: str = ""
    is_visible: bool = True
    is_enabled: bool = True
    position: Dict[str, float] = field(default_factory=dict)
    scores: Dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selector": self.selector,
            "tag": self.tag,
            "text": self.text,
            "aria_label": self.aria_label,
            "role": self.role,
            "type": self.type,
            "placeholder": self.placeholder,
            "nearby_text": self.nearby_text,
            "is_visible": self.is_visible,
            "is_enabled": self.is_enabled,
            "position": self.position,
            "scores": self.scores,
            "total_score": self.total_score,
            "confidence": self.confidence,
        }


@dataclass
class SessionRecord:
    session_id: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_goal: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

