"""Pydantic API schemas for the minimal Navis backend."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GoalRequest(BaseModel):
    session_id: str
    user_goal: str
    page_context: Dict[str, Any] = Field(default_factory=dict)


class AnalyzeRequest(BaseModel):
    session_id: str
    user_goal: str
    page_context: Dict[str, Any] = Field(default_factory=dict)
    elements: List[Dict[str, Any]] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    session_id: str
    user_goal: str
    page_context: Dict[str, Any] = Field(default_factory=dict)
    selected: Optional[Dict[str, Any]] = None
    outcome: str
    notes: Optional[str] = None
