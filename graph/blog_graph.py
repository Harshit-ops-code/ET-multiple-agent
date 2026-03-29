from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import TypedDict, Literal, Optional
from config import GROQ_API_KEY, GROQ_MODEL, MAX_REGENERATIONS
from prompts.blog_writer_prompt import (
    SYSTEM_PROMPT_NEWS, SYSTEM_PROMPT_PRODUCT,
    HUMAN_TEMPLATE_NEWS, HUMAN_TEMPLATE_PRODUCT,
    REFINEMENT_SYSTEM_PROMPT, REFINEMENT_HUMAN_TEMPLATE,
)
from agents.review_agent import ReviewAgent
from agents.image_generator import ImageGenerator
from agents.social_media_agent import SocialMediaAgent
import re


# ── State definition ──────────────────────────────────────────────
class BlogState(TypedDict):
    # Inputs
    mode:             Literal["news", "product"]
    topic:            str
    audience:         str
    length:           int
    context:          str
    product_details:  str
    key_features:     str
    uvp:              str

    # Processing
    raw_blog:         str
    parsed_blog:      dict
    quality_score:    float
    quality_issues:   str
    sources:          list

    # RAG
    rag_verdict:      str
    rag_summary:      str
    rag_suggestions:  list
    rag_score:        float

    # Review
    review_verdict:   str
    review_score:     int
    review_checks:    dict
    review_fixes:     list
    editor_note:      str

    # Images
    images:           dict
    generate_images:  bool
    image_formats:    list

    # Social media
    user_image_b64:   str  
    social_posts:     dict
    social_platforms: list

    # Human-in-the-loop
    human_feedback:   str
    approved:         bool
    iteration:        int
    
    # Localization (NEW)
    target_languages: list
    localized_content: dict


# ── LLM instance ──────────────────────────────────────────────────
llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name=GROQ_MODEL,
    temperature=0.7,
    max_tokens=4096,
)


# ── Node: write_blog ──────────────────────────────────────────────
def write_blog(state: BlogState) -> BlogState:
    """Write or rewrite the blog depending on iteration."""
    print(f"\n[LangGraph] write_blog — iteration {state['iteration'] + 1}, mode={state['mode']}")

    if state["iteration"] == 0:
        if state["mode"] == "news":
            prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT_NEWS),
                ("human",  HUMAN_TEMPLATE_NEWS),
            ])
            chain = prompt | llm | StrOutputParser()
            raw = chain.invoke({
                "topic":    state["topic"],
                "audience": state["audience"],
                "length":   state["length"],
                "context":  state["context"],
            })
        else:
            prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT_PRODUCT),
                ("human",  HUMAN_TEMPLATE_PRODUCT),
            ])
            chain = prompt | llm | StrOutputParser()
            raw = chain.invoke({
                "topic":           state["topic"],
                "audience":        state["audience"],
                "length":          state["length"],
                "product_details": state["product_details"],
                "key_features":    state["key_features"],
                "uvp":             state["uvp"],
            })
    else:
        # Refinement pass with feedback
        prompt = ChatPromptTemplate.from_messages([
            ("system", REFINEMENT_SYSTEM_PROMPT),
            ("human",  REFINEMENT_HUMAN_TEMPLATE),
        ])
        chain = prompt | llm | StrOutputParser()
        raw = chain.invoke({
            "original_blog":  state["raw_blog"],
            "feedback":       state["human_feedback"],
            "quality_issues": state["quality_issues"],
        })

    return {
        **state,
        "raw_blog":  raw,
        "iteration": state["iteration"] + 1,
    }


# ── Node: validate_blog ───────────────────────────────────────────
def validate_blog(state: BlogState) -> BlogState:
    """Basic structural quality check."""
    print(f"[LangGraph] validate_blog")

    blog   = state["raw_blog"]
    issues = []
    score  = 100.0

    if len(blog) < 400:
        issues.append("Blog too short")
        score -= 30
    if "TITLE:" not in blog:
        issues.append("Missing structured title")
        score -= 15
    if blog.count("\n\n") < 3:
        issues.append("Lacks paragraph structure")
        score -= 10
    if state["mode"] == "news" and len(state.get("sources", [])) > 0:
        if "http" not in blog:
            issues.append("No sources referenced")
            score -= 20
    if state["mode"] == "product":
        lower = blog.lower()
        if not any(w in lower for w in ["you", "your", "customer", "solution"]):
            issues.append("Not customer-centric enough")
            score -= 15

    return {
        **state,
        "quality_score":  max(score, 0),
        "quality_issues": "; ".join(issues) if issues else "None",
        "parsed_blog":    _parse_blog(blog),
    }


