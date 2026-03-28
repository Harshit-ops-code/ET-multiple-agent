from flask import Flask, request, jsonify
from flask_cors import CORS
from graph.blog_graph import blog_graph, BlogState
from agents.web_search import WebSearchAgent
import sys, os

# In generate() and feedback(), add rag_validate step:
from graph.blog_graph import (write_blog, validate_blog, rag_validate,
                               review_blog, generate_images,
                               generate_social_posts)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__)
CORS(app)

# In-memory session store (one blog at a time per server)
current_state: dict = {}


@app.route('/generate', methods=['POST'])
def generate():
    global current_state
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON payload received"}), 400

        user_image_b64 = data.get("user_image_b64", None)
            
        mode = data.get('mode', 'news')   # 'news' or 'product'

        print(f"[API] generate_images={data.get('generate_images')} formats={data.get('image_formats')}")

        # Build search context (news mode only)
        context = ""
        sources = []
        if mode == "news":
            searcher = WebSearchAgent()
            result   = searcher.search(data.get('topic', ''))
            context  = result["context"]
            sources  = result["sources"]

        # Initial state
        state: BlogState = {
            "mode":            mode,
            "topic":           data.get("topic", ""),
            "audience":        data.get("audience", "general audience"),
            "length":          int(data.get("length", 1000)),
            "context":         context,
            "product_details": data.get("product_details", ""),
            "key_features":    data.get("key_features", ""),
            "uvp":             data.get("uvp", ""),
            "raw_blog":        "",
            "parsed_blog":     {},
            "quality_score":   0,
            "quality_issues":  "",
            "sources":         sources,
            "human_feedback":  "",
            "approved":        False,
            "iteration":       0,
            "generate_images": data.get("generate_images", False),
            "image_formats":   data.get("image_formats", ["blog"]),
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
            "social_platforms": data.get("social_platforms", []),
            "social_posts":     {},
            "user_image_b64":   user_image_b64,
        }

        # Run write + validate only (stop before human_review blocks)
        from graph.blog_graph import write_blog, validate_blog, rag_validate, review_blog, generate_images, generate_social_posts
        state = write_blog(state)
        state = validate_blog(state)
        state = rag_validate(state) 
        state = review_blog(state)
        state = generate_images(state)
        state = generate_social_posts(state)
        current_state = state

        return jsonify(_state_to_response(state))
    except Exception as e:
        import traceback
        print("\n!!! EXCEPTION IN /generate !!!")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/feedback', methods=['POST'])
def feedback():
    """User submits feedback — AI regenerates with it."""
    global current_state
    data = request.get_json()
    action   = data.get("action")    # "approve" or "regenerate"
    feedback = data.get("feedback", "")

    if action == "approve":
        current_state["approved"] = True
        return jsonify({"message": "Blog approved!", "approved": True})

    # Regenerate with feedback
    from graph.blog_graph import write_blog, validate_blog
    current_state["human_feedback"] = feedback
    current_state["approved"]       = False
    current_state = write_blog(current_state)
    current_state = validate_blog(current_state)

    return jsonify(_state_to_response(current_state))


def _state_to_response(state: dict) -> dict:
    p = state.get("parsed_blog", {})


    # Convert saved images to base64 for frontend
    images_out = {}
    for fmt, img in state.get("images", {}).items():
        images_out[fmt] = {
            "base64": img.get("base64", ""),
            "label":  img.get("label", fmt),
            "width":  img.get("width", 1024),
            "height": img.get("height", 576),
        }
    
    # Social posts — strip image data for caption preview, keep b64 for display
    social_out = {}
    for platform, post in state.get("social_posts", {}).items():
        if "error" not in post:
            social_out[platform] = {
                "caption":    post.get("caption") or post.get("post_text", ""),
                "image_b64":  post.get("image_b64", ""),
                "dimensions": post.get("dimensions", ""),
                "platform":   platform,
                "mode":       post.get("mode", ""),
            }

    return {
        "success":         True,
        "mode":            state["mode"],
        "title":           p.get("title", ""),
        "meta_description":p.get("meta_description", ""),
        "reading_time":    p.get("reading_time", ""),
        "seo_keywords":    p.get("seo_keywords", []),
        "target_cta":      p.get("target_cta", ""),
        "content":         p.get("content", state.get("raw_blog", "")),
        "sources":         state.get("sources", []),
        "quality_score":   state.get("quality_score", 0),
        "quality_issues":  state.get("quality_issues", ""),
        "iteration":       state.get("iteration", 1),
        "max_iterations":  3,
        "rag_verdict":     state.get("rag_verdict", ""),
        "rag_summary":     state.get("rag_summary", ""),
        "rag_suggestions": state.get("rag_suggestions", []),
        "rag_score":       state.get("rag_score", 0),
        "review_verdict":   state.get("review_verdict", ""),
        "review_score":     state.get("review_score", 0),
        "review_checks":    state.get("review_checks", {}),
        "review_fixes":     state.get("review_fixes", []),
        "editor_note":      state.get("editor_note", ""),
        "images":           images_out,
        "social_posts":     social_out,
    }


if __name__ == '__main__':
    app.run(debug=True, port=5000)