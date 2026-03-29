from graph.blog_graph import blog_graph

initial_state = {
    "mode": "news",
    "topic": "test",
    "audience": "test",
    "length": 500,
    "context": "",
    "product_details": "",
    "key_features": "",
    "uvp": "",
    "raw_blog": "mock content",
    "parsed_blog": {},
    "quality_score": 100,
    "quality_issues": "",
    "sources": [],
    "rag_verdict": "",
    "rag_summary": "",
    "rag_suggestions": [],
    "rag_score": 100,
    "review_verdict": "APPROVED",
    "review_score": 100,
    "review_checks": {},
    "review_fixes": [],
    "editor_note": "",
    "images": {},
    "generate_images": False,
    "image_formats": [],
    "user_image_b64": None,
    "social_posts": {},
    "social_platforms": [],
    "target_languages": ["Spanish", "French"],
    "localized_content": {},
    "human_feedback": "",
    "approved": True,
    "iteration": 0,
}

from graph.blog_graph import run_localization
res = run_localization(initial_state)
print("run_localization direct result:", res.get("localized_content"))