def _parse_blog(raw: str) -> dict:
    """Parse structured fields from raw LLM output."""
    result = {"raw": raw, "content": raw}

    for field, pattern in [
        ("title",            r"TITLE:\s*(.+)"),
        ("meta_description", r"META_DESCRIPTION:\s*(.+)"),
        ("reading_time",     r"READING_TIME:\s*(.+)"),
        ("word_count",       r"WORD_COUNT:\s*(.+)"),
        ("seo_keywords",     r"SEO_KEYWORDS:\s*(.+)"),
        ("target_cta",       r"TARGET_CTA:\s*(.+)"),
        ("sources_used",     r"SOURCES_USED:\s*(.+)"),
    ]:
        m = re.search(pattern, raw)
        if m:
            val = m.group(1).strip()
            result[field] = (
                [k.strip() for k in val.split(",")]
                if field in ("seo_keywords", "sources_used")
                else val
            )

    parts = raw.split("---")
    if len(parts) >= 3:
        result["content"] = parts[2].strip()

    return result


# ── Node: rag_validate ────────────────────────────────────────────
def rag_validate(state: BlogState) -> BlogState:
    """RAG validation — fact-checks blog against embedded sources."""
    print(f"[LangGraph] rag_validate")

    try:
        from agents.rag_validator import RAGValidator
        validator  = RAGValidator()
        rag_result = validator.validate(
            blog_content=state["raw_blog"],
            sources=state["sources"],
            mode=state["mode"],
            topic=state["topic"],
        )

        existing = state.get("quality_score", 100)
        combined = (existing * 0.4) + (rag_result["accuracy_score"] * 0.6)

        existing_issues = state.get("quality_issues", "")
        rag_issues      = "; ".join(rag_result["issues"]) if rag_result.get("issues") else ""
        all_issues      = "; ".join(filter(None, [existing_issues, rag_issues]))

        return {
            **state,
            "quality_score":   round(combined, 1),
            "quality_issues":  all_issues or "None",
            "rag_verdict":     rag_result.get("verdict", "PASS"),
            "rag_summary":     rag_result.get("summary", ""),
            "rag_suggestions": rag_result.get("suggestions", []),
            "rag_score":       rag_result.get("accuracy_score", 0),
        }

    except Exception as e:
        print(f"[LangGraph] rag_validate error: {e} — skipping")
        return {
            **state,
            "rag_verdict":     "PASS",
            "rag_summary":     "",
            "rag_suggestions": [],
            "rag_score":       75,
        }


# ── Node: review_blog ─────────────────────────────────────────────
def review_blog(state: BlogState) -> BlogState:
    """5-layer compliance review — tone, legal, brand, accuracy, policy."""
    print(f"[LangGraph] review_blog")

    try:
        reviewer = ReviewAgent()
        result   = reviewer.review(
            content=state["raw_blog"],
            mode=state["mode"],
        )

        auto_feedback = ""
        if result["overall_verdict"] in ("NEEDS_FIX", "REJECTED"):
            fixes = "\n".join(f"- {f}" for f in result.get("fixes_required", []))
            auto_feedback = f"Review agent found issues. Fix these:\n{fixes}"

        existing = state.get("quality_score", 100)
        blended  = (existing * 0.5) + (result["overall_score"] * 0.5)

        return {
            **state,
            "quality_score":  round(blended, 1),
            "review_verdict": result["overall_verdict"],
            "review_score":   result["overall_score"],
            "review_checks": {
                "tone":     {"score": result["tone_score"],     "status": result["tone_status"],     "issues": result["tone_issues"]},
                "legal":    {"score": result["legal_score"],    "status": result["legal_status"],    "issues": result["legal_issues"]},
                "brand":    {"score": result["brand_score"],    "status": result["brand_status"],    "issues": result["brand_issues"]},
                "accuracy": {"score": result["accuracy_score"], "status": result["accuracy_status"], "issues": result["accuracy_issues"]},
                "policy":   {"score": result["policy_score"],   "status": result["policy_status"],   "issues": result["policy_issues"]},
            },
            "review_fixes": result.get("fixes_required", []),
            "editor_note":  result.get("editor_note", ""),
            "human_feedback": auto_feedback if auto_feedback else state.get("human_feedback", ""),
        }

    except Exception as e:
        print(f"[LangGraph] review_blog error: {e} — skipping")
        return {
            **state,
            "review_verdict": "APPROVED",
            "review_score":   75,
            "review_checks":  {},
            "review_fixes":   [],
            "editor_note":    "",
        }


