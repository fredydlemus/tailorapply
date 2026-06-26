from collections.abc import Iterator
import re
import difflib
from unicodedata import category

from .config import EXTRACT_MODEL, MAX_INPUT_CHARS, REASON_MODEL, MUST_HAVE_WEIGHT, NICE_TO_HAVE_WEIGHT, GENERATE_MODEL
from .llm_client import call_json, call_stream
from .prompts import (
    JOB_EXTRACTION_SYSTEM_PROMPT, 
    build_job_extraction_user_prompt, 
    build_cv_extraction_user_prompt, 
    CV_EXTRACTION_SYSTEM_PROMPT, 
    GAP_ANALYSIS_SYSTEM_PROMPT, 
    build_gap_analysis_user_prompt, 
    build_cover_letter_user_prompt, 
    build_letter_system_prompt,
    EVALUATOR_SYSTEM_PROMPT,
    build_evaluation_user_prompt
    )
from .schemas import JobProfile, Requirement, CVProfile, GapAnalysis, GapAnalysisLLM, Evaluation

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


_STATUS_VALUE = {"strong_match": 1.0, "partial_match": 0.5, "gap": 0.0}

def _compute_fit_score(llm_result: GapAnalysisLLM, job: JobProfile) -> tuple[int, str]:
    category_by_skill = {r.skill: r.category for r in job.requirements}
    weighted_sum = weight_total = 0.0
    must_total = must_covered = 0
    for m in llm_result.matches:
        category = category_by_skill.get(m.requirement)
        if category is None:
            continue
        weight = MUST_HAVE_WEIGHT if category == "must_have" else NICE_TO_HAVE_WEIGHT
        weighted_sum += weight * _STATUS_VALUE[m.status]
        weight_total += weight
        if category == "must_have":
            must_total += 1
            must_covered += m.status != "gap"
    score = round(100 * weighted_sum / weight_total) if weight_total else 0
    return score, f"{must_covered}/{must_total}"

def analyze_gaps(job: JobProfile, cv: CVProfile) -> GapAnalysis:
    llm_result = call_json(
        system_prompt=GAP_ANALYSIS_SYSTEM_PROMPT,
        user_prompt=build_gap_analysis_user_prompt(
            job.model_dump_json(indent=2), cv.model_dump_json(indent=2)
        ),
        schema=GapAnalysisLLM,
        model=REASON_MODEL
    )
    score, coverage = _compute_fit_score(llm_result, job)
    return GapAnalysis(
        fit_score=score,
        must_have_coverage=coverage,
        matches=llm_result.matches,
        missing_keywords=llm_result.missing_keywords,
        honest_summary=llm_result.honest_summary
    )

def verify_gap_analysis(
    analysis: GapAnalysis, job: JobProfile, cv: CVProfile
) -> dict[str, list[str]]:
    cv_source = " \n ".join(cv.skills + [b for e in cv.experiences for b in e.bullets] + cv.certifications)
    job_skills = {r.skill for r in job.requirements}
    matched_skills = {m.requirement for m in analysis.matches}

    inconsistent, ungrounded_evidence = [], []
    for m in analysis.matches:
        has_evidence = bool(m.evidence_from_cv and m.evidence_from_cv.strip())
        if m.status in ("strong_match", "partial_match") and not has_evidence:
            inconsistent.append(f"{m.requirement}: '{m.status}' without evidence")
        if m.status == "gap" and has_evidence:
            inconsistent.append(f"{m.requirement}: 'gap' but bring evidence")
        if has_evidence and not appears_verbatim_ish(m.evidence_from_cv, cv_source):
            ungrounded_evidence.append(f'{m.requirement}: "{m.evidence_from_cv}"')

    return {
        "uncovered_requirements": sorted(job_skills - matched_skills),
        "unknown_requirements": sorted(matched_skills - job_skills),
        "inconsistent_status": inconsistent,
        "ungrounded_evidence": ungrounded_evidence,
    }

def generate_cover_letter(analysis: GapAnalysis, job: JobProfile, tone: str = "formal", feedback: str = "") -> Iterator[str]:
    yield from call_stream(
        system_prompt=build_letter_system_prompt(tone),
        user_prompt=build_cover_letter_user_prompt(job.model_dump_json(indent=2), analysis.model_dump_json(indent=2), feedback),
        model=GENERATE_MODEL
    )

def flag_letter_concerns(letter: str, analysis: GapAnalysis) -> list[str]:
    norm = _normalize(letter)
    flags = []
    for m in analysis.matches:
        if m.status != "gap":
            continue
        tokens = [t for t in _normalize(m.requirement).split() if len(t) > 2]
        if any(re.search(rf"\b{re.escape(t)}\b", norm) for t in tokens):
            flags.append(
                f"mentions the gap '{m.requirement}': verify that it is handled "
                "honestly, not as an experience"
            )
    return flags

def evaluate_letter(letter: str, analysis: GapAnalysis, job: JobProfile) -> Evaluation:
    return call_json(
        system_prompt=EVALUATOR_SYSTEM_PROMPT,
        user_prompt=build_evaluation_user_prompt(
            letter, job.model_dump_json(indent=2), analysis.model_dump_json(indent=2)
        ),
        schema=Evaluation,
        model=REASON_MODEL
    )

def verify_evaluation(evaluation: Evaluation) -> list[str]:
    problems = []
    if evaluation.verdict == "approve" and evaluation.grounding_issues:
        problems.append("verdict 'approve' but there are grounding_issues")
    if(
        evaluation.verdict == "revise"
        and not evaluation.grounding_issues
        and not evaluation.notes_for_revision.strip()
    ):
        problems.append("'Revise' verdict, but with no issues or actionable notes.")
    return problems

def _build_revision_feedback(previous_letter: str, evaluation: Evaluation) -> str:
    issues = "\n".join(f"- {i}" for i in evaluation.grounding_issues) or "none"
    missed = "\n".join(f"- {s}" for s in evaluation.missed_strengths) or "(none)"
    return(
        f"Previous draft:\n{previous_letter}\n\n"
        f"Grounding issues detected:\n{issues}\n\n"
        f"Untapped strengths:\n{missed}\n\n"
        f"Instructions for making corrections:\n{evaluation.notes_for_revision}"
    )

def tailor_cover_letter(analysis: GapAnalysis, job: JobProfile, tone: str = "formal", max_revisions: int = 2) -> tuple[str, list[Evaluation]]:
    evaluations: list[Evaluation] = []
    feedback = ""
    letter = ""

    for _ in range(max_revisions + 1):
        letter = "".join(generate_cover_letter(analysis, job, tone=tone, feedback=feedback))
        evaluation = evaluate_letter(letter, analysis, job)
        evaluations.append(evaluation)
        if evaluation.verdict == "approve":
            break
        feedback = _build_revision_feedback(letter, evaluation)
    return letter, evaluations