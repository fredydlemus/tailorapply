import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from tailorapply.steps import extract_job_profile, verify_grouding

def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Use: python run_paso1.py <ruta_oferta.txt>")
    
    job_text = Path(sys.argv[1]).read_text(encoding="utf-8")

    profile = extract_job_profile(job_text)
    print(profile.model_dump_json(indent=2))

    ungrounded = verify_grouding(profile, job_text)
    if ungrounded:
        print("\n[!] Quotes that do NOT appear verbatim in the offer:")
        for r in ungrounded:
            print(f'  - {r.skill}: "{r.quote}"')
        else:
            print("\n[OK] Grounding verified: all quotes exist in the offer.")

if __name__ == "__main__":
    main()

