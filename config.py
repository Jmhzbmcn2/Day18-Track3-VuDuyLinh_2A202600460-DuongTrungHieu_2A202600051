"""Shared configuration for Lab 18."""

import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", OPENAI_API_KEY)

# Set local LLM as OpenAI Base URL for LangChain/Ragas compatibility
_llm_host = os.getenv("LLM_BINDING_HOST", "http://localhost:8000/v1")
os.environ["OPENAI_API_BASE"] = _llm_host
os.environ["OPENAI_API_KEY"] = OPENROUTER_API_KEY or "local"

# --- Generative Model ---
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ")
LLM_BINDING_HOST = os.getenv("LLM_BINDING_HOST", "http://localhost:8000/v1")

# --- Qdrant ---
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "lab18_production"
NAIVE_COLLECTION = "lab18_naive"

# --- Embedding ---
EMBEDDING_MODEL = "embeddinggemma:300m"
EMBEDDING_DIM = 768
OLLAMA_API_URL = "http://localhost:11434/api/embeddings"

# --- Chunking ---
HIERARCHICAL_PARENT_SIZE = 2048
HIERARCHICAL_CHILD_SIZE = 256
SEMANTIC_THRESHOLD = 0.85

# --- Search ---
BM25_TOP_K = 20
DENSE_TOP_K = 20
HYBRID_TOP_K = 20
RERANK_TOP_K = 3

# --- Reranker ---
RERANKER_HOST = os.getenv("RERANKER_HOST", "http://localhost:7997")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "Qwen/Qwen3-Reranker-0.6B")

# --- Paths ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TEST_SET_PATH = os.path.join(os.path.dirname(__file__), "test_set.json")
