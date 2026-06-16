import os

from dotenv import load_dotenv

load_dotenv(override=True)

EXTRACT_MODEL = os.getenv("EXTRACT_MODEL", "gpt-5-nano")
GENERATE_MODEL = os.getenv("GENERATE_MODEL", "gpt-4.1-mini")

MAX_INPUT_CHARS = 8_000