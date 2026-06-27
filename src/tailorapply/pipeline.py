from dataclasses import dataclass

from .schemas import CVProfile, Evaluation, GapAnalysis, JobProfile
from .steps import (
    analyze_gaps,
    extract_cv_profile,
    extract_job_profile,
    tailor_cover_letter,
    verify_cv_grounding,
    verify_evaluation,
    verify_gap_analysis,
    verify_grounding,
)

@dataclass
class PipelineResult:
    job: JobProfile
    cv: CVProfile
    analysis: GapAnalysis
    letter: str
    evaluations: list[Evaluation]
    checks: dict

def _extraction_grounding_failed(checks: dict) -> bool:
    cv = checks["cv_grounding"]
    return bool(checks["job_grounding"] or cv["skills"] or cv["bullets"])

def run_pipeline(
    job_text: str,
    cv_text: str,
    tone: str = "formal",
    max_revisions: int = 2,
    strict: bool = False,
) -> PipelineResult:
    checks: dict = {}

    job = extract_job_profile(job_text)
    checks["job_grounding"] = verify_grounding(job, job_text)

    cv = extract_cv_profile(cv_text)
    checks["cv_grounding"] = verify_cv_grounding(cv, cv_text)

    if strict and _extraction_grounding_failed(checks):
        raise RuntimeError(
            "Extraction grounding failed (Step 1/2); aborting in strict mode."
        )

    analysis = analyze_gaps(job, cv)
    checks["gap_analysis"] = verify_gap_analysis(analysis, job, cv)

    letter, evaluations = tailor_cover_letter(
        analysis, job, tone=tone, max_revisions=max_revisions
    )
    checks["evaluation_consistency"] = verify_evaluation(evaluations[-1])

    return PipelineResult(
        job=job,
        cv=cv,
        analysis=analysis,
        letter=letter,
        evaluations=evaluations,
        checks=checks,
    )