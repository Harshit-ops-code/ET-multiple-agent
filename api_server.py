"""
ET-AI Content Engine — FastAPI Backend
Connects the LangGraph blog_graph to the frontend UI.
"""
import uuid, time, threading, traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import os

app = FastAPI(title="ET-AI Content Engine", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Serve frontend
if os.path.exists("frontend"):
    app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")

jobs = {}

# ── Request models ──
class GenerateRequest(BaseModel):
    mode: str = "news"
    topic: str
    audience: str = "general professional audience"
    length: int = 1000
    context: str = ""
    product_details: str = ""
    key_features: str = ""
    uvp: str = ""
    generate_images: bool = True
    image_formats: List[str] = ["blog", "instagram", "linkedin"]
    social_platforms: List[str] = ["instagram", "linkedin"]
    user_image_b64: Optional[str] = None
    target_languages: List[str] = [] # FIXED: Added languages to the model

class FeedbackRequest(BaseModel):
    job_id: str
    action: str  # "approve" or "refine"
    feedback: str = ""
    target_languages: List[str] = []

class ScheduleRequest(BaseModel):
    job_id: str
    platform: str
    time: str
    note: str

# ── Background pipeline runner ──
def run_pipeline(job_id: str, req: GenerateRequest):
    from graph.blog_graph import blog_graph, BlogState
    from agents.web_search import WebSearchAgent

    jobs[job_id]["status"] = "running"
    jobs[job_id]["current_node"] = "starting"

    try:
        context = req.context
        sources = []
        if req.mode == "news":
            jobs[job_id]["current_node"] = "web_search"
            try:
                searcher = WebSearchAgent()
                result = searcher.search(req.topic)
                context = result.get("context", req.context)
                sources = result.get("sources", [])
            except Exception as e:
                print(f"[WebSearch] Error: {e} — continuing without search")

        if req.mode != "news":
            jobs[job_id]["current_node"] = "write"

        initial_state: BlogState = {
            "mode": req.mode,
            "topic": req.topic,
            "audience": req.audience,
            "length": req.length,
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
            "target_languages": req.target_languages, # FIXED: Pass languages to graph
            "localized_content": {},                  # FIXED: Initialize dict
            "human_feedback": "",
            "approved": False,
            "iteration": 0,
        }

        node_map = {
            "write": "write",
            "validate": "validate",
            "rag_validate": "rag",
            "review": "review",
            "gen_images": "gen_images",
            "gen_social": "gen_social",
            "human_review": "human_review",
        }

        final_state = initial_state.copy()
        jobs[job_id]["current_node"] = "write"
        for event in blog_graph.stream(initial_state):
            for node_name, node_state in event.items():
                jobs[job_id]["current_node"] = node_map.get(node_name, node_name)
                if isinstance(node_state, dict):
                    final_state.update(node_state)

        jobs[job_id].update({
            "status": "awaiting_human",
            "current_node": "human_review",
            "data": final_state,
            "sources": sources,
        })

    except Exception as e:
        traceback.print_exc()
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


def resume_pipeline(job_id: str):
    from graph.blog_graph import blog_graph

    jobs[job_id]["status"] = "running"
    job = jobs[job_id]
    state = job["data"].copy()
    state["human_feedback"] = job.get("pending_feedback", "")
    state["approved"] = job.get("pending_action") == "approve"

    try:
        final_state = state.copy()
        for event in blog_graph.stream(state):
            for node_name, node_state in event.items():
                jobs[job_id]["current_node"] = node_name
                if isinstance(node_state, dict):
                    final_state.update(node_state)

        jobs[job_id]["data"] = final_state
        if state["approved"]:
            jobs[job_id]["status"] = "completed"
        else:
            jobs[job_id]["status"] = "awaiting_human"

    except Exception as e:
        traceback.print_exc()
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)


# ── API endpoints ──
@app.post("/api/generate")
def generate(req: GenerateRequest):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "status": "starting",
        "current_node": "starting",
        "data": None,
        "error": None,
        "start_time": time.time(),
    }
    threading.Thread(target=run_pipeline, args=(job_id, req), daemon=True).start()
    return {"job_id": job_id, "status": "started"}


