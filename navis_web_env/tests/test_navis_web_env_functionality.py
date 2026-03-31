"""Additional functionality tests for the Navis web environment."""

from __future__ import annotations

import os
import sys

from fastapi.testclient import TestClient

ROOT = os.path.join(os.path.dirname(__file__), "..")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from envs.navis_web_env.navis_web_env.server.app import app
from envs.navis_web_env.navis_web_env.server.navis_web_environment import NavisWebEnvironment
from envs.navis_web_env.navis_web_env.site_loader import list_task_ids, shortest_path_length, load_task


def _post_step(client: TestClient, click_link_id: str):
    response = client.post("/step", json={"click_link_id": click_link_id})
    if response.status_code == 422:
        response = client.post("/step", json={"action": {"click_link_id": click_link_id}})
    return response


def _unwrap_observation_payload(payload: dict):
    if "observation" in payload:
        return payload["observation"]
    if "result" in payload and isinstance(payload["result"], dict) and "observation" in payload["result"]:
        return payload["result"]["observation"]
    return payload


def _unwrap_info_payload(payload: dict):
    if "info" in payload and isinstance(payload["info"], dict):
        return payload["info"]
    if "result" in payload and isinstance(payload["result"], dict):
        result = payload["result"]
        if "info" in result and isinstance(result["info"], dict):
            return result["info"]
    return {}


def _looks_like_state(payload: dict) -> bool:
    return any(key in payload for key in ("task_id", "current_page_id", "page_id", "visited_pages", "step_count"))


def test_state_tracks_task_metadata_after_reset():
    env = NavisWebEnvironment(default_task_id="hard")
    env.reset(task_id="hard")

    state = env.state
    assert state.task_id == "hard"
    assert state.current_page_id == "dashboard"
    assert state.target_page_id == "emergency_access_reset_playbook"
    assert state.visited_pages == ["dashboard"]
    assert state.visited_counts == {"dashboard": 1}
    assert state.shortest_distance_to_target == 5


def test_state_updates_after_valid_transition():
    env = NavisWebEnvironment(default_task_id="easy")
    env.reset(task_id="easy")
    env.step(action=type("Action", (), {"click_link_id": "home_support"})())

    state = env.state
    assert state.step_count == 1
    assert state.current_page_id == "support_center"
    assert state.visited_pages == ["home", "support_center"]
    assert state.visited_counts["support_center"] == 1
    assert state.last_action_valid is True
    assert state.shortest_distance_to_target == 1


def test_loop_cap_termination_sets_reason_and_penalty():
    env = NavisWebEnvironment(default_task_id="hard")
    env.reset(task_id="hard")

    observation = None
    for link_id in [
        "dash_remote_work",
        "remote_dashboard",
        "dash_remote_work",
        "remote_dashboard",
        "dash_remote_work",
        "remote_dashboard",
    ]:
        observation = env.step(action=type("Action", (), {"click_link_id": link_id})())
        if observation.done:
            break

    assert observation is not None
    assert observation.done is True
    assert env.state.termination_reason == "loop_cap_exceeded"
    assert env.get_last_info()["termination_reason"] == "loop_cap_exceeded"


def test_task_catalog_and_shortest_paths_are_deterministic():
    assert list_task_ids() == ["easy", "medium", "hard"]

    easy = load_task("easy")
    medium = load_task("medium")
    hard = load_task("hard")

    assert shortest_path_length(easy, easy.start_page_id) == 2
    assert shortest_path_length(medium, medium.start_page_id) == 4
    assert shortest_path_length(hard, hard.start_page_id) == 5


def test_http_endpoints_expose_health_schema_and_state():
    client = TestClient(app)

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json()["status"] in {"ok", "healthy"}

    schema_response = client.get("/schema")
    assert schema_response.status_code == 200
    schema_payload = schema_response.json()
    assert ("action_schema" in schema_payload and "observation_schema" in schema_payload) or (
        "action" in schema_payload and "observation" in schema_payload
    )

    reset_response = client.post("/reset", json={"task_id": "easy"})
    assert reset_response.status_code == 200
    reset_payload = reset_response.json()
    observation_payload = _unwrap_observation_payload(reset_payload)
    assert observation_payload["page_id"] == "home"

    state_response = client.get("/state")
    assert state_response.status_code == 200
    state_payload = state_response.json()
    assert isinstance(state_payload, dict)
    assert _looks_like_state(state_payload)


def test_http_step_returns_info_summary_on_success():
    client = TestClient(app)
    reset_response = client.post("/reset", json={"task_id": "easy"})
    session_id = reset_response.json().get("session_id")
    step_response = _post_step(client, "home_support")

    assert step_response.status_code == 200
    payload = step_response.json()
    observation_payload = _unwrap_observation_payload(payload)
    info_payload = _unwrap_info_payload(payload)
    assert payload.get("session_id") == session_id
    assert observation_payload["page_id"] in {"support_center", "contact_support"}
    if info_payload:
        assert "grade" in info_payload or "reached_target" in info_payload or "task_id" in info_payload


def test_http_session_id_persists_state_across_steps():
    client = TestClient(app)

    reset_response = client.post("/reset", json={"task_id": "easy"})
    assert reset_response.status_code == 200
    session_id = reset_response.json()["session_id"]

    first_step = client.post("/step", json={"session_id": session_id, "click_link_id": "home_support"})
    assert first_step.status_code == 200
    first_payload = first_step.json()
    assert first_payload["session_id"] == session_id
    assert _unwrap_observation_payload(first_payload)["page_id"] == "support_center"

    second_step = client.post("/step", json={"session_id": session_id, "click_link_id": "support_contact"})
    assert second_step.status_code == 200
    second_payload = second_step.json()
    second_observation = _unwrap_observation_payload(second_payload)
    assert second_observation["page_id"] == "contact_support"
    assert second_observation["done"] is True

    state_response = client.get("/state", params={"session_id": session_id})
    assert state_response.status_code == 200
    assert state_response.json()["step_count"] == 2
