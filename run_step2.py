import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from tailorapply.steps import extract_cv_profile, verify_cv_grounding


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Use: python run_paso2.py <ruta_cv.txt>")

    cv_text = Path(sys.argv[1]).read_text(encoding="utf-8")

    profile = extract_cv_profile(cv_text)
    print(profile.model_dump_json(indent=2))

    report = verify_cv_grounding(profile, cv_text)
    if report["skills"] or report["bullets"]:
        print("\n[!] Unsupported content in the original CV:")
        for s in report["skills"]:
            print(f'  - invented kill: "{s}"')
        for b in report["bullets"]:
            print(f'  - altered bullet: "{b}"')
    else:
        print("\n[OK] Grounding verified: skills and achievements exist in the CV.")


if __name__ == "__main__":
    main()