@app.get("/api/status/{job_id}")
def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    job = jobs[job_id]
    d = job.get("data") or {}
    elapsed = time.time() - job["start_time"]
    return {
        "job_id": job_id,
        "status": job["status"],
        "current_node": job["current_node"],
        "elapsed": round(elapsed, 1),
        "error": job.get("error"),
        "raw_blog": d.get("raw_blog", ""),
        "parsed_blog": d.get("parsed_blog", {}),
        "quality_score": d.get("quality_score", 0),
        "quality_issues": d.get("quality_issues", ""),
        "sources": d.get("sources", []),
        "rag_verdict": d.get("rag_verdict", ""),
        "rag_summary": d.get("rag_summary", ""),
        "rag_suggestions": d.get("rag_suggestions", []),
        "rag_score": d.get("rag_score", 0),
        "review_verdict": d.get("review_verdict", ""),
        "review_score": d.get("review_score", 0),
        "review_checks": d.get("review_checks", {}),
        "review_fixes": d.get("review_fixes", []),
        "editor_note": d.get("editor_note", ""),
        "images": {k: {"base64": v.get("base64",""), "label": v.get("label",""), "width": v.get("width",0), "height": v.get("height",0)} for k, v in (d.get("images") or {}).items()},
        "social_posts": {k: {"caption": v.get("caption", v.get("post_text", "")), "post_text": v.get("post_text", v.get("caption", "")), "image_b64": v.get("image_b64", ""), "size": v.get("size",""), "platform": v.get("platform", k)} for k, v in (d.get("social_posts") or {}).items()},
        "localized_content": d.get("localized_content", {}), # FIXED: Expose translations to UI
        "target_languages": d.get("target_languages", []),
        "iteration": d.get("iteration", 0),
        "approved": d.get("approved", False),
        "mode": d.get("mode", ""),
        "topic": d.get("topic", ""),
    }


@app.post("/api/feedback")
def post_feedback(req: FeedbackRequest):
    if req.job_id not in jobs:
        raise HTTPException(404, "Job not found")
    
    jobs[req.job_id]["pending_action"] = req.action
    jobs[req.job_id]["pending_feedback"] = req.feedback
    
    if req.action == "approve":
        # FIXED: Tell the C++ engine to run manually now that it is approved!
        if jobs[req.job_id].get("data"):
            jobs[req.job_id]["data"]["approved"] = True
            if req.target_languages:
                jobs[req.job_id]["data"]["target_languages"] = req.target_languages
                
        jobs[req.job_id]["status"] = "running"
        jobs[req.job_id]["current_node"] = "localize"
        
        def run_localization_process():
            try:
                from graph.blog_graph import run_localization
                new_state = run_localization(jobs[req.job_id]["data"])
                jobs[req.job_id]["data"] = new_state
                jobs[req.job_id]["status"] = "completed"
            except Exception as e:
                traceback.print_exc()
                jobs[req.job_id]["status"] = "error"
                jobs[req.job_id]["error"] = str(e)
                
        threading.Thread(target=run_localization_process, daemon=True).start()
    else:
        threading.Thread(target=resume_pipeline, args=(req.job_id,), daemon=True).start()
        
    return {"status": "ok", "action": req.action}


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0"}

@app.post("/api/schedule")
def schedule_post_endpoint(req: ScheduleRequest):
    from fastapi import HTTPException
    if req.job_id not in jobs:
        raise HTTPException(404, "Job not found")
        
    job = jobs[req.job_id]
    d = job.get("data") or {}
    
    from agents.scheduler import SocialScheduler
    scheduler = SocialScheduler()
    
    result = scheduler.schedule_post(
        job_id=req.job_id,
        platform=req.platform,
        post_time=req.time,
        note=req.note,
        blog_data=d.get("parsed_blog") or {"topic": d.get("topic", "")},
        social_data=d.get("social_posts", {})
    )
    
    return result

@app.get("/api/queue")
def get_queue():
    from agents.scheduler import get_scheduled_posts
    return {"queue": get_scheduled_posts()}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
