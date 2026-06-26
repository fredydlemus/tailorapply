import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from tailorapply.steps import (  # noqa: E402
    analyze_gaps,
    extract_cv_profile,
    extract_job_profile,
    tailor_cover_letter,
)


def main() -> None:
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    tone = next(
        (a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--tone=")), "formal"
    )
    if len(positional) != 2:
        raise SystemExit(
            "Use: python run_paso5.py <oferta.txt> <cv.txt> [--tone=formal|startup|technical]"
        )

    job = extract_job_profile(Path(positional[0]).read_text(encoding="utf-8"))
    cv = extract_cv_profile(Path(positional[1]).read_text(encoding="utf-8"))
    analysis = analyze_gaps(job, cv)

    letter, evaluations = tailor_cover_letter(analysis, job, tone=tone, max_revisions=2)

    print("--- Loop traceability ---")
    for i, ev in enumerate(evaluations, 1):
        print(f"Round {i}: verdict={ev.verdict} | issues={len(ev.grounding_issues)} | "
              f"unused strengths={len(ev.missed_strengths)}")
        for issue in ev.grounding_issues:
            print(f"    grounding: {issue}")

    approved = evaluations[-1].verdict == "approve"
    state = "APPROVED" if approved else f"unapproved after {len(evaluations)} rounds (the last one is returned)"
    print(f"\nFinal state: {state}")

    print(f"\n--- Final letter ({tone}) ---\n{letter}")


if __name__ == "__main__":
    main()