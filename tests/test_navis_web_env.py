"""Tests for the Navis deterministic web environment."""

from __future__ import annotations

import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from envs.navis_web_env.navis_web_env.grading import grade_episode
from envs.navis_web_env.navis_web_env.models import NavisWebAction
from envs.navis_web_env.navis_web_env.server.navis_web_environment import NavisWebEnvironment


def test_reset_returns_expected_initial_observation_for_each_task():
    env = NavisWebEnvironment()
    for task_id in ("easy", "medium", "hard"):
        observation = env.reset(task_id=task_id)
        assert observation.page_id
        assert observation.goal_instruction
        assert observation.target_page_title
        assert observation.remaining_steps > 0
        assert observation.visited_count == 1


def test_step_follows_valid_edge():
    env = NavisWebEnvironment(default_task_id="easy")
    observation = env.reset(task_id="easy")
    next_observation = env.step(NavisWebAction(click_link_id="home_support"))
    assert observation.page_id == "home"
    assert next_observation.page_id == "support_center"


def test_invalid_link_does_not_move_and_penalizes():
    env = NavisWebEnvironment(default_task_id="easy")
    env.reset(task_id="easy")
    observation = env.step(NavisWebAction(click_link_id="missing_link"))
    assert observation.page_id == "home"
    assert observation.reward == -0.25
    assert env.state.last_action_valid is False


def test_progress_reward_is_higher_when_distance_decreases():
    env = NavisWebEnvironment(default_task_id="medium")
    env.reset(task_id="medium")
    better = env.step(NavisWebAction(click_link_id="landing_students"))

    env.reset(task_id="medium")
    worse = env.step(NavisWebAction(click_link_id="landing_campus"))

    assert better.reward > worse.reward


def test_repeat_visits_penalize_deterministically():
    env = NavisWebEnvironment(default_task_id="easy")
    env.reset(task_id="easy")
    env.step(NavisWebAction(click_link_id="home_support"))
    back_home = env.step(NavisWebAction(click_link_id="support_home"))
    repeated_support = env.step(NavisWebAction(click_link_id="home_support"))

    assert back_home.reward <= 0.0
    assert repeated_support.reward < 0.0
    assert env.get_last_info()["repeat_visits"] >= 2


def test_reaching_target_sets_done_and_success_reward():
    env = NavisWebEnvironment(default_task_id="easy")
    env.reset(task_id="easy")
    env.step(NavisWebAction(click_link_id="home_support"))
    observation = env.step(NavisWebAction(click_link_id="support_contact"))

    assert observation.done is True
    assert observation.page_id == "contact_support"
    assert observation.reward == 1.0
    assert env.get_last_info()["termination_reason"] == "target_reached"


def test_max_step_termination_works():
    env = NavisWebEnvironment(default_task_id="easy")
    env.reset(task_id="easy")
    for _ in range(5):
        observation = env.step(NavisWebAction(click_link_id="home_pricing" if env.state.current_page_id == "home" else "pricing_home"))
    assert observation.done is True
    assert env.get_last_info()["termination_reason"] in {"max_steps_exceeded", "loop_cap_exceeded"}


def test_grader_returns_valid_range_and_prefers_efficient_success():
    optimal = {
        "reached_target": True,
        "actual_steps": 2,
        "optimal_steps": 2,
    }
    inefficient = {
        "reached_target": True,
        "actual_steps": 4,
        "optimal_steps": 2,
    }
    failure = {
        "reached_target": False,
        "actual_steps": 8,
        "optimal_steps": 2,
    }

    optimal_score = grade_episode(optimal)
    inefficient_score = grade_episode(inefficient)
    failure_score = grade_episode(failure)

    assert 0.0 <= optimal_score <= 1.0
    assert 0.0 <= inefficient_score <= 1.0
    assert optimal_score > inefficient_score
    assert failure_score == 0.0
