"""Project configuration: paths, defaults, and environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env so future phases can read OPENAI_API_KEY without changes.
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
MOCK_POLICY_DIR = PROJECT_ROOT / "data" / "policies" / "mock"

CHUNK_SIZE = 900
CHUNK_OVERLAP = 150

CHROMA_PERSIST_DIR = PROCESSED_DATA_DIR / "chroma"
CHROMA_COLLECTION_NAME = "ai_governance_docs"
EMBEDDING_MODEL = "text-embedding-3-small"

CHAT_MODEL = "gpt-4o-mini"
CHAT_TEMPERATURE = 0

USE_LANGGRAPH = os.getenv("USE_LANGGRAPH", "true").lower() == "true"
USE_LLM_PARSER = os.getenv("USE_LLM_PARSER", "true").lower() == "true"
LLM_PARSER_MODEL = os.getenv("LLM_PARSER_MODEL", CHAT_MODEL)
THREAD_PERSISTENCE = os.getenv("THREAD_PERSISTENCE", "false").lower() == "true"
AGENT_THREADS_PATH = PROCESSED_DATA_DIR / "agent_threads.json"
