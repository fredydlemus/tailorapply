import os

from dotenv import load_dotenv

load_dotenv(override=True)

EXTRACT_MODEL = os.getenv("EXTRACT_MODEL", "gpt-5-nano")
GENERATE_MODEL = os.getenv("GENERATE_MODEL", "gpt-4.1-mini")

MAX_INPUT_CHARS = 8_000

REASON_MODEL = os.getenv("REASON_MODEL", "gpt-4.1-mini")

MUST_HAVE_WEIGHT = 1.0
NICE_TO_HAVE_WEIGHT = 0.4