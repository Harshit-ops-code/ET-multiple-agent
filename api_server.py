from flask import Flask, request, jsonify
from flask_cors import CORS
from graph.blog_graph import blog_graph, BlogState
from agents.web_search import WebSearchAgent
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__)
CORS(app)

# In-memory session store (one blog at a time per server)
current_state: dict = {}


@app.route('/generate', methods=['POST'])
def generate():
    global current_state
    data = request.get_json()
    mode = data.get('mode', 'news')   # 'news' or 'product'

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
    }

    # Run write + validate only (stop before human_review blocks)
    from graph.blog_graph import write_blog, validate_blog
    state = write_blog(state)
    state = validate_blog(state)
    current_state = state

    return jsonify(_state_to_response(state))


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
    }


if __name__ == '__main__':
    app.run(debug=True, port=5000)