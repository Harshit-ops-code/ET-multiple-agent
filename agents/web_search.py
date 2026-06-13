from tavily import TavilyClient
from newsapi import NewsApiClient
from config import TAVILY_API_KEY, NEWSAPI_KEY
from datetime import datetime, timedelta
import socket


class WebSearchAgent:
    """
    Multi-source search: Tavily (deep web) + NewsAPI (live headlines).
    Only used in NEWS mode — product mode skips this.
    Gracefully handles network failures when behind restrictive firewalls.
    """

    def __init__(self):
        self.tavily = None
        self.newsapi = None
        self.network_available = True
        
        try:
            if TAVILY_API_KEY and TAVILY_API_KEY != "your_tavily_api_key_here":
                self.tavily = TavilyClient(api_key=TAVILY_API_KEY)
        except Exception as e:
            print(f"[WebSearchAgent] Tavily initialization warning: {e}")
        
        try:
            if NEWSAPI_KEY and NEWSAPI_KEY != "your_newsapi_key_here":
                self.newsapi = NewsApiClient(api_key=NEWSAPI_KEY)
        except Exception as e:
            print(f"[WebSearchAgent] NewsAPI initialization warning: {e}")

    def _is_network_error(self, e: Exception) -> bool:
        msg = str(e).lower()
        return any(term in msg for term in ["connection", "socket", "timeout", "refused", "10013", "unreachable", "getaddrinfo"])

    def search(self, topic: str, max_results: int = 5) -> dict:
        print(f"\n[WebSearchAgent] Searching: '{topic}'")
        
        if not self.network_available:
            print(f"[WebSearchAgent] ⚠️  Network access unavailable (firewall/restrictions)")
            print(f"[WebSearchAgent] Using empty context. LLM will generate without web context.")
            return {"context": "", "sources": [], "tavily_answer": ""}

        tavily_data, tavily_answer = self._search_tavily(topic, max_results)
        newsapi_data = self._search_newsapi(topic)

        # Merge and deduplicate by URL
        all_sources = {s["url"]: s for s in tavily_data + newsapi_data}
        sources = list(all_sources.values())[:8]

        context = self._build_context(topic, sources)
        print(f"[WebSearchAgent] Found {len(sources)} sources total")
        return {"context": context, "sources": sources, "tavily_answer": tavily_answer}

    def _search_tavily(self, topic: str, max_results: int) -> tuple:
        if not self.tavily:
            return [], ""
        try:
            res = self.tavily.search(
                query=topic,
                search_depth="advanced",
                max_results=max_results,
                include_answer=True,
            )
            sources = [{
                "title":   r.get("title", ""),
                "url":     r.get("url", ""),
                "content": r.get("content", "")[:500],
                "source":  "Tavily",
                "score":   r.get("score", 0),
            } for r in res.get("results", [])]
            return sources, res.get("answer", "")
        except Exception as e:
            print(f"[WebSearchAgent] Tavily error: {e}")
            if self._is_network_error(e):
                print("[WebSearchAgent] Network issue detected during Tavily search. Disabling search network access.")
                self.network_available = False
            return [], ""

    def _search_newsapi(self, topic: str) -> list:
        if not self.newsapi:
            return []
        try:
            from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            res = self.newsapi.get_everything(
                q=topic,
                from_param=from_date,
                language="en",
                sort_by="relevancy",
                page_size=5,
            )
            return [{
                "title":   a.get("title", ""),
                "url":     a.get("url", ""),
                "content": (a.get("description") or "")[:500],
                "source":  a.get("source", {}).get("name", "NewsAPI"),
                "score":   0.8,
            } for a in res.get("articles", []) if a.get("title")]
        except Exception as e:
            print(f"[WebSearchAgent] NewsAPI error: {e}")
            if self._is_network_error(e):
                print("[WebSearchAgent] Network issue detected during NewsAPI search. Disabling search network access.")
                self.network_available = False
            return []

    def _build_context(self, topic: str, sources: list) -> str:
        today = datetime.now().strftime("%B %d, %Y")
        lines = [
            f"=== LIVE WEB CONTEXT (as of {today}) ===",
            f"Topic: {topic}", "",
            "RECENT SOURCES:",
        ]
        for i, s in enumerate(sources, 1):
            lines += [
                f"\n[{i}] {s['title']} — via {s['source']}",
                f"URL: {s['url']}",
                s["content"],
            ]
        lines += ["", "=== END CONTEXT ===",
                  "Cite sources naturally. Write as if today is " + today + "."]
        return "\n".join(lines)