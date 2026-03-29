"""Baseline inference runner for the Navis OpenEnv hackathon submission."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from envs.navis_web_env.navis_web_env.grading import grade_episode
from envs.navis_web_env.navis_web_env.models import NavisWebAction
from envs.navis_web_env.navis_web_env.server.navis_web_environment import NavisWebEnvironment
from envs.navis_web_env.navis_web_env.site_loader import list_task_ids

OUTPUT_DIR = Path("outputs/evals")
OUTPUT_PATH = OUTPUT_DIR / "baseline.json"


def build_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required.")
    base_url = os.getenv("API_BASE_URL") or None
    return OpenAI(api_key=api_key, base_url=base_url)


def model_name() -> str:
    model = os.getenv("MODEL_NAME")
    if not model:
        raise RuntimeError("MODEL_NAME is required.")
    return model


def prompt_from_observation(observation: Any) -> str:
    link_lines = []
    for link in observation.available_links:
        preview = f" | preview: {link.preview_text}" if link.preview_text else ""
        aria = f" | aria: {link.aria_label}" if link.aria_label else ""
        link_lines.append(f"- {link.link_id}: {link.label} | role: {link.role}{aria}{preview}")

    return "\n".join(
        [
            "You are navigating a deterministic mock website.",
            "Choose exactly one available link id that best helps reach the goal page.",
            "Return strict JSON with this shape only: {\"click_link_id\": \"...\"}",
            f"Goal: {observation.goal_instruction}",
            f"Target page title: {observation.target_page_title}",
            f"Current page title: {observation.page_title}",
            f"Current page text: {observation.page_text}",
            f"Remaining steps: {observation.remaining_steps}",
            "Available links:",
            *link_lines,
        ]
    )


def choose_action(client: OpenAI, model: str, observation: Any) -> str:
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": prompt_from_observation(observation),
            }
        ],
    )
    text = (response.choices[0].message.content or "").strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return "__invalid_json__"
    click_link_id = payload.get("click_link_id")
    return click_link_id if isinstance(click_link_id, str) else "__invalid_json__"


def run_task(client: Any, model: str, task_id: str) -> dict[str, Any]:
    env = NavisWebEnvironment(default_task_id=task_id)
    observation = env.reset(task_id=task_id)

    while not observation.done:
        click_link_id = choose_action(client, model, observation)
        observation = env.step(NavisWebAction(click_link_id=click_link_id))

    summary = env.get_last_info()
    score = grade_episode(summary)
    return {
        "task_id": task_id,
        "score": score,
        "summary": summary,
    }


def main() -> None:
    os.getenv("HF_TOKEN")
    client = build_client()
    model = model_name()

    results = [run_task(client, model, task_id) for task_id in list_task_ids()]
    aggregate = round(sum(result["score"] for result in results) / len(results), 4)

    report = {
        "model": model,
        "tasks": results,
        "aggregate_score": aggregate,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    for result in results:
        print(
            f"{result['task_id']}: score={result['score']} "
            f"steps={result['summary']['actual_steps']} "
            f"invalid={result['summary']['invalid_actions']} "
            f"path={' -> '.join(result['summary']['path'])}"
        )
    print(f"aggregate_score={aggregate}")


if __name__ == "__main__":
    main()