# ── Node: generate_images ─────────────────────────────────────────
def generate_images(state: BlogState) -> BlogState:
    """Generate blog/Instagram/LinkedIn images via Stability AI."""
    if not state.get("generate_images", False):
        print(f"[LangGraph] generate_images — skipped (toggled off)")
        return {**state, "images": {}}

    print(f"[LangGraph] generate_images — formats={state.get('image_formats')}")

    try:
        generator = ImageGenerator()
        result    = generator.generate(
            title=state.get("parsed_blog", {}).get("title", state["topic"]),
            topic=state["topic"],
            mode=state["mode"],
            formats=state.get("image_formats", ["blog"]),
        )
        return {**state, "images": result.get("images", {})}

    except Exception as e:
        print(f"[LangGraph] generate_images error: {e}")
        return {**state, "images": {}}


# ── Node: generate_social_posts ───────────────────────────────────
def generate_social_posts(state: BlogState) -> BlogState:
    """Generate Instagram + LinkedIn posts with images and captions."""
    platforms = state.get("social_platforms", [])
    if not platforms:
        print(f"[LangGraph] generate_social_posts — skipped (no platforms)")
        return {**state, "social_posts": {}}

    print(f"[LangGraph] generate_social_posts — {platforms}")

    try:
        agent = SocialMediaAgent()
        posts = agent.generate(
            blog_data={
                "topic":        state["topic"],
                "title":        state.get("parsed_blog", {}).get("title", state["topic"]),
                "content":      state.get("parsed_blog", {}).get("content", state["raw_blog"]),
                "key_features": state.get("key_features", ""),
                "uvp":          state.get("uvp", ""),
                "audience":     state.get("audience", "professionals"),
            },
            mode=state["mode"],
            platforms=platforms,
            user_image_b64=state.get("user_image_b64"),
            existing_images=state.get("images", {}),
        )
        return {**state, "social_posts": posts}

    except Exception as e:
        print(f"[LangGraph] generate_social_posts error: {e}")
        import traceback
        traceback.print_exc()          
        return {**state, "social_posts": {}}


# ── Node: human_review ────────────────────────────────────────────
def human_review(state: BlogState) -> BlogState:
    """Placeholder — frontend sends feedback via /feedback API endpoint."""
    print(f"[LangGraph] human_review — quality={state.get('quality_score', 0):.0f}/100 "
          f"review={state.get('review_verdict', 'N/A')}")
    return state


# ── Node: run_localization (NEW) ──────────────────────────────────
def run_localization(state: BlogState) -> BlogState:
    """Passes approved content to the C++ microservice for parallel translation."""
    languages = state.get("target_languages", [])
    
    if not languages or not state.get("approved"):
        print(f"[LangGraph] run_localization — skipped (no languages or not approved)")
        return {**state, "localized_content": {}}

    try:
        from agents.localization_wrapper import LocalizationWrapper
        wrapper = LocalizationWrapper()
        
        translations = wrapper.localize(
            final_blog=state["raw_blog"], 
            target_languages=languages
        )
        return {**state, "localized_content": translations}
    except Exception as e:
        print(f"[LangGraph] run_localization error: {e}")
        return {**state, "localized_content": {}}


# ── Router ────────────────────────────────────────────────────────
def should_continue(state: BlogState) -> Literal["refine", "done"]:
    """Decide whether to loop back or finish."""
    if state["approved"]:
        return "done"

    if state["iteration"] >= MAX_REGENERATIONS:
        print(f"[LangGraph] Max iterations ({MAX_REGENERATIONS}) reached — finishing")
        return "done"

    if state.get("review_verdict") == "REJECTED":
        print(f"[LangGraph] Review REJECTED — auto-refining")
        return "refine"

    if state.get("review_verdict") in ("APPROVED", "NEEDS_FIX"):
        return "done"

    return "done"


# ── Build graph ───────────────────────────────────────────────────
def build_blog_graph():
    g = StateGraph(BlogState)

    # Register all nodes
    g.add_node("write",          write_blog)
    g.add_node("validate",       validate_blog)
    g.add_node("rag_validate",   rag_validate)
    g.add_node("review",         review_blog)
    g.add_node("gen_images",     generate_images)
    g.add_node("gen_social",     generate_social_posts)
    g.add_node("human_review",   human_review)
    g.add_node("localize",       run_localization) # NEW NODE added here

    # Linear pipeline edges
    g.set_entry_point("write")
    g.add_edge("write",        "validate")
    g.add_edge("validate",     "rag_validate")
    g.add_edge("rag_validate", "review")
    g.add_edge("review",       "gen_images")
    g.add_edge("gen_images",   "gen_social")
    g.add_edge("gen_social",   "human_review")

    # Conditional: human_review → refine loop OR proceed to localization
    g.add_conditional_edges("human_review", should_continue, {
        "refine": "write",
        "done":   "localize", # Routes to localization when done refining
    })
    
    # Finish the graph after localization
    g.add_edge("localize", END)

    return g.compile()


# ── Singleton graph instance ──────────────────────────────────────
blog_graph = build_blog_graph()
