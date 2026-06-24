from typing import List, Literal, Optional
from pydantic import BaseModel, Field

# User Profile
class Requirement(BaseModel):
    skill: str = Field(description="Short name of the skill or requirement")
    category: Literal["must_have", "nice_to_have"]
    quote: str = Field(description="Direct quote from the offer that supports this requirement")

class JobProfile(BaseModel):
    role_title: str
    seniority: Literal["junior", "mid", "senior", "lead", "no_specific"]
    requirements: List[Requirement]
    ats_keywords: List[str]
    culture_signals: List[str]

class Experience(BaseModel):
    role: str = Field("Position, copied from CV")
    company: str = Field("Company, copied from CV")
    bullets: list[str] = Field(
        description="Achievements/responsibilities COPIED VERBATIM from the CV, without rewriting"
    )

class CVProfile(BaseModel):
    skills: list[str] = Field(
        description="Skills explicitly listed in the CV (without inference)"
    )
    experiences: list[Experience]
    certifications: list[str]

class RequirementMatch(BaseModel):
    requirement: str = Field(
        description="Exact skill for the job profile being evaluated"
    )
    status: Literal["strong_match", "partial_match", "gap"]
    evidence_from_cv: str | None = Field(
        description="Direct quote from the CV profile that supports the match; null if it is a gap"
    )
    how_to_present: str = Field(
        description="Honest suggestion for framing this in the application"
    )

class GapAnalysisLLM(BaseModel):
    matches: list[RequirementMatch]
    missing_keywords: list[str]
    honest_summary: str

class GapAnalysis(BaseModel):
    fit_score: int
    must_have_coverage: str
    matches: list[RequirementMatch]
    missing_keywords: list[str]
    honest_summary: str
