from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from prompts.review_prompt import REVIEW_SYSTEM_PROMPT, REVIEW_HUMAN_TEMPLATE
from config import GROQ_API_KEY, GROQ_MODEL, BRAND_TONE, BRAND_NAME
import re


class ReviewAgent:
    """
    5-layer compliance review agent.
    Checks tone, legal, brand, accuracy, and policy.
    Returns structured verdict with specific fixes.
    """

    def __init__(self):
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=GROQ_MODEL,
            temperature=0.0,   # zero temp — we want deterministic compliance decisions
            max_tokens=2048,
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", REVIEW_SYSTEM_PROMPT),
            ("human",  REVIEW_HUMAN_TEMPLATE),
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()

    def review(self, content: str, mode: str) -> dict:
        print(f"\n[ReviewAgent] Running 5-layer compliance review...")

        raw = self.chain.invoke({
            "content":    content[:4000],  # cap for token safety
            "mode":       mode,
            "brand_tone": BRAND_TONE,
            "brand_name": BRAND_NAME,
            "source_context": "",
        })

        result = self._parse(raw)
        result["raw_review"] = raw

        verdict = result.get("overall_verdict", "NEEDS_FIX")
        score   = result.get("overall_score", 0)
        print(f"[ReviewAgent] Verdict={verdict} Score={score}/100")
        return result

    def _parse(self, raw: str) -> dict:
        result = {
            "tone_score":     self._extract_int(raw, "TONE_SCORE"),
            "tone_status":    self._extract_str(raw, "TONE_STATUS"),
            "tone_issues":    self._extract_list(raw, "TONE_ISSUES"),
            "legal_score":    self._extract_int(raw, "LEGAL_SCORE"),
            "legal_status":   self._extract_str(raw, "LEGAL_STATUS"),
            "legal_issues":   self._extract_list(raw, "LEGAL_ISSUES"),
            "brand_score":    self._extract_int(raw, "BRAND_SCORE"),
            "brand_status":   self._extract_str(raw, "BRAND_STATUS"),
            "brand_issues":   self._extract_list(raw, "BRAND_ISSUES"),
            "accuracy_score": self._extract_int(raw, "ACCURACY_SCORE"),
            "accuracy_status":self._extract_str(raw, "ACCURACY_STATUS"),
            "accuracy_issues":self._extract_list(raw, "ACCURACY_ISSUES"),
            "policy_score":   self._extract_int(raw, "POLICY_SCORE"),
            "policy_status":  self._extract_str(raw, "POLICY_STATUS"),
            "policy_issues":  self._extract_list(raw, "POLICY_ISSUES"),
            "overall_verdict":self._extract_str(raw, "OVERALL_VERDICT"),
            "overall_score":  self._extract_int(raw, "OVERALL_SCORE"),
            "editor_note":    self._extract_str(raw, "EDITOR_NOTE"),
            "fixes_required": self._extract_bullet_list(raw, "FIXES_REQUIRED"),
        }
        return result

    def _extract_int(self, text: str, key: str) -> int:
        m = re.search(rf"{key}:\s*(\d+)", text)
        return int(m.group(1)) if m else 0

    def _extract_str(self, text: str, key: str) -> str:
        m = re.search(rf"{key}:\s*(.+?)(?:\n|$)", text)
        return m.group(1).strip() if m else ""

    def _extract_list(self, text: str, key: str) -> list:
        m = re.search(rf"{key}:\s*(.+?)(?:\n|$)", text)
        if not m:
            return []
        val = m.group(1).strip()
        if val.upper() == "NONE" or not val:
            return []
        parts = re.split(r"\s+\|\s+|,\s*", val)
        return [v.strip() for v in parts if v.strip()]

    def _extract_bullet_list(self, text: str, key: str) -> list:
        m = re.search(rf"{key}:\n(.*?)(?:\n[A-Z_]+:|$)", text, re.DOTALL)
        if not m:
            return []
        lines = m.group(1).strip().split("\n")
        return [l.lstrip("- •").strip() for l in lines if l.strip() and l.strip() != "-"]
