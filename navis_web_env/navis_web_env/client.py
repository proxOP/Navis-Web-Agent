"""Typed client for the Navis web environment."""

from __future__ import annotations

from typing import Any

from .models import LinkOption, NavisWebAction, NavisWebObservation, NavisWebState
from .openenv_compat import EnvClient, StepResult


class NavisWebEnv(EnvClient[NavisWebAction, NavisWebObservation, NavisWebState]):
    """Client for interacting with the Navis web environment."""

    def _step_payload(self, action: NavisWebAction) -> dict[str, Any]:
        return action.model_dump(exclude_none=True)

    def _parse_result(self, payload: dict[str, Any]) -> StepResult[NavisWebObservation]:
        observation_payload = payload.get("observation", {})
        link_payloads = observation_payload.get("available_links", [])
        observation_payload["available_links"] = [LinkOption(**link_payload) for link_payload in link_payloads]
        observation = NavisWebObservation(**observation_payload)
        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
            info=payload.get("info"),
        )

    def _parse_state(self, payload: dict[str, Any]) -> NavisWebState:
        return NavisWebState(**payload)

    def reset(self, task_id: str | None = None, **kwargs: Any) -> StepResult[NavisWebObservation]:
        if task_id is not None:
            kwargs["task_id"] = task_id
        return super().reset(**kwargs)
