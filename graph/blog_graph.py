from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import TypedDict, Literal, Optional
from config import GROQ_API_KEY, GROQ_MODEL, MAX_REGENERATIONS
from prompts.blog_writer_prompt import (
    SYSTEM_PROMPT_NEWS, SYSTEM_PROMPT_PRODUCT,
    HUMAN_TEMPLATE_NEWS, HUMAN_TEMPLATE_PRODUCT,
    REFINEMENT_TEMPLATE,
)
import re


# ── State definition ──────────────────────────────────────────────
class BlogState(TypedDict):
    # Inputs
    mode:            Literal["news", "product"]
    topic:           str
    audience:        str
    length:          int
    context:         str           # web search context (news mode)
    product_details: str           # product description (product mode)
    key_features:    str
    uvp:             str           # unique value proposition

    # Processing
    raw_blog:        str
    parsed_blog:     dict
    quality_score:   float
    quality_issues:  str
    sources:         list

    # Human-in-the-loop
    human_feedback:  str
    approved:        bool
    iteration:       int           # how many times we've regenerated


# ── Node functions ────────────────────────────────────────────────
llm = ChatGroq(api_key=GROQ_API_KEY, model_name=GROQ_MODEL,
               temperature=0.7, max_tokens=4096)


def write_blog(state: BlogState) -> BlogState:
    """Write the blog using the correct mode prompt."""
    print(f"\n[LangGraph] write_blog — iteration {state['iteration']+1}, mode={state['mode']}")

    if state["iteration"] == 0:
        # First write
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
                "topic":          state["topic"],
                "audience":       state["audience"],
                "length":         state["length"],
                "product_details": state["product_details"],
                "key_features":   state["key_features"],
                "uvp":            state["uvp"],
            })
    else:
        # Refinement pass — uses feedback
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT_NEWS if state["mode"] == "news" else SYSTEM_PROMPT_PRODUCT),
            ("human",  REFINEMENT_TEMPLATE),
        ])
        chain = prompt | llm | StrOutputParser()
        raw = chain.invoke({
            "original_blog":  state["raw_blog"],
            "feedback":       state["human_feedback"],
            "quality_issues": state["quality_issues"],
        })

    return {**state, "raw_blog": raw, "iteration": state["iteration"] + 1}


def validate_blog(state: BlogState) -> BlogState:
    """Score the blog quality and flag issues."""
    print(f"[LangGraph] validate_blog")

    blog = state["raw_blog"]
    issues = []
    score  = 100.0

    if len(blog) < 400:
        issues.append("Blog too short"); score -= 30
    if "TITLE:" not in blog:
        issues.append("Missing structured title"); score -= 15
    if blog.count("\n\n") < 3:
        issues.append("Lacks paragraph structure"); score -= 10
    if state["mode"] == "news" and "http" not in blog and len(state["sources"]) > 0:
        issues.append("No sources referenced"); score -= 20
    if state["mode"] == "product":
        lower = blog.lower()
        if not any(w in lower for w in ["you", "your", "customer", "solution"]):
            issues.append("Not customer-centric enough"); score -= 15

    return {
        **state,
        "quality_score":  max(score, 0),
        "quality_issues": "; ".join(issues) if issues else "None",
        "parsed_blog":    _parse_blog(blog),
    }


def _parse_blog(raw: str) -> dict:
    result = {"raw": raw, "content": raw}
    for field, pattern in [
        ("title",            r"TITLE:\s*(.+)"),
        ("meta_description", r"META_DESCRIPTION:\s*(.+)"),
        ("reading_time",     r"READING_TIME:\s*(.+)"),
        ("seo_keywords",     r"SEO_KEYWORDS:\s*(.+)"),
        ("target_cta",       r"TARGET_CTA:\s*(.+)"),
        ("sources_used",     r"SOURCES_USED:\s*(.+)"),
    ]:
        m = re.search(pattern, raw)
        if m:
            val = m.group(1).strip()
            result[field] = [k.strip() for k in val.split(",")] if field in ("seo_keywords", "sources_used") else val

    parts = raw.split("---")
    if len(parts) >= 3:
        result["content"] = parts[2].strip()
    return result


def human_review(state: BlogState) -> BlogState:
    """Placeholder — frontend sends feedback via API, state updated externally."""
    print(f"[LangGraph] Waiting for human review... (quality: {state['quality_score']:.0f}/100)")
    return state


def should_continue(state: BlogState) -> Literal["refine", "done"]:
    """Router: approved or max retries reached → done. Otherwise → refine."""
    if state["approved"]:
        return "done"
    if state["iteration"] >= MAX_REGENERATIONS:
        print(f"[LangGraph] Max iterations reached ({MAX_REGENERATIONS}), finishing.")
        return "done"
    return "refine"


# ── Build the graph ───────────────────────────────────────────────
def build_blog_graph():
    g = StateGraph(BlogState)

    g.add_node("write",    write_blog)
    g.add_node("validate", validate_blog)
    g.add_node("review",   human_review)

    g.set_entry_point("write")
    g.add_edge("write",    "validate")
    g.add_edge("validate", "review")

    g.add_conditional_edges("review", should_continue, {
        "refine": "write",    # loop back with feedback
        "done":   END,
    })

    return g.compile()


blog_graph = build_blog_graph()