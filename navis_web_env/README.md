# Navis Web Env

Navis Web Env is a deterministic OpenEnv environment for training and evaluating web-navigation agents on a realistic but fully controlled task: moving through mock websites to reach a target page.

## Why This Environment Exists

Real browser environments are powerful, but they are also brittle for a hackathon setting. Live sites change, break, rate-limit, and introduce nondeterminism. This environment keeps the task realistic while removing that instability:

- The agent still solves a real task humans do: website wayfinding.
- Pages contain natural-language content and browser-like links.
- Each task is deterministic, reproducible, and easy to grade.
- Reward shaping gives signal across the full trajectory instead of only at the end.

## Environment Design

Each task is a mock site represented as a directed graph of pages:

- A page has a `title`, `text`, and ordered outgoing links.
- Each link includes DOM-lite metadata such as `label`, `role`, `aria_label`, and `preview_text`.
- The agent starts on a fixed page and must reach a fixed target page.

### Action Space

The action space is intentionally narrow:

- `NavisWebAction(click_link_id: str, reason: str | None = None)`

The only valid action is clicking one of the presented links.

### Observation Space

Each observation includes:

- `page_id`
- `page_title`
- `page_text`
- `available_links`
- `target_page_title`
- `goal_instruction`
- `remaining_steps`
- `visited_count`
- `done`
- `reward`

### State

The exported state includes the OpenEnv base metadata plus environment-specific details:

- current task id
- current page id
- target page id
- visit history
- visit counts per page
- shortest-path distance to target
- max steps
- action validity
- termination reason

## Tasks

The environment ships with 3 deterministic tasks:

- `easy`: 2-3 clicks with light distraction and no meaningful loops
- `medium`: 4-6 clicks with semantically plausible detours
- `hard`: 6-9 clicks with loops, repeated terminology, and near-target decoys

The tasks are defined under [`navis_web_env/sites`](./navis_web_env/sites).

## Reward Shaping

Reward is dense and trajectory-aware:

- `+1.0` for reaching the target page
- `+0.15` for strictly reducing shortest-path distance
- `0.0` bonus when a valid action leaves distance unchanged
- `-0.05` per step
- `-0.10` for revisiting a page
- `-0.20` for invalid link ids
- `-0.15` extra penalty for tight loops or repeated moves that increase distance

Episodes terminate on:

- success when the target is reached
- failure when max steps are exhausted
- failure when any page is visited more than 3 times

## Graders

Task graders are deterministic project-level functions. They score the final episode summary on `[0.0, 1.0]`:

- `1.0` for an optimal successful route
- `0.7-1.0` for successful but inefficient routes
- `0.0` for failure

Grader-facing episode summaries include:

- `task_id`
- `reached_target`
- `actual_steps`
- `optimal_steps`
- `invalid_actions`
- `repeat_visits`
- `termination_reason`

## Local Development

Install dependencies:

```bash
cd envs/navis_web_env
pip install -e .
```

If you only need the optional Google baseline dependency, install:

```bash
pip install -U google-genai
```

Run the server locally:

```bash
uv run --project . server --host 0.0.0.0 --port 8000
```

Or with uvicorn:

```bash
cd envs/navis_web_env
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

For the fallback plain-HTTP path, `POST /reset` now returns a `session_id`. Subsequent `POST /step` and `GET /state` calls should include that `session_id` so episode state is preserved even when requests are handled independently.

## OpenEnv Validation

From the environment directory:

```bash
cd envs/navis_web_env
openenv validate --verbose
```

If `openenv` is not installed yet, install the runtime first:

```bash
pip install "openenv-core[core]"
```

## Docker

Build:

```bash
cd envs/navis_web_env
openenv build
```

Run directly with Docker:

```bash
docker build -f server/Dockerfile -t navis-web-env .
docker run -p 8000:8000 navis-web-env
```

## Baseline Inference

The hackathon baseline script is at the repo root as [`inference.py`](../../inference.py). It supports two agent modes:

- `heuristic` (default): no LLM calls, uses token overlap / semantic similarity between the goal and available links
- `google_genai`: uses `google-genai` with `genai.Client(api_key=...)`

Environment variables:

- `BASELINE_AGENT=heuristic` or `BASELINE_AGENT=google_genai`
- `MODEL_NAME` only needed for `google_genai`
- `GOOGLE_GENAI_API_KEY` only needed for `google_genai`
- `HF_TOKEN` optional for submission workflows

Example heuristic run:

```bash
set BASELINE_AGENT=heuristic
python inference.py
```

Example Google GenAI run:

```bash
set BASELINE_AGENT=google_genai
set GOOGLE_GENAI_API_KEY=...
set MODEL_NAME=gemini-2.0-flash
python inference.py
```

Both modes run all 3 tasks in fixed order and save a reproducible report to `outputs/evals/baseline.json`.

## Expected Baseline Outputs

The exact score depends on the selected agent mode and model, but the output report includes:

- per-task score
- path taken
- invalid action count
- repeat visits
- aggregate mean score

## Hugging Face Spaces Deployment

This environment is designed to deploy as a Docker-backed HF Space tagged `openenv`:

1. Validate locally with `openenv validate --verbose`
2. Push with `openenv push`
3. Ensure the Space returns healthy responses for `/health`, reset, step, state, metadata, and schema

Because the environment is fully self-contained, deployment does not require access to live websites or external page content.
