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
    env = NavisWebEnvironment(default_task_id="easy")
    env.reset(task_id="easy")

    observation = None
    for link_id in ["home_support", "support_home", "home_support", "support_home", "home_support", "support_home"]:
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
    assert shortest_path_length(medium, medium.start_page_id) == 3
    assert shortest_path_length(hard, hard.start_page_id) == 5


def test_http_endpoints_expose_health_schema_and_state():
    client = TestClient(app)

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json()["status"] == "ok"

    schema_response = client.get("/schema")
    assert schema_response.status_code == 200
    schema_payload = schema_response.json()
    assert "action_schema" in schema_payload
    assert "observation_schema" in schema_payload

    reset_response = client.post("/reset", json={"task_id": "easy"})
    assert reset_response.status_code == 200
    reset_payload = reset_response.json()
    assert reset_payload["observation"]["page_id"] == "home"
    assert reset_payload["done"] is False

    state_response = client.get("/state")
    assert state_response.status_code == 200
    state_payload = state_response.json()
    assert state_payload["task_id"] == "easy"
    assert state_payload["current_page_id"] == "home"


def test_http_step_returns_info_summary_on_success():
    client = TestClient(app)
    client.post("/reset", json={"task_id": "easy"})
    client.post("/step", json={"click_link_id": "home_support"})
    step_response = client.post("/step", json={"click_link_id": "support_contact"})

    assert step_response.status_code == 200
    payload = step_response.json()
    assert payload["done"] is True
    assert payload["observation"]["page_id"] == "contact_support"
    assert payload["info"]["reached_target"] is True
    assert payload["info"]["grade"] == 1.0
