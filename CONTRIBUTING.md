# Contributing to ET-AI Content Engine

Thank you for your interest in contributing! This guide will get you up and running quickly.

---

## Table of Contents
1. [Getting Started](#getting-started)
2. [Project Structure](#project-structure)
3. [Branch Strategy](#branch-strategy)
4. [Making Changes](#making-changes)
5. [Running Tests](#running-tests)
6. [Code Style](#code-style)
7. [Submitting a PR](#submitting-a-pr)
8. [Environment Variables](#environment-variables)

---

## Getting Started

### Prerequisites
- Python 3.11+
- `pip`
- Git
- Docker (optional but recommended)

### Local Setup
```bash
# 1. Clone the repo
git clone https://github.com/Harshit-ops-code/ET-multiple-agent.git
cd ET-multiple-agent

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # Mac/Linux
venv\Scripts\activate          # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Fill in your API keys in .env

# 5. Start the server
uvicorn api_server:app --reload
```
The static frontend is served at `http://localhost:8000/app` once the server is running.

---

## Project Structure

| Folder | Purpose |
| :--- | :--- |
| `agents/` | LangChain-powered pipeline agents (writer, reviewer, etc.) |
| `graph/` | LangGraph workflow state machine |
| `frontend/` | Modular SPA — HTML shell + JS controllers + CSS modules |
| `prompts/` | LLM prompt templates |
| `rag/` | Retrieval-Augmented Generation and ChromaDB config |
| `tests/` | Pytest unit tests |
| `engine/` | C++ parallel translation microservice |

---

## Branch Strategy

| Branch | Purpose |
| :--- | :--- |
| `main` | Stable, deployable code only |
| `dev` | Integration branch for features |
| `fix/...` | Bug fixes (e.g. `fix/cors-issue`) |
| `feat/...` | New features (e.g. `feat/twitter-agent`) |
| `chore/...` | Config, deps, tooling changes |

> [!IMPORTANT]
> Never push directly to `main`. Always open a Pull Request.

---

## Making Changes
```bash
# Always branch off main
git checkout main
git pull origin main
git checkout -b feat/your-feature-name

# Make your changes, then stage and commit
git add .
git commit -m "feat: describe what you did"

# Push your branch
git push origin feat/your-feature-name
```
Then open a Pull Request on GitHub targeting `main`.

---

## Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_parser.py -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=. --cov-report=term-missing
```

---

## Code Style

This project uses Ruff for linting.
```bash
# Install
pip install ruff

# Check
ruff check .

# Auto-fix
ruff check . --fix
```

Rules followed:
- Max line length: 100 characters
- No unused imports
- No bare `except` clauses
- Use `logging` — never `print()` in production code

---

## Submitting a PR

Before opening a PR, make sure:
- [ ] All tests pass (`pytest tests/`)
- [ ] Ruff linting passes (`ruff check .`)
- [ ] You have not committed `.env` or any API keys
- [ ] New features have at least one test in `tests/`
- [ ] You've updated `README.md` if behavior changed

PR title format:
```text
feat: add Twitter scheduling agent
fix: resolve CORS error on deployment
chore: update dependencies
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your keys. Never commit `.env`.

| Variable | Required | Description |
| :--- | :---: | :--- |
| `GROQ_API_KEY` | ✅ | LLM inference via Groq |
| `TAVILY_API_KEY` | ✅ | Web search agent |
| `NEWSAPI_KEY` | ✅ | News crawler |
| `STABILITY_API_KEY` | ✅ | Image generation |
| `BYTEZ_API_KEY` | ✅ | Bytez image model |
| `ALLOWED_ORIGINS` | ✅ | Comma-separated frontend origins |
| `GROQ_MODEL` | ❌ | Defaults to `llama-3.1-8b-instant` |
| `BYTEZ_IMAGE_MODEL` | ❌ | Defaults to SDXL base |

---

## Questions?

Open a GitHub Issue and tag it with `question`.
