import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from tailorapply.steps import (  # noqa: E402
    analyze_gaps,
    extract_cv_profile,
    extract_job_profile,
    verify_gap_analysis,
)

def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Use: python run_paso3.py <oferta.txt> <cv.txt>")

    job_text = Path(sys.argv[1]).read_text(encoding="utf-8")
    cv_text = Path(sys.argv[2]).read_text(encoding="utf-8")

    job = extract_job_profile(job_text)
    cv = extract_cv_profile(cv_text)
    analysis = analyze_gaps(job, cv)

    print(analysis.model_dump_json(indent=2))
    print(f"\nFit score: {analysis.fit_score}/100 (must-haves: {analysis.must_have_coverage})")

    report = verify_gap_analysis(analysis, job, cv)
    problems = {k: v for k, v in report.items() if v}
    if problems:
        print("\n[!] The verification found problems:")
        for key, items in problems.items():
            print(f" {key}:")
            for it in items:
                print(f"    - {it}")
    else:
        print("\n[OK] Clean verification: correct coverage, consistency, and grounding.")

if __name__ == "__main__":
    main()

