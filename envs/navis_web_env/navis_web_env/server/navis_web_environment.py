"""Environment logic for deterministic mock website navigation."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict
from uuid import uuid4

from ..grading import grade_episode
from ..models import LinkOption, NavisWebAction, NavisWebObservation, NavisWebState
from ..openenv_compat import Environment
from ..site_loader import TaskDefinition, load_task, optimal_path_budget, shortest_path_length


class NavisWebEnvironment(Environment):
    """Deterministic graph-navigation environment with DOM-lite observations."""

    def __init__(self, default_task_id: str = "easy") -> None:
        self._default_task_id = default_task_id
        self._task = load_task(default_task_id)
        self._state = self._build_state(self._task)
        self._last_info: Dict[str, Any] = {}
        self._invalid_actions = 0
        self._repeat_visits = 0
        self._optimal_steps = optimal_path_budget(self._task)

    def reset(self, task_id: str | None = None, **_: Any) -> NavisWebObservation:
        if task_id is None:
            task_id = self._default_task_id
        self._task = load_task(task_id)
        self._invalid_actions = 0
        self._repeat_visits = 0
        self._optimal_steps = optimal_path_budget(self._task)
        self._state = self._build_state(self._task)
        self._last_info = self._episode_summary(reached_target=False)
        self._last_info["termination_reason"] = None
        return self._current_observation(reward=0.0, done=False)

    def step(self, action: NavisWebAction, **_: Any) -> NavisWebObservation:
        if self._state.termination_reason is not None:
            self._last_info = self._episode_summary(reached_target=self._state.current_page_id == self._state.target_page_id)
            return self._current_observation(reward=0.0, done=True)

        page = self._task.pages[self._state.current_page_id]
        links_by_id = {link.link_id: link for link in page.links}
        previous_distance = self._state.shortest_distance_to_target
        reward = -0.05
        action_valid = action.click_link_id in links_by_id
        reached_target = False

        self._state.step_count += 1
        self._state.last_action_valid = action_valid

        if not action_valid:
            reward -= 0.20
            self._invalid_actions += 1
        else:
            link = links_by_id[action.click_link_id]
            next_page_id = link.destination_page_id
            already_seen = next_page_id in self._state.visited_counts
            self._state.current_page_id = next_page_id
            self._state.visited_pages.append(next_page_id)
            self._state.visited_counts[next_page_id] = self._state.visited_counts.get(next_page_id, 0) + 1
            self._state.shortest_distance_to_target = shortest_path_length(self._task, next_page_id)

            if self._state.shortest_distance_to_target < previous_distance:
                reward += 0.15

            if already_seen:
                reward -= 0.10
                self._repeat_visits += 1

            if self._state.shortest_distance_to_target > previous_distance and self._state.visited_counts[next_page_id] >= 2:
                reward -= 0.15

            if self._state.current_page_id == self._state.target_page_id:
                reward += 1.0
                reached_target = True

        done = False
        termination_reason: str | None = None

        if reached_target:
            done = True
            termination_reason = "target_reached"
        elif self._state.step_count >= self._state.max_steps:
            done = True
            termination_reason = "max_steps_exceeded"
        elif any(count > 3 for count in self._state.visited_counts.values()):
            reward -= 0.15
            done = True
            termination_reason = "loop_cap_exceeded"

        self._state.termination_reason = termination_reason
        reward = max(-0.5, min(1.0, reward))
        self._last_info = self._episode_summary(reached_target=reached_target)
        self._last_info["grade"] = grade_episode(self._last_info)
        observation = self._current_observation(reward=reward, done=done)
        return observation

    @property
    def state(self) -> NavisWebState:
        return self._state

    def get_last_info(self) -> Dict[str, Any]:
        return dict(self._last_info)

    def _build_state(self, task: TaskDefinition) -> NavisWebState:
        visited_pages = [task.start_page_id]
        visited_counts = {task.start_page_id: 1}
        return NavisWebState(
            episode_id=str(uuid4()),
            step_count=0,
            task_id=task.task_id,
            current_page_id=task.start_page_id,
            target_page_id=task.target_page_id,
            visited_pages=visited_pages,
            visited_counts=visited_counts,
            shortest_distance_to_target=shortest_path_length(task, task.start_page_id),
            max_steps=task.max_steps,
            last_action_valid=True,
            termination_reason=None,
        )

    def _current_observation(self, reward: float | None, done: bool) -> NavisWebObservation:
        page = self._task.pages[self._state.current_page_id]
        return NavisWebObservation(
            page_id=page.page_id,
            page_title=page.title,
            page_text=page.text,
            available_links=[
                LinkOption(
                    link_id=link.link_id,
                    label=link.label,
                    role=link.role,
                    aria_label=link.aria_label,
                    preview_text=link.preview_text,
                )
                for link in page.links
            ],
            target_page_title=self._task.target_page.title,
            goal_instruction=self._task.goal_instruction,
            remaining_steps=max(self._state.max_steps - self._state.step_count, 0),
            visited_count=len(self._state.visited_pages),
            done=done,
            reward=reward,
        )

    def _episode_summary(self, reached_target: bool) -> Dict[str, Any]:
        return {
            "task_id": self._task.task_id,
            "reached_target": reached_target,
            "actual_steps": self._state.step_count,
            "optimal_steps": self._optimal_steps,
            "invalid_actions": self._invalid_actions,
            "repeat_visits": self._repeat_visits,
            "termination_reason": self._state.termination_reason,
            "path": list(self._state.visited_pages),
            "visited_histogram": dict(Counter(self._state.visited_pages)),
        }
