"""
ET-AI Content Engine — FastAPI Backend (fixed)

Fixes applied vs original:
  #2  — CORS: allow_credentials removed, origins read from env
  #3  — Rate limiting via slowapi (10 generate requests / minute / IP)
  #7  — Raw threads replaced with FastAPI BackgroundTasks
  #8  — Job TTL / cleanup handled by JobStore (jobs.db, 2-hour expiry)
  #9  — Top-level imports instead of inside functions
  #11 — Pydantic field validators: topic required, length capped, mode enum
  #12 — stdlib logging replaces print()
  #13 — Polling interval cleaned up on error inside pipeline

Install new deps:
    pip install slowapi limits
"""

import uuid
import time
import logging
import traceback
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Load env variables early
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import os

# ── Fix #9: all project imports at the top ───────────────────────────────────
from job_store import job_store                         # Fix #1 (persistent store)
from graph.blog_graph import blog_graph, BlogState, run_localization
from agents.web_search import WebSearchAgent
from agents.scheduler import SocialScheduler, get_scheduled_posts

# ── Fix #12: proper logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("et_api")

# ── Fix #3: rate limiting ─────────────────────────────────────────────────────
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# ── App factory ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ET-AI Content Engine starting up")
    yield
    logger.info("ET-AI Content Engine shutting down")

