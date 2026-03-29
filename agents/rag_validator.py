from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from rag.chroma_store import upsert_documents, query_collection, delete_collection
from config import GROQ_API_KEY, GROQ_MODEL
from prompts.rag_validator_prompt import (
    RAG_VALIDATOR_SYSTEM_PROMPT,
    RAG_VALIDATOR_HUMAN_TEMPLATE,
)
import re
import uuid


class RAGValidator:
    """
    Embeds blog + sources into ChromaDB, retrieves relevant
    chunks per blog section, and uses Groq to fact-check.
    """

    def __init__(self):
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=GROQ_MODEL,
            temperature=0.1,
            max_tokens=2048,
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", RAG_VALIDATOR_SYSTEM_PROMPT),
            ("human", RAG_VALIDATOR_HUMAN_TEMPLATE),
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()

    def validate(self, blog_content: str, sources: list, mode: str, topic: str) -> dict:
        """
        Full validation pipeline:
        1. Embed sources into ChromaDB (session collection)
        2. Retrieve relevant chunks for the generated blog
        3. LLM fact-checks against retrieved chunks
        4. Return structured result
        """
        print(f"\n[RAGValidator] Starting validation - mode={mode}")

        collection_name = f"validation_{uuid.uuid4().hex[:8]}"

        try:
            if sources:
                self._embed_sources(collection_name, sources, mode, topic)

            source_chunks = self._retrieve_chunks(
                collection_name, blog_content, n_results=5
            )
            source_text = self._format_chunks(source_chunks)

            raw_result = self.chain.invoke({
                "generated_content": blog_content[:3000],
                "context_chunks": source_text or "No external sources available.",
            })

            parsed = self._parse_result(raw_result)
            parsed["raw_validator_output"] = raw_result
            parsed["chunks_used"] = len(source_chunks)

            print(f"[RAGValidator] Score={parsed['accuracy_score']} Verdict={parsed['verdict']}")
            return parsed

        finally:
            delete_collection(collection_name)

    def _embed_sources(self, collection_name: str, sources: list,
                       mode: str, topic: str):
        """Embed all source articles into ChromaDB."""
        documents = []

        for i, src in enumerate(sources):
            text = f"{src.get('title', '')}\n\n{src.get('content', '')}"
            if text.strip():
                documents.append({
                    "id": f"source_{i}",
                    "text": text,
                    "metadata": {
                        "url": src.get("url", ""),
                        "source": src.get("source", "web"),
                        "title": src.get("title", ""),
                        "mode": mode,
                        "topic": topic,
                    }
                })

        if mode == "product":
            product_text = "\n".join([
                f"Product: {topic}",
                f"Details: {sources[0].get('product_details', '') if sources else ''}",
            ])
            documents.append({
                "id": "product_spec",
                "text": product_text,
                "metadata": {"source": "product_spec", "mode": "product", "topic": topic, "url": ""},
            })

        if documents:
            upsert_documents(collection_name, documents)
            print(f"[RAGValidator] Embedded {len(documents)} source documents")

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
            src = meta.get("source", "unknown")
            url = meta.get("url", "")
            dist = chunk.get("distance", 1.0)
            relevance = f"{(1 - dist) * 100:.0f}%"
            lines.append(
                f"[Chunk {i} | Source: {src} | Relevance: {relevance}]\n"
                f"{chunk['text'][:400]}\n"
                f"URL: {url}\n"
            )
        return "\n".join(lines)

    def _parse_result(self, raw: str) -> dict:
        result = {
            "accuracy_score": 75,
            "verdict": "PASS",
            "issues": [],
            "suggestions": [],
            "summary": "",
        }

        score_match = re.search(r"CITATION_ACCURACY_SCORE:\s*(\d+)", raw)
        verdict_match = re.search(r"GATE_SIGNAL:\s*(PASS|NEEDS_FIX|REJECT)", raw)
        summary_match = re.search(r"VALIDATOR_SUMMARY:\s*(.+?)(?:\n|$)", raw, re.DOTALL)

        if not score_match:
            score_match = re.search(r"ACCURACY_SCORE:\s*(\d+)", raw)
        if not verdict_match:
            verdict_match = re.search(r"VERDICT:\s*(PASS|NEEDS_REVISION|FAIL)", raw)
        if not summary_match:
            summary_match = re.search(r"SUMMARY:\s*(.+?)(?:\n|$)", raw, re.DOTALL)

        if score_match:
            result["accuracy_score"] = int(score_match.group(1))
        if verdict_match:
            result["verdict"] = verdict_match.group(1)
        if summary_match:
            result["summary"] = summary_match.group(1).strip()

        flagged_claims = re.findall(
            r'CLAIM:\s*"(.+?)"\s+STATUS:\s*(UNSUPPORTED|CONTRADICTED)\s+ISSUE:\s*(.+?)\s+SUGGESTED_FIX:\s*(.+?)(?=\n-\s+CLAIM:|\nVALIDATOR_SUMMARY:|$)',
            raw,
            re.DOTALL,
        )
        if flagged_claims:
            result["issues"] = [
                f'{status}: "{claim}" -> {issue.strip()}'
                for claim, status, issue, _fix in flagged_claims
            ]
            result["suggestions"] = [fix.strip() for _claim, _status, _issue, fix in flagged_claims]
        else:
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

        if result["verdict"] == "NEEDS_FIX":
            result["verdict"] = "NEEDS_REVISION"
        elif result["verdict"] == "REJECT":
            result["verdict"] = "FAIL"

        return result
