from .config import EXTRACT_MODEL, MAX_INPUT_CHARS
from .llm_client import call_json
from .prompts import JOB_EXTRACTION_SYSTEM_PROMPT, build_job_extraction_user_prompt
from .schemas import JobProfile, Requirement

def extract_job_profile(job_text: str) -> JobProfile:
    user_prompt = build_job_extraction_user_prompt(job_text[:MAX_INPUT_CHARS])
    return call_json(
        system_prompt=JOB_EXTRACTION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema=JobProfile,
        model=EXTRACT_MODEL
    )

def verify_grouding(profile: JobProfile, job_text: str) -> list[Requirement]:
    normalized_source = " ".join(job_text.split()).lower()
    return [
        r
        for r in profile.requirements
        if " ".join(r.quote.split()).lower() not in normalized_source
    ]