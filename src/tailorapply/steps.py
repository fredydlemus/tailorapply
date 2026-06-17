import re
import difflib

from .config import EXTRACT_MODEL, MAX_INPUT_CHARS
from .llm_client import call_json
from .prompts import JOB_EXTRACTION_SYSTEM_PROMPT, build_job_extraction_user_prompt, build_cv_extraction_user_prompt, CV_EXTRACTION_SYSTEM_PROMPT
from .schemas import JobProfile, Requirement, CVProfile

def _normalize(text: str) -> str:
    return " ".join(text.split()).lower()

def appears_as_phrase(claim: str, source: str) -> bool:
    nc, ns = _normalize(claim), _normalize(source)
    if not nc:
        return True
    if re.search(rf"\b{re.escape(nc)}\b", ns):
        return True
    if re.search(r"[^\w\s]", nc):
        return nc in ns
    return False

def appears_verbatim_ish(claim: str, source: str, threshold: float = 0.85) -> bool:
    nc, ns = _normalize(claim), _normalize(source)
    if not nc:
        return True
    if nc in ns:
        return True
    match = difflib.SequenceMatcher(None, nc, ns).find_longest_match(
        0, len(nc), 0, len(ns)
    )
    return (match.size / len(nc)) >= threshold

def extract_job_profile(job_text: str) -> JobProfile:
    user_prompt = build_job_extraction_user_prompt(job_text[:MAX_INPUT_CHARS])
    return call_json(
        system_prompt=JOB_EXTRACTION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema=JobProfile,
        model=EXTRACT_MODEL
    )

def verify_grouding(profile: JobProfile, job_text: str) -> list[Requirement]:
    return [r for r in profile.requirements if not appears_verbatim_ish(r.quote, job_text)]

def extract_cv_profile(cv_text: str) -> CVProfile:
    user_prompt = build_cv_extraction_user_prompt(cv_text[:MAX_INPUT_CHARS])
    return call_json(
        system_prompt=CV_EXTRACTION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema=CVProfile,
        model=EXTRACT_MODEL,
    )

def verify_cv_grounding(profile: CVProfile, cv_text: str) -> dict[str, list[str]]:
    ungrounded_skills = [s for s in profile.skills if not appears_as_phrase(s, cv_text)]
    ungrounded_bullets = [
        b
        for exp in profile.experiences
        for b in exp.bullets
        if not appears_verbatim_ish(b, cv_text)
    ]
    return {"skills": ungrounded_skills, "bullets": ungrounded_bullets}