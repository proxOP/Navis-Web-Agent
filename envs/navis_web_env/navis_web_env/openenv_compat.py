"""Compatibility helpers for running with or without the OpenEnv runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, TypeVar

import requests
from fastapi import Body, FastAPI
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

        def __enter__(self) -> "EnvClient[ActT, ObsT, StateT]":
            return self

        def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
            self.close()

        def close(self) -> None:
            self._session.close()

        def _step_payload(self, action: ActT) -> dict[str, Any]:
            raise NotImplementedError

        def _parse_result(self, payload: dict[str, Any]) -> StepResult[ObsT]:
            raise NotImplementedError

        def _parse_state(self, payload: dict[str, Any]) -> StateT:
            raise NotImplementedError

        def reset(self, **kwargs: Any) -> StepResult[ObsT]:
            response = self._session.post(f"{self.base_url}/reset", json=kwargs or {})
            response.raise_for_status()
            return self._parse_result(response.json())

        def step(self, action: ActT, **kwargs: Any) -> StepResult[ObsT]:
            payload = self._step_payload(action)
            if kwargs:
                payload.update(kwargs)
            response = self._session.post(f"{self.base_url}/step", json=payload)
            response.raise_for_status()
            return self._parse_result(response.json())

        def state(self) -> StateT:
            response = self._session.get(f"{self.base_url}/state")
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
        env = env_factory() if callable(env_factory) and not isinstance(env_factory, type) else env_factory()  # type: ignore[misc]

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
            kwargs = payload or {}
            observation = env.reset(**kwargs)
            info = getattr(env, "get_last_info", lambda: {})()
            return {
                "observation": observation.model_dump(),
                "reward": observation.reward,
                "done": observation.done,
                "info": info,
            }

        @app.post("/step")
        def step(payload: dict[str, Any]) -> dict[str, Any]:
            action = action_model(**payload)
            observation = env.step(action)
            info = getattr(env, "get_last_info", lambda: {})()
            return {
                "observation": observation.model_dump(),
                "reward": observation.reward,
                "done": observation.done,
                "info": info,
            }

        @app.get("/state")
        def state() -> dict[str, Any]:
            current_state = env.state
            return current_state.model_dump() if hasattr(current_state, "model_dump") else dict(current_state)

        return app
