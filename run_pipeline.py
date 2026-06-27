import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from tailorapply.pipeline import run_pipeline  # noqa: E402


def _fmt(value) -> str:
    if isinstance(value, dict):
        problems = {k: v for k, v in value.items() if v}
        return "OK" if not problems else str(problems)
    return "OK" if not value else str(value)


def main() -> None:
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    tone = next(
        (a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--tone=")), "formal"
    )
    if len(positional) != 2:
        raise SystemExit(
            "Use: python run_pipeline.py <offer.txt> <cv.txt> [--tone=formal|startup|technical]"
        )

    job_text = Path(positional[0]).read_text(encoding="utf-8")
    cv_text = Path(positional[1]).read_text(encoding="utf-8")

    result = run_pipeline(job_text, cv_text, tone=tone, max_revisions=2)

    print("--- Pipeline checks (defense-in-depth) ---")
    jg = result.checks["job_grounding"]
    print(f"[Step 1] Grounding the offer:     {_fmt([r.skill for r in jg])}")
    print(f"[Step 2] Grounding the CV:           {_fmt(result.checks['cv_grounding'])}")
    print(f"[Step 3] Coverage/coherence/evidence: {_fmt(result.checks['gap_analysis'])}")
    print(f"[Step 5] Evaluator consistency:   {_fmt(result.checks['evaluation_consistency'])}")

    print("\n--- Loop traceability ---")
    for i, ev in enumerate(result.evaluations, 1):
        print(
            f"Round {i}: verdict={ev.verdict} | issues={len(ev.grounding_issues)} | "
            f"unused strengths={len(ev.missed_strengths)}"
        )
        for issue in ev.grounding_issues:
            print(f"    grounding: {issue}")

    approved = result.evaluations[-1].verdict == "approve"
    estado = (
        "APPROVE"
        if approved
        else f"unapproved after {len(result.evaluations)} rounds (the last one is returned)"
    )
    print(f"\nFinal state: {estado}")
    print(f"\n--- Final cover letter ({tone}) ---\n{result.letter}")


if __name__ == "__main__":
    main()