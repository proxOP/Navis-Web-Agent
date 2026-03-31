"""Compatibility helpers for running with or without the OpenEnv runtime."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, Dict, Generic, TypeVar
from uuid import uuid4

import requests
from fastapi import Body, FastAPI, HTTPException
from pydantic import BaseModel, Field

ActT = TypeVar("ActT", bound="Action")
ObsT = TypeVar("ObsT", bound="Observation")
StateT = TypeVar("StateT", bound="State")

try:
    from openenv.core.client_types import StepResult  # type: ignore
    from openenv.core.env_client import EnvClient  # type: ignore
    from openenv.core.env_server import create_app  # type: ignore
    from openenv.core.env_server.interfaces import Environment  # type: ignore
    from openenv.core.env_server.types import Action, Observation, State  # type: ignore
    OPENENV_AVAILABLE = True
except Exception:  # pragma: no cover - compatibility path
    OPENENV_AVAILABLE = False

    class Action(BaseModel):
        """Fallback action model."""

    class Observation(BaseModel):
        """Fallback observation model."""

        done: bool = Field(default=False, description="Whether the episode has terminated.")
        reward: float | None = Field(default=None, description="Reward emitted for this observation.")

    class State(BaseModel):
        """Fallback environment state model."""

        episode_id: str
        step_count: int = 0

    class Environment:
        """Fallback environment interface."""

        def reset(self, **kwargs: Any) -> Observation:
            raise NotImplementedError

        def step(self, action: Action, **kwargs: Any) -> Observation:
            raise NotImplementedError

        @property
        def state(self) -> State:
            raise NotImplementedError

    @dataclass
    class StepResult(Generic[ObsT]):
        """Fallback step result container."""

        observation: ObsT
        reward: float | None
        done: bool
        info: Dict[str, Any] | None = None

    class EnvClient(Generic[ActT, ObsT, StateT]):
        """Small sync fallback client for local HTTP usage."""

        def __init__(self, base_url: str = "http://localhost:8000", **_: Any) -> None:
            self.base_url = base_url.rstrip("/")
            self._session = requests.Session()
            self._session_id: str | None = None

        def __enter__(self) -> "EnvClient[ActT, ObsT, StateT]":
            return self

        def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
            self.close()

        def close(self) -> None:
            self._session.close()

        @property
        def session_id(self) -> str | None:
            return self._session_id

        def _step_payload(self, action: ActT) -> dict[str, Any]:
            raise NotImplementedError

        def _parse_result(self, payload: dict[str, Any]) -> StepResult[ObsT]:
            raise NotImplementedError

        def _parse_state(self, payload: dict[str, Any]) -> StateT:
            raise NotImplementedError

        def reset(self, **kwargs: Any) -> StepResult[ObsT]:
            response = self._session.post(f"{self.base_url}/reset", json=kwargs or {})
            response.raise_for_status()
            payload = response.json()
            self._session_id = payload.get("session_id") or payload.get("episode_id")
            return self._parse_result(payload)

        def step(self, action: ActT, **kwargs: Any) -> StepResult[ObsT]:
            payload = self._step_payload(action)
            if self._session_id and "session_id" not in payload and "episode_id" not in payload:
                payload["session_id"] = self._session_id
            if kwargs:
                payload.update(kwargs)
            response = self._session.post(f"{self.base_url}/step", json=payload)
            response.raise_for_status()
            return self._parse_result(response.json())

        def state(self) -> StateT:
            params = {"session_id": self._session_id} if self._session_id else None
            response = self._session.get(f"{self.base_url}/state", params=params)
            response.raise_for_status()
            return self._parse_state(response.json())

        @classmethod
        def from_docker_image(cls, image: str, **kwargs: Any) -> "EnvClient[ActT, ObsT, StateT]":
            raise NotImplementedError(f"Docker bootstrap requires OpenEnv runtime. Requested image: {image}")

        @classmethod
        def from_hub(cls, repo_id: str, **kwargs: Any) -> "EnvClient[ActT, ObsT, StateT]":
            raise NotImplementedError(f"Hub bootstrap requires OpenEnv runtime. Requested repo: {repo_id}")

    def create_app(
        env_factory: Callable[[], Environment] | type[Environment],
        action_model: type[Action],
        observation_model: type[Observation],
        env_name: str,
    ) -> FastAPI:
        """Fallback FastAPI app with reset, step, state, metadata, and schema endpoints."""

        app = FastAPI(title=env_name)
        sessions: dict[str, Environment] = {}
        latest_session_id: str | None = None
        lock = Lock()

        def _new_env() -> Environment:
            return env_factory() if callable(env_factory) and not isinstance(env_factory, type) else env_factory()  # type: ignore[misc]

        def _resolve_session_id(payload: dict[str, Any] | None = None, query_session_id: str | None = None) -> str | None:
            if query_session_id:
                return query_session_id
            if payload:
                candidate = payload.get("session_id") or payload.get("episode_id")
                if isinstance(candidate, str) and candidate:
                    return candidate
            return latest_session_id

        def _session_env(session_id: str | None) -> Environment:
            if session_id is None:
                raise HTTPException(status_code=400, detail="Missing session_id. Call reset() first or pass session_id explicitly.")
            try:
                return sessions[session_id]
            except KeyError as exc:
                raise HTTPException(
                    status_code=404,
                    detail=f"Unknown session_id '{session_id}'. Call reset() to start a new episode.",
                ) from exc

        @app.get("/health")
        def health() -> dict[str, str]:
            return {"status": "ok", "env": env_name}

        @app.get("/metadata")
        def metadata() -> dict[str, Any]:
            return {
                "name": env_name,
                "action_model": action_model.__name__,
                "observation_model": observation_model.__name__,
            }

        @app.get("/schema")
        def schema() -> dict[str, Any]:
            return {
                "action_schema": action_model.model_json_schema(),
                "observation_schema": observation_model.model_json_schema(),
            }

        @app.post("/reset")
        def reset(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
            nonlocal latest_session_id
            kwargs = payload or {}
            env = _new_env()
            observation = env.reset(**kwargs)
            info = getattr(env, "get_last_info", lambda: {})()
            state = env.state
            session_id = getattr(state, "episode_id", None) or info.get("episode_id") or str(uuid4())

            with lock:
                sessions[session_id] = env
                latest_session_id = session_id

            return {
                "session_id": session_id,
                "observation": observation.model_dump(),
                "reward": observation.reward,
                "done": observation.done,
                "info": info,
            }

        @app.post("/step")
        def step(payload: dict[str, Any]) -> dict[str, Any]:
            session_id = _resolve_session_id(payload=payload)
            env = _session_env(session_id)
            action_payload = dict(payload)
            action_payload.pop("session_id", None)
            action_payload.pop("episode_id", None)
            action = action_model(**action_payload)
            observation = env.step(action)
            info = getattr(env, "get_last_info", lambda: {})()
            return {
                "session_id": session_id,
                "observation": observation.model_dump(),
                "reward": observation.reward,
                "done": observation.done,
                "info": info,
            }

        @app.get("/state")
        def state(session_id: str | None = None) -> dict[str, Any]:
            env = _session_env(_resolve_session_id(query_session_id=session_id))
            current_state = env.state
            return current_state.model_dump() if hasattr(current_state, "model_dump") else dict(current_state)

        return app
