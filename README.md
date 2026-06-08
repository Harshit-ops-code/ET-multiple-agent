# ET Multiple Agent

ET Multiple Agent is a multi-step AI content pipeline for generating articles, compliance audits, social media posts, AI-generated images, and post-approval parallel translations from a single modular web interface.

The project uses:

- **FastAPI** for the backend API and static page serving
- **LangGraph** for multi-agent state orchestration
- **Groq** for high-speed LLM-powered writing, review, and translations
- **Tavily** and **NewsAPI** for deep web research in news mode
- **Stability AI** / **Bytez** for parallel image generation
- A parallel **C++** localization microservice engine

---

## Features

- **Dual-Mode Writing:** News Blog (with web crawler search context) and Product Launch modes.
- **Structured Agentic Pipeline:**
  1. `write` — Composes first drafts using Groq.
  2. `validate` — Verifies readability, length, and structured markdown.
  3. `rag_validate` — Fact-checks assertions against retrieved search context using local ChromaDB and `all-MiniLM-L6-v2` embeddings.
  4. `review` — Runs a 5-layer compliance audit (Tone, Brand, Legal, Accuracy, Policy).
  5. `gen_images` — Renders blog hero graphics using Stability AI in parallel.
  6. `gen_social` — Composes branded Instagram and LinkedIn posts with tailored sizes.
  7. `human_review` — Gated approval interface supporting human feedback and auto-refinement.
  8. `localize` — Launches parallel C++ translations for selected languages after approval.

---

## Project Structure

```text
ET-multiple-agent/
├── .github/workflows/ci.yml     # CI/CD workflow (Pytest + Ruff linting)
├── agents/                      # LLM-powered agents (writer, reviewer, etc.)
├── engine/                      # Core translation microservice (C++ engine source)
├── frontend/                    # Modular Single-Page Application (SPA)
│   ├── index.html               # Main HTML layout
│   ├── js/                      # Controllers (state, pipeline, ui, actions, shortcuts)
│   └── styles/                  # Custom CSS (base, skeleton, mobile, results, layouts)
├── graph/                       # LangGraph orchestration state machine
├── prompts/                     # Prompt templates (writer, reviewer, RAG prompts)
├── rag/                         # RAG ChromaDB vector store helpers
├── scripts/                     # Helper development scripts
│   ├── README.md                # Notes explaining legacy scripts
│   ├── run.bat                  # Legacy batch runner
│   └── start.ps1                # Legacy PowerShell process manager
├── tests/                       # Unit and integration test suites
│   ├── test_api.py              # Mocked API endpoint and job store coverage
│   ├── test_graph_state.py      # Manual validation script for localization wrapper
│   └── test_parser.py           # Parser unit tests
├── api_server.py                # FastAPI backend serving APIs & the frontend at /app
├── config.py                    # Global configuration
├── Dockerfile                   # Deployment container
└── requirements.txt             # Pinned package dependencies
```

---

## Prerequisites

- **Windows** / Linux / macOS
- **Python 3.14+**
- A virtual environment set up at `venv/`

---

## Setup & Installation

1.  **Clone the Repository** and navigate to it:
    ```bash
    git clone https://github.com/Harshit-ops-code/ET-multiple-agent.git
    cd ET-multiple-agent
    ```

2.  **Create the Virtual Environment:**
    On Windows, it is highly recommended to use the absolute path to your Python interpreter and specify the `--copies` flag to bypass Microsoft Store permission errors:
    ```powershell
    & "C:\Users\harsh\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m venv venv --copies
    ```

3.  **Activate and Install Dependencies:**
    ```powershell
    venv\Scripts\activate
    pip install -r requirements.txt
    ```

4.  **Set Up Environment Variables:**
    Copy `.env.example` to `.env` and fill in your API keys:
    ```env
    GROQ_API_KEY=your_groq_key
    TAVILY_API_KEY=your_tavily_key
    STABILITY_API_KEY=your_stability_key
    NEWSAPI_KEY=your_newsapi_key
    ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
    ```

---

## Running the Application

### Option 1: Docker (Recommended)
Build and run the application inside a container:
```bash
docker build -t et-ai-engine .
docker run -p 8000:8000 --env-file .env et-ai-engine
```
Then open: **`http://localhost:8000/app`**

### Option 2: Direct Startup
Start the FastAPI server directly:
```bash
venv\Scripts\python.exe -m uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser to: **`http://127.0.0.1:8000/app`** (FastAPI automatically mounts and serves the static frontend pages under the `/app` URL path).

---

## Testing

Run the automated test suite using Pytest:
```bash
venv\Scripts\python.exe -m pytest tests/ -v
```

All 16 unit and API integration tests will run with mocked gRPC/pipeline backends for rapid verification.

---

## Common Issues & Notes

- **RAG Skip Warnings:** RAG fact-checking requires `chromadb` and `sentence-transformers`. If they fail to load due to environment problems, the `rag_validate` node outputs a warning and skips verification. Making sure your virtual environment packages are correctly installed via `pip install -r requirements.txt` fixes this.
- **NEEDS_FIX Verdicts:** If the review agent flags a critical issue (e.g. missing brand name or bracketed placeholders), the LangGraph workflow automatically routes the draft back into the refinement loop (up to 3 iterations) to correct the output.