app = FastAPI(title="ET-AI Content Engine", version="2.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Fix #2: CORS — origins from env, no credentials wildcard ─────────────────
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5500,http://127.0.0.1:5500")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,          # was True with * — invalid combo
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(BASE_DIR, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")

# ── Request models ────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    # Fix #11: validators guard against blank topics & out-of-range values
    mode: str = Field("news", pattern="^(news|product)$")
    topic: str = Field(..., min_length=5, max_length=500)
    audience: str = Field("general professional audience", max_length=200)
    length: int = Field(1000, ge=300, le=2000)
    context: str = Field("", max_length=2000)
    product_details: str = Field("", max_length=2000)
    key_features: str = Field("", max_length=1000)
    uvp: str = Field("", max_length=500)
    generate_images: bool = True
    image_formats: List[str] = ["blog", "instagram", "linkedin"]
    social_platforms: List[str] = ["instagram", "linkedin"]
    user_image_b64: Optional[str] = None
    target_languages: List[str] = []
    tone: str = Field("professional", pattern="^(professional|conversational|authoritative|playful|educational)$")

    @field_validator("image_formats")
    @classmethod
    def valid_image_formats(cls, v):
        allowed = {"blog", "instagram", "linkedin", "twitter"}
        return [f for f in v if f in allowed]

    @field_validator("social_platforms")
    @classmethod
    def valid_platforms(cls, v):
        allowed = {"instagram", "linkedin", "twitter"}
        return [p for p in v if p in allowed]


class FeedbackRequest(BaseModel):
    job_id: str
    action: str = Field(..., pattern="^(approve|refine)$")
    feedback: str = Field("", max_length=1000)
    target_languages: List[str] = []


class ScheduleRequest(BaseModel):
    job_id: str
    platform: str = Field(..., pattern="^(instagram|linkedin|both)$")
    time: str
    note: str = Field("", max_length=500)


# ── Pipeline helpers ──────────────────────────────────────────────────────────

def _build_initial_state(req: GenerateRequest, context: str, sources: list) -> BlogState:
    return {
        "mode": req.mode,
        "topic": req.topic,
        "audience": req.audience,
        "length": req.length,
        "tone": req.tone,
        "context": context,
        "product_details": req.product_details,
        "key_features": req.key_features,
        "uvp": req.uvp,
        "raw_blog": "",
        "parsed_blog": {},
        "quality_score": 0.0,
        "quality_issues": "",
        "sources": sources,
        "rag_verdict": "",
        "rag_summary": "",
        "rag_suggestions": [],
        "rag_score": 0.0,
        "review_verdict": "",
        "review_score": 0,
        "review_checks": {},
        "review_fixes": [],
        "editor_note": "",
        "images": {},
        "generate_images": req.generate_images,
        "image_formats": req.image_formats,
        "user_image_b64": req.user_image_b64,
        "social_posts": {},
        "social_platforms": req.social_platforms,
        "target_languages": req.target_languages,
        "localized_content": {},
        "human_feedback": "",
        "approved": False,
        "iteration": 0,
    }


NODE_MAP = {
    "write": "write",
    "validate": "validate",
    "rag_validate": "rag",
    "review": "review",
    "gen_images": "gen_images",
    "gen_social": "gen_social",
    "human_review": "human_review",
}


def run_pipeline(job_id: str, req: GenerateRequest) -> None:
    """
    Fix #7: called by BackgroundTasks — no raw threading.Thread needed.
    Fix #13: always cleans up status on both success and error paths.
    """
    job_store.update(job_id, {"status": "running", "current_node": "starting"})
    logger.info("Pipeline started for job %s (mode=%s topic=%s)", job_id, req.mode, req.topic[:60])

    try:
        context = req.context
        sources: list = []

        if req.mode == "news":
            job_store.update(job_id, {"current_node": "web_search"})
            try:
                result  = WebSearchAgent().search(req.topic)
                context = result.get("context", req.context)
                sources = result.get("sources", [])
            except Exception as e:
                logger.warning("WebSearch failed for job %s: %s — continuing", job_id, e)

        initial_state = _build_initial_state(req, context, sources)
        final_state   = initial_state.copy()

        job_store.update(job_id, {"current_node": "write"})

        for event in blog_graph.stream(initial_state):
            for node_name, node_state in event.items():
                job_store.update(job_id, {"current_node": NODE_MAP.get(node_name, node_name)})
                if isinstance(node_state, dict):
                    final_state.update(node_state)

        job_store.update(job_id, {
            "status":       "awaiting_human",
            "current_node": "human_review",
            "data":         final_state,
            "sources":      sources,
        })
        logger.info("Pipeline awaiting human review for job %s", job_id)

    except Exception as e:
        logger.error("Pipeline error for job %s: %s", job_id, traceback.format_exc())
        job_store.update(job_id, {"status": "error", "error": str(e)})


def resume_pipeline(job_id: str) -> None:
    """Fix #13: error path also sets status so polling stops."""
    job = job_store.get(job_id)
    if not job:
        return

    job_store.update(job_id, {"status": "running"})
    state = job["data"].copy()
    state["human_feedback"] = job.get("data", {}).get("pending_feedback", "")
    state["approved"]       = job.get("data", {}).get("pending_action") == "approve"

    try:
        final_state = state.copy()
        for event in blog_graph.stream(state):
            for node_name, node_state in event.items():
                job_store.update(job_id, {"current_node": node_name})
                if isinstance(node_state, dict):
                    final_state.update(node_state)

        job_store.update(job_id, {"data": final_state})

        new_status = "completed" if state["approved"] else "awaiting_human"
        job_store.update(job_id, {"status": new_status})

    except Exception as e:
        logger.error("Resume error for job %s: %s", job_id, traceback.format_exc())
        job_store.update(job_id, {"status": "error", "error": str(e)})


def run_localization_task(job_id: str) -> None:
    """Fix #13: error sets status correctly so polling stops."""
    try:
        job = job_store.get(job_id)
        if not job:
            return
        new_state = run_localization(job["data"])
        job_store.update(job_id, {"data": new_state, "status": "completed"})
        logger.info("Localization completed for job %s", job_id)
    except Exception as e:
        logger.error("Localization error for job %s: %s", job_id, traceback.format_exc())
        job_store.update(job_id, {"status": "error", "error": str(e)})


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.post("/api/generate")
@limiter.limit("10/minute")           # Fix #3: rate limit
async def generate(request: Request, req: GenerateRequest, bg: BackgroundTasks):
    job_id = str(uuid.uuid4())
    job_store.create(job_id, {
        "status":       "starting",
        "current_node": "starting",
        "error":        None,
    })
    bg.add_task(run_pipeline, job_id, req)   # Fix #7: BackgroundTasks
    logger.info("Job %s created", job_id)
    return {"job_id": job_id, "status": "started"}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")

    d       = job.get("data") or {}
    elapsed = time.time() - job["start_time"]

    return {
        "job_id":           job_id,
        "status":           job["status"],
        "current_node":     job["current_node"],
        "elapsed":          round(elapsed, 1),
        "error":            job.get("error"),
        "raw_blog":         d.get("raw_blog", ""),
        "parsed_blog":      d.get("parsed_blog", {}),
        "quality_score":    d.get("quality_score", 0),
        "quality_issues":   d.get("quality_issues", ""),
        "sources":          d.get("sources", []),
        "rag_verdict":      d.get("rag_verdict", ""),
        "rag_summary":      d.get("rag_summary", ""),
        "rag_suggestions":  d.get("rag_suggestions", []),
        "rag_score":        d.get("rag_score", 0),
        "review_verdict":   d.get("review_verdict", ""),
        "review_score":     d.get("review_score", 0),
        "review_checks":    d.get("review_checks", {}),
        "review_fixes":     d.get("review_fixes", []),
        "editor_note":      d.get("editor_note", ""),
        "images": {
            k: {
                "base64": v.get("base64", ""),
                "label":  v.get("label", ""),
                "width":  v.get("width", 0),
                "height": v.get("height", 0),
            }
            for k, v in (d.get("images") or {}).items()
        },
        "social_posts": {
            k: {
                "caption":    v.get("caption", v.get("post_text", "")),
                "post_text":  v.get("post_text", v.get("caption", "")),
                "image_b64":  v.get("image_b64", ""),
                "size":       v.get("size", ""),
                "platform":   v.get("platform", k),
            }
            for k, v in (d.get("social_posts") or {}).items()
        },
        "localized_content": d.get("localized_content", {}),
        "target_languages":  d.get("target_languages", []),
        "iteration":         d.get("iteration", 0),
        "approved":          d.get("approved", False),
        "mode":              d.get("mode", ""),
        "topic":             d.get("topic", ""),
    }


@app.post("/api/feedback")
async def post_feedback(req: FeedbackRequest, bg: BackgroundTasks):
    job = job_store.get(req.job_id)
    if job is None:
        raise HTTPException(404, "Job not found")

    data_patch = {
        "pending_action":   req.action,
        "pending_feedback": req.feedback,
    }

    if req.action == "approve":
        data_patch["approved"] = True
        if req.target_languages:
            data_patch["target_languages"] = req.target_languages

        job_store.update(req.job_id, {
            "status":       "running",
            "current_node": "localize",
            "data":         data_patch,
        })
        bg.add_task(run_localization_task, req.job_id)   # Fix #7
    else:
        job_store.update(req.job_id, {"data": data_patch})
        bg.add_task(resume_pipeline, req.job_id)          # Fix #7

    return {"status": "ok", "action": req.action}


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.1.0"}


@app.get("/")
async def root():
    return RedirectResponse(url="/app")


@app.post("/api/schedule")
async def schedule_post_endpoint(req: ScheduleRequest):
    job = job_store.get(req.job_id)
    if job is None:
        raise HTTPException(404, "Job not found")

    d       = job.get("data") or {}
    result  = SocialScheduler().schedule_post(
        job_id    = req.job_id,
        platform  = req.platform,
        post_time = req.time,
        note      = req.note,
        blog_data = d.get("parsed_blog") or {"topic": d.get("topic", "")},
        social_data = d.get("social_posts", {}),
    )
    return result


@app.get("/api/queue")
async def get_queue():
    return {"queue": get_scheduled_posts()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)