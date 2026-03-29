# ET Multiple Agent

ET Multiple Agent is a multi-step AI content pipeline for generating blogs, reviews, social posts, images, scheduling metadata, and post-approval translations from a single web UI.

The project uses:

- `FastAPI` for the backend API
- `LangGraph` for the generation workflow
- `Groq` for LLM-powered writing, review, and translation
- `Tavily` and `NewsAPI` for news-mode research
- `Bytez` as the preferred image generation provider
- `Stability AI` as an image-generation fallback
- a small `C++` localization engine wrapper plus Groq fallback translation

## Features

- Generate content in two modes:
  - `news`
  - `product`
- Multi-step content pipeline:
  - write
  - validate
  - RAG validation
  - review
  - image generation
  - social post generation
  - human approval loop
  - localization
- Human-in-the-loop approval and refinement
- Translation support after approval
- Social post scheduling endpoints
- Single-page frontend with tabs for:
  - blog
  - review
  - social posts
  - images
  - translations
  - schedule queue

## Project Structure

```text
ETHACKATHON/
|-- agents/                    # Pipeline agents
|-- engine/                    # C++ localization engine source
|-- graph/                     # LangGraph workflow
|-- prompts/                   # Prompt templates
|-- rag/                       # RAG helpers and vector store integration
|-- api_server.py              # FastAPI backend
|-- index.html                 # Frontend UI
|-- config.py                  # Environment-backed config
|-- start.ps1                  # Windows startup script
|-- run.bat                    # Windows launcher
`-- test_graph_state.py        # Direct localization test
```

## Requirements

- Windows
- Python 3.12+ recommended
- A virtual environment at `ETHACKATHON\.venv`

API keys are read from `.env`.

## Environment Variables

Create a `.env` file in the project root with:

```env
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile
TAVILY_API_KEY=your_tavily_key
STABILITY_API_KEY=your_stability_key
BYTEZ_API_KEY=your_bytez_key
BYTEZ_IMAGE_MODEL=stabilityai/stable-diffusion-xl-base-1.0
NEWSAPI_KEY=your_newsapi_key
HF_TOKEN=optional_huggingface_token
```

Notes:

- `GROQ_API_KEY` is required for blog generation, review, and translation.
- `GROQ_MODEL` is optional. If omitted, the app falls back to the default from `config.py`.
- `TAVILY_API_KEY` is used for news research.
- `NEWSAPI_KEY` supports additional news retrieval.
- `BYTEZ_API_KEY` is the preferred key for image generation.
- `BYTEZ_IMAGE_MODEL` is optional and defaults to `stabilityai/stable-diffusion-xl-base-1.0`.
- `STABILITY_API_KEY` is optional fallback support for image generation.
- `HF_TOKEN` is optional in the current codebase.

## Installation

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Running the Project

### Option 1: Recommended

Use the included launcher:

```powershell
.\start.ps1
```

or

```bat
run.bat
```

This starts:

- backend at `http://127.0.0.1:8000`
- frontend at `http://127.0.0.1:5500/index.html`

`start.ps1` now clears stale listeners on ports `8000` and `5500` before launching, which helps avoid old backend/frontend instances hanging around between restarts.

### Option 2: Manual

Start backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api_server:app --host 127.0.0.1 --port 8000
```

Start frontend:

```powershell
.\.venv\Scripts\python.exe -m http.server 5500
```

Then open:

```text
http://127.0.0.1:5500/index.html
```

## Workflow Overview

The backend pipeline is defined in `graph/blog_graph.py`.

Main flow:

1. `write`
2. `validate`
3. `rag_validate`
4. `review`
5. `gen_images`
6. `gen_social`
7. `human_review`
8. `localize` after approval

Important behavior:

- Translation only runs after the user approves the content.
- The frontend sends selected target languages during generate and approval.
- Social image generation reuses already-generated platform images when available instead of regenerating them.
- Image generation runs selected formats in parallel.
- Localization first pings the C++ layer if present, then performs the actual translations through Groq in parallel.

## API Endpoints

### `POST /api/generate`

Starts a new generation job.

Example fields:

- `mode`
- `topic`
- `audience`
- `length`
- `context`
- `product_details`
- `key_features`
- `uvp`
- `generate_images`
- `image_formats`
- `social_platforms`
- `user_image_b64`
- `target_languages`

### `GET /api/status/{job_id}`

Returns the current job state, including:

- generation status
- parsed blog
- review details
- image outputs
- social posts
- `localized_content`

### `POST /api/feedback`

Used for:

- `approve`
- `refine`

When approved, localization is triggered if `target_languages` are present.

### `POST /api/schedule`

Schedules a generated social post.

### `GET /api/queue`

Returns the current scheduled post queue.

### `GET /api/health`

Simple health endpoint.

## Translation Notes

Translation support is implemented through:

- `graph/blog_graph.py`
- `agents/localization_wrapper.py`
- `engine/localization_agent.cpp`

Behavior:

- if no target languages are selected, localization is skipped
- if the content is not approved, localization is skipped
- after approval, translated content is stored under `localized_content`

## Testing

You can directly test the localization path with:

```powershell
.\.venv\Scripts\python.exe test_graph_state.py
```

This exercises `run_localization(...)` directly.

## Common Issues

### Translation not working

Check:

- `.env` exists in the project root
- `GROQ_API_KEY` is valid
- target languages are selected in the UI
- content is approved, not just generated

Notes:

- if `engine/localization_agent.exe` is missing, the app now falls back to Groq-only translation
- translations are generated after approval, not during the first draft pass

### News mode has weak context

Check:

- `TAVILY_API_KEY`
- `NEWSAPI_KEY`

### Images not generated

Check:

- `BYTEZ_API_KEY`
- `STABILITY_API_KEY`
- image generation toggle in the UI

Notes:

- Bytez is the preferred provider
- Stability is only used as fallback
- if Instagram/LinkedIn images were already generated in the image stage, the social stage reuses them for speed

### App starts but frontend cannot connect

Check:

- backend is running on `8000`
- frontend is running on `5500`
- browser is using `http://127.0.0.1:5500/index.html`

## Notes For GitHub

Generated runtime artifacts are intentionally ignored:

- `.env`
- `__pycache__`
- logs
- generated outputs
- local Chroma DB files
- compiled localization executable

This keeps the repository focused on source code.
