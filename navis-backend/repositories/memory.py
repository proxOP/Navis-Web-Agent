"""Simple in-memory repositories for local development."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from domain.models import SessionRecord


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionRecord] = {}

    def create(self, metadata: Optional[Dict[str, Any]] = None) -> SessionRecord:
        session_id = str(uuid.uuid4())
        record = SessionRecord(session_id=session_id, metadata=metadata or {})
        self._sessions[session_id] = record
        return record

    def get(self, session_id: str) -> Optional[SessionRecord]:
        return self._sessions.get(session_id)

    def update(self, session_id: str, updates: Dict[str, Any]) -> Optional[SessionRecord]:
        record = self._sessions.get(session_id)
        if record is None:
            return None
        if "last_goal" in updates:
            record.last_goal = updates["last_goal"]
        record.metadata.update(updates.get("metadata", {}))
        record.updated_at = datetime.utcnow().isoformat()
        return record


class InMemoryFeedbackRepository:
    def __init__(self) -> None:
        self._events: List[Dict[str, Any]] = []

    def add(self, event: Dict[str, Any]) -> None:
        self._events.append({**event, "recorded_at": datetime.utcnow().isoformat()})

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self._events)
