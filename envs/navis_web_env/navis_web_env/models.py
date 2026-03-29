"""Typed models for the Navis web wayfinding environment."""

from __future__ import annotations

from typing import Dict, List

from pydantic import Field

from .openenv_compat import Action, Observation, State


class LinkOption(Observation):
    """DOM-lite representation of a click target."""

    link_id: str = Field(..., description="Stable action identifier for the link.")
    label: str = Field(..., description="Visible link text.")
    role: str = Field(default="link", description="Accessibility role for the target.")
    aria_label: str | None = Field(default=None, description="Optional aria-label value.")
    preview_text: str | None = Field(default=None, description="Short preview of what the link leads to.")
    done: bool = Field(default=False, exclude=True)
    reward: float | None = Field(default=None, exclude=True)


class NavisWebAction(Action):
    """The single allowed agent action."""

    click_link_id: str = Field(..., description="Link identifier to click from the current page.")
    reason: str | None = Field(default=None, description="Optional agent rationale for debugging and logs.")


class NavisWebObservation(Observation):
    """Observation emitted after each environment transition."""

    page_id: str = Field(..., description="Identifier of the current page.")
    page_title: str = Field(..., description="Title of the current page.")
    page_text: str = Field(..., description="Main text content for the page.")
    available_links: List[LinkOption] = Field(default_factory=list, description="Links that can be clicked next.")
    target_page_title: str = Field(..., description="Title of the goal page.")
    goal_instruction: str = Field(..., description="Natural-language description of the task.")
    remaining_steps: int = Field(..., description="Number of steps left before termination.")
    visited_count: int = Field(..., description="Count of visited pages in the episode history.")


class NavisWebState(State):
    """Extended state export for evaluation and debugging."""

    task_id: str = Field(..., description="Current task identifier.")
    current_page_id: str = Field(..., description="Current page identifier.")
    target_page_id: str = Field(..., description="Target page identifier.")
    visited_pages: List[str] = Field(default_factory=list, description="Ordered page visit history.")
    visited_counts: Dict[str, int] = Field(default_factory=dict, description="Visit counts by page id.")
    shortest_distance_to_target: int = Field(..., description="Shortest-path distance from current page to target.")
    max_steps: int = Field(..., description="Episode step limit.")
    last_action_valid: bool = Field(default=True, description="Whether the last action was valid.")
    termination_reason: str | None = Field(default=None, description="Why the episode ended, if ended.")
