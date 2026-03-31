"""Baseline inference runner for the Navis OpenEnv hackathon submission."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from envs.navis_web_env.navis_web_env.grading import grade_episode
from envs.navis_web_env.navis_web_env.models import NavisWebAction
from envs.navis_web_env.navis_web_env.server.navis_web_environment import NavisWebEnvironment
from envs.navis_web_env.navis_web_env.site_loader import list_task_ids

load_dotenv()

OUTPUT_DIR = Path("outputs/evals")
OUTPUT_PATH = OUTPUT_DIR / "baseline.json"
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "i", "in", "into",
    "is", "it", "of", "on", "or", "page", "reach", "site", "that", "the", "this", "to", "you", "your"
}


def agent_mode() -> str:
    return os.getenv("BASELINE_AGENT", "heuristic").strip().lower()


def google_genai_api_key() -> str:
    api_key = os.getenv("GOOGLE_GENAI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_GENAI_API_KEY is required for BASELINE_AGENT=google_genai.")
    return api_key


def model_name() -> str:
    model = os.getenv("MODEL_NAME")
    if not model:
        raise RuntimeError("MODEL_NAME is required.")
    return model


def build_client() -> Any:
    try:
        from google import genai
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise RuntimeError(
            "google-genai is required for BASELINE_AGENT=google_genai. Install it with `pip install -U google-genai`."
        ) from exc

    return genai.Client(api_key=google_genai_api_key())


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


def _extract_response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    candidates = getattr(response, "candidates", None) or []
    parts: list[str] = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if content is None:
            continue
        for part in getattr(content, "parts", []) or []:
            part_text = getattr(part, "text", None)
            if part_text:
                parts.append(part_text)
    return "".join(parts).strip()


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOPWORDS and len(token) > 1}


def choose_action_with_llm(client: Any, model: str, observation: Any) -> str:
    response = client.models.generate_content(model=model, contents=prompt_from_observation(observation))
    text = _extract_response_text(response)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return "__invalid_json__"
    click_link_id = payload.get("click_link_id")
    return click_link_id if isinstance(click_link_id, str) else "__invalid_json__"


def choose_action_with_heuristic(observation: Any) -> str:
    goal_tokens = _tokenize(observation.goal_instruction)
    target_tokens = _tokenize(observation.target_page_title)
    page_tokens = _tokenize(observation.page_title + " " + observation.page_text)
    query_tokens = goal_tokens | target_tokens

    best_link_id = observation.available_links[0].link_id if observation.available_links else "__invalid_json__"
    best_score = float("-inf")

    for index, link in enumerate(observation.available_links):
        link_text = " ".join(
            part for part in [link.label, link.aria_label or "", link.preview_text or ""] if part
        )
        link_tokens = _tokenize(link_text)

        overlap_score = len(query_tokens & link_tokens) * 3
        target_overlap = len(target_tokens & link_tokens) * 5
        support_bonus = 2 if "support" in query_tokens and "support" in link_tokens else 0
        page_novelty = len((query_tokens - page_tokens) & link_tokens)
        total_score = overlap_score + target_overlap + support_bonus + page_novelty - (index * 0.01)

        if total_score > best_score:
            best_score = total_score
            best_link_id = link.link_id

    return best_link_id


def choose_action(agent: Any, model: str | None, observation: Any, mode: str) -> str:
    if mode == "heuristic":
        return choose_action_with_heuristic(observation)
    if mode == "google_genai":
        if agent is None or model is None:
            return "__invalid_json__"
        return choose_action_with_llm(agent, model, observation)
    raise ValueError(f"Unsupported BASELINE_AGENT '{mode}'. Expected 'heuristic' or 'google_genai'.")


def run_task(agent: Any, model: str | None, task_id: str, mode: str | None = None) -> dict[str, Any]:
    selected_mode = mode or agent_mode()
    env = NavisWebEnvironment(default_task_id=task_id)
    observation = env.reset(task_id=task_id)

    while not observation.done:
        click_link_id = choose_action(agent, model, observation, selected_mode)
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
    selected_mode = agent_mode()
    selected_model = model_name() if selected_mode == "google_genai" else "heuristic-semantic-baseline"
    agent = build_client() if selected_mode == "google_genai" else None

    results = [run_task(agent, selected_model if selected_mode == "google_genai" else None, task_id, mode=selected_mode) for task_id in list_task_ids()]
    aggregate = round(sum(result["score"] for result in results) / len(results), 4)

    report = {
        "agent_mode": selected_mode,
        "model": selected_model,
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
    print(f"agent_mode={selected_mode}")
    print(f"aggregate_score={aggregate}")


if __name__ == "__main__":
    main()
