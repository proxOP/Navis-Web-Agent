#!/usr/bin/env python3
"""Minimal Navis backend aligned with the current spec baseline."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.schemas import AnalyzeRequest, FeedbackRequest, GoalRequest, SessionCreateRequest
from repositories.memory import InMemoryFeedbackRepository, InMemorySessionRepository
from services.intent_service import IntentService
from services.navigation_service import NavigationService
from services.policy_service import PolicyService
from services.semantic_service import SemanticService


session_repository = InMemorySessionRepository()
feedback_repository = InMemoryFeedbackRepository()
intent_service = IntentService()
semantic_service = SemanticService()
policy_service = PolicyService(feedback_repository=feedback_repository)
navigation_service = NavigationService(
    intent_service=intent_service,
    semantic_service=semantic_service,
    policy_service=policy_service,
    session_repository=session_repository,
)

app = FastAPI(title="Navis Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://*", "http://localhost", "http://127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict:
    return {"message": "Navis backend is running", "version": "0.1.0"}


@app.post("/sessions")
async def create_session(request: SessionCreateRequest) -> dict:
    session = session_repository.create(metadata=request.metadata)
    return {
        "session_id": session.session_id,
        "created_at": session.created_at,
        "metadata": session.metadata,
    }


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    session = session_repository.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session.session_id,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "last_goal": session.last_goal,
        "metadata": session.metadata,
    }


@app.post("/intent/parse")
async def parse_intent(request: GoalRequest) -> dict:
    if session_repository.get(request.session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    intent = await intent_service.parse(request.user_goal, request.page_context)
    session_repository.update(request.session_id, {"last_goal": intent.goal})
    return {
        "goal": intent.goal,
        "action_type": intent.action_type,
        "target": intent.target,
        "keywords": intent.keywords,
        "element_types": intent.element_types,
        "requires_confirmation": intent.requires_confirmation,
        "confidence": intent.confidence,
    }


@app.post("/semantic/analyze")
async def analyze(request: AnalyzeRequest) -> dict:
    if session_repository.get(request.session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await navigation_service.process(
        session_id=request.session_id,
        goal=request.user_goal,
        page_context=request.page_context,
        elements=request.elements,
    )
    return result


@app.post("/feedback")
async def record_feedback(request: FeedbackRequest) -> dict:
    session = session_repository.get(request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    intent = await intent_service.parse(request.user_goal, request.page_context)
    event = policy_service.record_feedback(
        session_id=request.session_id,
        intent=intent,
        selected=request.selected,
        outcome=request.outcome,
        notes=request.notes,
    )
    return {"recorded": True, "event": event}


@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "version": "0.1.0",
        "components": {
            "intent_service": intent_service.is_ready(),
            "semantic_service": True,
            "policy_service": True,
            "session_repository": True,
            "feedback_repository": True,
        },
        "feedback_events": len(feedback_repository.list_all()),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
