from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from rag.chroma_store import upsert_documents, query_collection, delete_collection
from config import GROQ_API_KEY, GROQ_MODEL
import re
import uuid


VALIDATOR_SYSTEM_PROMPT = """
You are a rigorous fact-checking editor. You verify blog content 
against provided source material and identify any inaccuracies,
unsupported claims, or hallucinations.

For each claim you check, you will have access to relevant source chunks.
Be precise and fair — only flag something as wrong if the sources 
clearly contradict it, or if it's a specific factual claim with no 
source backing it at all.

Return your analysis in EXACTLY this format:
---
ACCURACY_SCORE: [0-100]
VERDICT: [PASS / NEEDS_REVISION / FAIL]
ISSUES:
- [issue 1, if any]
- [issue 2, if any]
SUGGESTIONS:
- [concrete fix 1]
- [concrete fix 2]
SUMMARY: [1-2 sentence overall assessment]
---
"""

VALIDATOR_HUMAN_TEMPLATE = """
BLOG TO VALIDATE:
{blog_content}

RELEVANT SOURCE MATERIAL (retrieved from ChromaDB):
{source_chunks}

BLOG MODE: {mode}

Instructions:
- For NEWS mode: every specific stat, quote, or dated claim must be traceable to a source
- For PRODUCT mode: check that feature claims are consistent with the product details provided
- Flag any claim that sounds invented or overly specific without source backing
- Do NOT penalize for general knowledge or commonly known facts
- Be constructive — suggest exact fixes, not just problems
"""


class RAGValidator:
    """
    Embeds blog + sources into ChromaDB, retrieves relevant
    chunks per blog section, and uses Groq to fact-check.
    """

    def __init__(self):
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=GROQ_MODEL,
            temperature=0.1,    # low temp for analytical precision
            max_tokens=2048,
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", VALIDATOR_SYSTEM_PROMPT),
            ("human",  VALIDATOR_HUMAN_TEMPLATE),
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()

    def validate(self, blog_content: str, sources: list, mode: str, topic: str) -> dict:
        """
        Full validation pipeline:
        1. Embed sources into ChromaDB (session collection)
        2. Split blog into sections
        3. Retrieve relevant chunks per section
        4. LLM fact-checks against retrieved chunks
        5. Return structured result
        """
        print(f"\n[RAGValidator] Starting validation — mode={mode}")

        # Use a fresh collection per validation run (no stale data)
        collection_name = f"validation_{uuid.uuid4().hex[:8]}"

        try:
            # Step 1: Embed all source material
            if sources:
                self._embed_sources(collection_name, sources, mode, topic)

            # Step 2: Split blog into meaningful chunks
            blog_sections = self._split_blog(blog_content)

            # Step 3: Retrieve relevant source chunks for the whole blog
            source_chunks = self._retrieve_chunks(
                collection_name, blog_content, n_results=5
            )

            # Step 4: LLM validates
            source_text = self._format_chunks(source_chunks)

            raw_result = self.chain.invoke({
                "blog_content":  blog_content[:3000],  # cap for token limit
                "source_chunks": source_text or "No external sources available.",
                "mode":          mode,
            })

            parsed = self._parse_result(raw_result)
            parsed["raw_validator_output"] = raw_result
            parsed["chunks_used"] = len(source_chunks)

            print(f"[RAGValidator] Score={parsed['accuracy_score']} Verdict={parsed['verdict']}")
            return parsed

        finally:
            # Always clean up the temp collection
            delete_collection(collection_name)

    def _embed_sources(self, collection_name: str, sources: list,
                       mode: str, topic: str):
        """Embed all source articles into ChromaDB."""
        documents = []

        for i, src in enumerate(sources):
            text = f"{src.get('title','')}\n\n{src.get('content','')}"
            if text.strip():
                documents.append({
                    "id":       f"source_{i}",
                    "text":     text,
                    "metadata": {
                        "url":    src.get("url", ""),
                        "source": src.get("source", "web"),
                        "title":  src.get("title", ""),
                        "mode":   mode,
                        "topic":  topic,
                    }
                })

        # For product mode, embed the product details as a "source"
        if mode == "product":
            product_text = "\n".join([
                f"Product: {topic}",
                f"Details: {sources[0].get('product_details','') if sources else ''}",
            ])
            documents.append({
                "id":       "product_spec",
                "text":     product_text,
                "metadata": {"source": "product_spec", "mode": "product", "topic": topic, "url": ""},
            })

        if documents:
            upsert_documents(collection_name, documents)
            print(f"[RAGValidator] Embedded {len(documents)} source documents")

    def _split_blog(self, blog: str) -> list[str]:
        """Split blog into sections by headings or paragraph groups."""
        sections = re.split(r'\n#{1,3} ', blog)
        # Further split long sections into ~300 word chunks
        chunks = []
        for section in sections:
            words = section.split()
            for i in range(0, len(words), 300):
                chunk = " ".join(words[i:i+300])
                if chunk.strip():
                    chunks.append(chunk)
        return chunks

    def _retrieve_chunks(self, collection_name: str,
                         query: str, n_results: int = 5) -> list:
        """Retrieve most relevant source chunks for fact-checking."""
        return query_collection(collection_name, query, n_results=n_results)

    def _format_chunks(self, chunks: list) -> str:
        if not chunks:
            return ""
        lines = []
        for i, chunk in enumerate(chunks, 1):
            meta = chunk.get("metadata", {})
            src  = meta.get("source", "unknown")
            url  = meta.get("url", "")
            dist = chunk.get("distance", 1.0)
            relevance = f"{(1 - dist)*100:.0f}%"
            lines.append(
                f"[Chunk {i} | Source: {src} | Relevance: {relevance}]\n"
                f"{chunk['text'][:400]}\n"
                f"URL: {url}\n"
            )
        return "\n".join(lines)

    def _parse_result(self, raw: str) -> dict:
        result = {
            "accuracy_score": 75,
            "verdict":        "PASS",
            "issues":         [],
            "suggestions":    [],
            "summary":        "",
        }

        score_match   = re.search(r"ACCURACY_SCORE:\s*(\d+)", raw)
        verdict_match = re.search(r"VERDICT:\s*(PASS|NEEDS_REVISION|FAIL)", raw)
        summary_match = re.search(r"SUMMARY:\s*(.+?)(?:\n|$)", raw, re.DOTALL)

        if score_match:
            result["accuracy_score"] = int(score_match.group(1))
        if verdict_match:
            result["verdict"] = verdict_match.group(1)
        if summary_match:
            result["summary"] = summary_match.group(1).strip()

        # Parse bullet lists
        issues_block = re.search(r"ISSUES:\n(.*?)(?:SUGGESTIONS:|$)", raw, re.DOTALL)
        if issues_block:
            result["issues"] = [
                line.lstrip("- ").strip()
                for line in issues_block.group(1).strip().split("\n")
                if line.strip() and line.strip() != "-"
            ]

        suggestions_block = re.search(r"SUGGESTIONS:\n(.*?)(?:SUMMARY:|$)", raw, re.DOTALL)
        if suggestions_block:
            result["suggestions"] = [
                line.lstrip("- ").strip()
                for line in suggestions_block.group(1).strip().split("\n")
                if line.strip() and line.strip() != "-"
            ]

        return result