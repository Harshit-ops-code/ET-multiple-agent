import subprocess
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from config import GROQ_API_KEY, GROQ_MODEL

class LocalizationWrapper:
    def __init__(self):
        # Resolve the binary relative to the project, not the caller's cwd.
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.binary_path = os.path.join(project_root, "engine", "localization_agent.exe")

    def localize(self, final_blog: str, target_languages: list) -> dict:
        print(f"\n[LocalizationWrapper] Offloading to C++ engine for: {target_languages}")

        results = {}
        try:
            self._ping_cpp_engine(final_blog, target_languages)
            results = self._translate_parallel(final_blog, target_languages)
            print(f"[LocalizationWrapper] Successfully retrieved {len(results)} translations.")
            return results

        except Exception as e:
            print(f"[LocalizationWrapper] Integration failure: {e}")
            return {}

    def _ping_cpp_engine(self, final_blog: str, target_languages: list) -> None:
        if not os.path.exists(self.binary_path):
            print("[LocalizationWrapper] C++ binary not found. Falling back to Groq-only translation.")
            return

        langs_str = ",".join(target_languages)
        process = subprocess.Popen(
            [self.binary_path, langs_str],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

        stdout, stderr = process.communicate(input=final_blog, timeout=30)
        if process.returncode != 0:
            print(f"[LocalizationWrapper] C++ Engine Error: {stderr}")
        elif stdout.strip():
            print(f"[LocalizationWrapper] C++ engine acknowledged languages: {stdout.strip()}")

    def _translate_parallel(self, final_blog: str, target_languages: list) -> dict:
        def translate_one(lang: str) -> tuple[str, str]:
            print(f"[LocalizationWrapper] Generating real AI translation for {lang}...")
            llm = ChatGroq(api_key=GROQ_API_KEY, model_name=GROQ_MODEL, temperature=0.2)
            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    f"You are a professional localization expert. Translate the following content into {lang}. Preserve markdown formatting, headings, bullets, and links exactly. Do not add commentary.",
                ),
                ("human", "{blog}"),
            ])
            chain = prompt | llm | StrOutputParser()
            return lang, chain.invoke({"blog": final_blog})

        results = {}
        max_workers = min(4, max(1, len(target_languages)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(translate_one, lang) for lang in target_languages]
            for future in as_completed(futures):
                lang, translated = future.result()
                results[lang] = translated
        return results
