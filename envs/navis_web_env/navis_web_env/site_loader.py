"""Static task and site loading utilities."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class LinkDefinition:
    link_id: str
    label: str
    href_slug: str
    role: str
    aria_label: str | None
    preview_text: str | None
    destination_page_id: str


@dataclass(frozen=True)
class PageDefinition:
    page_id: str
    title: str
    text: str
    links: List[LinkDefinition]


@dataclass(frozen=True)
class TaskDefinition:
    task_id: str
    goal_instruction: str
    start_page_id: str
    target_page_id: str
    max_steps: int
    pages: Dict[str, PageDefinition]
    distractor_taxonomy: List[str]

    @property
    def target_page(self) -> PageDefinition:
        return self.pages[self.target_page_id]


SITES_DIR = Path(__file__).resolve().parent / "sites"
TASK_FILE_MAP = {
    "easy": SITES_DIR / "site_easy.json",
    "medium": SITES_DIR / "site_medium.json",
    "hard": SITES_DIR / "site_hard.json",
}


def list_task_ids() -> list[str]:
    return list(TASK_FILE_MAP.keys())


def load_task(task_id: str) -> TaskDefinition:
    if task_id not in TASK_FILE_MAP:
        raise ValueError(f"Unknown task_id '{task_id}'. Expected one of: {', '.join(list_task_ids())}")
    payload = json.loads(TASK_FILE_MAP[task_id].read_text(encoding="utf-8-sig"))
    pages = {
        page_id: PageDefinition(
            page_id=page_id,
            title=page["title"],
            text=page["text"],
            links=[
                LinkDefinition(
                    link_id=link["link_id"],
                    label=link["label"],
                    href_slug=link["href_slug"],
                    role=link.get("role", "link"),
                    aria_label=link.get("aria_label"),
                    preview_text=link.get("preview_text"),
                    destination_page_id=link["destination_page_id"],
                )
                for link in page.get("links", [])
            ],
        )
        for page_id, page in payload["pages"].items()
    }
    return TaskDefinition(
        task_id=payload["task_id"],
        goal_instruction=payload["goal_instruction"],
        start_page_id=payload["start_page_id"],
        target_page_id=payload["target_page_id"],
        max_steps=payload["max_steps"],
        pages=pages,
        distractor_taxonomy=payload.get("distractor_taxonomy", []),
    )


def shortest_path_length(task: TaskDefinition, start_page_id: str, target_page_id: str | None = None) -> int:
    target = target_page_id or task.target_page_id
    if start_page_id == target:
        return 0
    queue: deque[tuple[str, int]] = deque([(start_page_id, 0)])
    seen = {start_page_id}
    while queue:
        current, distance = queue.popleft()
        for link in task.pages[current].links:
            next_page = link.destination_page_id
            if next_page == target:
                return distance + 1
            if next_page not in seen:
                seen.add(next_page)
                queue.append((next_page, distance + 1))
    return 999


def optimal_path_budget(task: TaskDefinition) -> int:
    return shortest_path_length(task, task.start_page_id, task.target_page_id)


def serialize_links(links: Iterable[LinkDefinition]) -> list[dict[str, str | None]]:
    return [
        {
            "link_id": link.link_id,
            "label": link.label,
            "role": link.role,
            "aria_label": link.aria_label,
            "preview_text": link.preview_text,
        }
        for link in links
    ]
