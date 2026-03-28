
from graph.blog_graph import write_blog, validate_blog, rag_validate, review_blog, generate_images, generate_social_posts
from agents.web_search import WebSearchAgent

state = {
    "mode":            "news",
    "topic":           "AI agents in 2024",
    "audience":        "tech professionals",
    "length":          500,
    "context":         "AI agents are evolving rapidly.",
    "product_details": "",
    "key_features":    "",
    "uvp":             "",
    "raw_blog":        "",
    "parsed_blog":     {},
    "quality_score":   0,
    "quality_issues":  "",
    "sources":         [],
    "human_feedback":  "",
    "approved":        False,
    "iteration":       0,
    "generate_images": True,
    "image_formats":   ["blog"],
    "review_verdict":  "",
    "review_score":    0,
    "review_checks":   {},
    "review_fixes":    [],
    "editor_note":     "",
    "images":          {},
    "rag_verdict":     "",
    "rag_summary":     "",
    "rag_suggestions": [],
    "rag_score":       0,
    "social_platforms": ["instagram"],
    "social_posts":     {},
}

print("Running write_blog...")
state = write_blog(state)
print("Running validate_blog...")
state = validate_blog(state)
print("Running rag_validate...")
state = rag_validate(state)
print("Running review_blog...")
state = review_blog(state)
print("Running generate_images...")
state = generate_images(state)
print("Running generate_social_posts...")
state = generate_social_posts(state)
print("All nodes completed!")
