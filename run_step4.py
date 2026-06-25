import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from tailorapply.steps import (  # noqa: E402
    analyze_gaps,
    extract_cv_profile,
    extract_job_profile,
    flag_letter_concerns,
    generate_cover_letter,
)


def main() -> None:
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    tone = next(
        (a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--tone=")), "formal"
    )
    if len(positional) != 2:
        raise SystemExit(
            "Use: python run_paso4.py <oferta.txt> <cv.txt> [--tone=formal|startup|technical]"
        )

    job = extract_job_profile(Path(positional[0]).read_text(encoding="utf-8"))
    cv = extract_cv_profile(Path(positional[1]).read_text(encoding="utf-8"))
    analysis = analyze_gaps(job, cv)

    print(f"--- Letter ({tone}) ---\n")
    pieces = []
    for piece in generate_cover_letter(analysis, job, tone=tone):
        print(piece, end="", flush=True)
        pieces.append(piece)
    letter = "".join(pieces)

    print("\n\n--- Revision (advisory) ---")
    concerns = flag_letter_concerns(letter, analysis)
    if concerns:
        print("Items for human review:")
        for c in concerns:
            print(f"  - {c}")
    else:
        print("Without heuristic flags.")
    print(
        "Note: This does NOT verify the grounding of the prose; that verification"
        "Semantics is Step 5 (evaluator)."
    )


if __name__ == "__main__":
    main()
