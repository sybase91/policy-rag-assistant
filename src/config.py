"""Project configuration: paths, defaults, and environment variables."""

from pathlib import Path

from dotenv import load_dotenv

# Load .env so future phases can read OPENAI_API_KEY without changes.
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
