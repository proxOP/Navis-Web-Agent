# Navis Chrome Extension

**Don't just browse. Arrive.**

Navis is a voice-driven AI navigation agent implemented as a Chrome extension with a lightweight Python backend. The current backend is intentionally minimal and focused on simple action selection from page elements.

## Overview

- Intent parsing uses OpenAI when configured, with a local heuristic fallback for development.
- Semantic scoring ranks DOM elements using text, element type, context, and interactivity.
- Selection logic decides whether an action can be recommended directly or should require confirmation.
- Session and feedback data are stored in memory to keep the stack simple.
- The backend is organized into `api`, `domain`, `repositories`, and `services`.

## Setup

1. Create and activate a Python virtual environment.
2. Install backend dependencies:

```bash
pip install -r navis-backend/requirements.txt
```

3. Copy `.env.template` to `.env` and set any API keys you want to use.
4. Start the backend:

```bash
cd navis-backend
python main.py
```

5. Test the backend:

```bash
python test_backend.py
```

6. Load the Chrome extension from the `extension/` directory in `chrome://extensions/`.

## Project Structure

```text
Navis-Chrome-Extension/
├── spec/                  # Project specifications
├── navis-backend/         # Python backend
│   ├── api/               # Request schemas
│   ├── domain/            # Core domain models
│   ├── repositories/      # In-memory storage
│   ├── services/          # Intent parsing, scoring, policy, orchestration
│   └── main.py            # FastAPI server
├── extension/             # Chrome extension
├── tests/                 # Test suite
└── test_backend.py        # Backend health test
```

## Backend Capabilities

- Intent parsing endpoint
- Semantic analysis endpoint
- Session creation and lookup endpoints
- Feedback recording endpoint
- End-to-end goal analysis endpoint for simple action recommendation
- Health endpoint

## Testing

Run the unit tests with:

```bash
pytest tests/ -v
```
