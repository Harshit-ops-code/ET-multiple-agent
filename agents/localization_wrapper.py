import subprocess
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

class LocalizationWrapper:
    def __init__(self):
        # Resolve the binary relative to the project, not the caller's cwd.
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.binary_path = os.path.join(project_root, "engine", "localization_agent.exe")

    def localize(self, final_blog: str, target_languages: list) -> dict:
        print(f"\n[LocalizationWrapper] Offloading to C++ engine for: {target_languages}")
        
        if not os.path.exists(self.binary_path):
            print("[LocalizationWrapper] ERROR: C++ binary not found. Did you compile it?")
            return {}

        results = {}
        try:
            langs_str = ",".join(target_languages)
            
            process = subprocess.Popen(
                [self.binary_path, langs_str],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8"
            )
            
            stdout, stderr = process.communicate(input=final_blog, timeout=30)
            
            if process.returncode != 0:
                print(f"[LocalizationWrapper] C++ Engine Error: {stderr}")
                return {}
            
            # C++ simulated engine succeeded. For the ultimate hackathon demo, 
            # let's generate the REAL translation using the LLM in the payload!
            from langchain_groq import ChatGroq
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser
            from config import GROQ_API_KEY, GROQ_MODEL
            
            def translate_one(lang: str) -> tuple[str, str]:
                print(f"[LocalizationWrapper] Generating real AI translation for {lang}...")
                llm = ChatGroq(api_key=GROQ_API_KEY, model_name=GROQ_MODEL, temperature=0.3)
                prompt = ChatPromptTemplate.from_messages([
                    ("system", f"You are a professional localization expert. Translate the following content into {lang}. Preserve all markdown formatting flawlessly."),
                    ("human", "{blog}")
                ])
                chain = prompt | llm | StrOutputParser()
                return lang, chain.invoke({"blog": final_blog})

            max_workers = min(4, max(1, len(target_languages)))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(translate_one, lang) for lang in target_languages]
                for future in as_completed(futures):
                    lang, translated = future.result()
                    results[lang] = translated
            print(f"[LocalizationWrapper] Successfully retrieved {len(results)} translations.")
            return results

        except Exception as e:
            print(f"[LocalizationWrapper] Integration failure: {e}")
            return {}
