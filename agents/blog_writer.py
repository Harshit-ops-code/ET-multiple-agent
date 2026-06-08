from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import GROQ_API_KEY, GROQ_MODEL, OUTPUT_DIR, BRAND_NAME
from agents.web_search import WebSearchAgent 
from prompts.blog_writer_prompt import (
    SYSTEM_PROMPT_NEWS,
    HUMAN_TEMPLATE_NEWS,
)
from agents.llm_fallback import run_llm_with_fallback
import os
import re
from datetime import datetime


class BlogWriterAgent:
    """
    Phase 1 Agent: Generates a full structured blog post given a topic.
    Uses Groq (LLaMA3-70B) via LangChain for maximum output quality.
    Falls back to mock generation if network is restricted.
    """

    def __init__(self):
        # Lazy initialization - don't create LLM instance until needed
        self.llm = None
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT_NEWS),
            ("human", HUMAN_TEMPLATE_NEWS),
        ])
        self.chain = None
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def _initialize_llm(self):
        """Lazy initialize LLM to avoid network access during __init__"""
        if self.llm is None:
            try:
                self.llm = ChatGroq(
                    api_key=GROQ_API_KEY,
                    model_name=GROQ_MODEL,
                    temperature=0.7,        # creative but controlled
                    max_tokens=4096,
                )
                self.chain = self.prompt | self.llm | StrOutputParser()
            except Exception as e:
                print(f"[BlogWriterAgent] Failed to initialize ChatGroq: {e}")
                # Will use fallback in run_llm_with_fallback
                self.llm = None

    def generate(
        self,
        topic: str,
        audience: str = "general professional audience",
        length: int = 1000,
        use_web_search: bool = True,           # toggle search on/off
    ) -> dict:
        print(f"\n[BlogWriterAgent] Generating blog on: '{topic}'")
        
        # Lazy initialize LLM (avoids network access during __init__)
        self._initialize_llm()

        search_results = {"context": "", "sources": [], "tavily_answer": ""}

        if use_web_search:
            searcher = WebSearchAgent()
            search_results = searcher.search(topic)

        raw_output = run_llm_with_fallback(
            prompt_template=self.prompt,
            inputs={
                "topic":    topic,
                "audience": audience,
                "length":   length,
                "context":  search_results["context"],
                "brand_name": BRAND_NAME,
            },
            groq_llm=self.llm,
            temperature=0.7,
            max_tokens=4096
        )

        parsed = self._parse_output(raw_output)
        parsed["sources"] = search_results["sources"]       # attach sources
        parsed["tavily_answer"] = search_results.get("tavily_answer", "")
        self._save_blog(parsed, topic)

        print(f"[BlogWriterAgent] Done. Title: {parsed.get('title', 'Untitled')}")
        return parsed

    def _parse_output(self, raw: str) -> dict:
        """
        Extract structured fields from the model's formatted output.
        Falls back gracefully if the model doesn't follow format exactly.
        """
        result = {"raw": raw, "content": raw}

        title_match    = re.search(r"TITLE:\s*(.+)", raw)
        meta_match     = re.search(r"META_DESCRIPTION:\s*(.+)", raw)
        time_match     = re.search(r"READING_TIME:\s*(.+)", raw)
        keywords_match = re.search(r"SEO_KEYWORDS:\s*(.+)", raw)

        if title_match:
            result["title"] = title_match.group(1).strip()
        if meta_match:
            result["meta_description"] = meta_match.group(1).strip()
        if time_match:
            result["reading_time"] = time_match.group(1).strip()
        if keywords_match:
            result["seo_keywords"] = [
                k.strip() for k in keywords_match.group(1).split(",")
            ]

        # Extract main Markdown content (between the --- separators)
        parts = raw.split("---")
        if len(parts) >= 3:
            content = parts[2].strip()
            result["content"] = self._clean_links(content)   # ← called here
        else:
            # Fallback — clean the whole raw output if no separators found
            result["content"] = self._clean_links(raw)

        return result

    def _clean_links(self, content: str) -> str:
        """
        Keep max 3 markdown links. Convert the rest to plain text.
        e.g. [Daily Mail](https://...) → Daily Mail
        """
        import re
        links_found = re.findall(r'\[([^\]]+)\]\(https?://[^\)]+\)', content)

        if len(links_found) <= 3:
            return content  # already fine, nothing to clean

        count = 0

        def replace_link(match):
            nonlocal count
            count += 1
            if count <= 3:
                return match.group(0)   # keep first 3 as full links
            return match.group(1)       # strip URL, keep anchor text only

        cleaned = re.sub(r'\[([^\]]+)\]\(https?://[^\)]+\)', replace_link, content)
        return cleaned

    def _save_blog(self, parsed: dict, topic: str):
        """Save the blog to disk as a markdown file."""
        safe_topic = re.sub(r"[^\w\s-]", "", topic).strip().replace(" ", "_")[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{OUTPUT_DIR}/{timestamp}_{safe_topic}.md"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {parsed.get('title', topic)}\n\n")
            if "meta_description" in parsed:
                f.write(f"> {parsed['meta_description']}\n\n")
            f.write(parsed.get("content", parsed["raw"]))

        print(f"[BlogWriterAgent] Saved to: {filename}")