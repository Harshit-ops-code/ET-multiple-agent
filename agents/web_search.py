from tavily import TavilyClient
from config import TAVILY_API_KEY
from datetime import datetime


class WebSearchAgent:
    """
    Fetches live, current web articles about a topic.
    Returns a clean context string ready to inject into the blog prompt.
    """

    def __init__(self):
        self.client = TavilyClient(api_key=TAVILY_API_KEY)

    def search(self, topic: str, max_results: int = 5) -> dict:
        """
        Search the web for the topic and return structured results.
        """
        print(f"\n[WebSearchAgent] Searching: '{topic}'")

        response = self.client.search(
            query=topic,
            search_depth="advanced",     # deeper = better quality
            max_results=max_results,
            include_answer=True,          # Tavily gives a short AI summary too
            include_raw_content=False,
        )

        sources = []
        for r in response.get("results", []):
            sources.append({
                "title":   r.get("title", ""),
                "url":     r.get("url", ""),
                "content": r.get("content", "")[:600],  # cap per source
                "score":   r.get("score", 0),
            })

        # Sort by relevance score
        sources.sort(key=lambda x: x["score"], reverse=True)

        context = self._build_context(topic, sources, response.get("answer", ""))

        print(f"[WebSearchAgent] Found {len(sources)} sources")
        return {
            "context":       context,
            "sources":       sources,
            "tavily_answer": response.get("answer", ""),
        }

    def _build_context(self, topic: str, sources: list, tavily_answer: str) -> str:
        today = datetime.now().strftime("%B %d, %Y")

        context_parts = [
            f"=== CURRENT WORLD CONTEXT (as of {today}) ===",
            f"Topic: {topic}",
            "",
        ]

        if tavily_answer:
            context_parts += [
                "QUICK SUMMARY FROM LIVE SOURCES:",
                tavily_answer,
                "",
            ]

        context_parts.append("RECENT ARTICLES AND FINDINGS:")
        for i, src in enumerate(sources, 1):
            context_parts += [
                f"\n[Source {i}] {src['title']}",
                f"URL: {src['url']}",
                f"{src['content']}",
            ]

        context_parts += [
            "",
            "=== END CONTEXT ===",
            "Use the above real-world context to make the blog accurate,",
            "current, and grounded. Cite sources naturally in the text.",
        ]

        return "\n".join(context_parts)