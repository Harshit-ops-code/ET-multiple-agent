from dotenv import load_dotenv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
BYTEZ_API_KEY = os.getenv("BYTEZ_API_KEY")
BYTEZ_IMAGE_MODEL = os.getenv("BYTEZ_IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
BRAND_TONE        = "professional and authoritative"
BRAND_NAME        = "ET-AI"  # change to your actual brand name

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
MAX_REGENERATIONS = 3  # LangGraph retry limit

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # local, fast, free
CHROMA_DB_PATH = "./rag/chroma_db"
OUTPUT_DIR = "./outputs/blogs"
