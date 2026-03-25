from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

GROQ_MODEL = "llama-3.3-70b-versatile"      # best quality on Groq
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # local, fast, free
CHROMA_DB_PATH = "./rag/chroma_db"
OUTPUT_DIR = "./outputs/blogs"