import os
import json
import requests
from pathlib import Path
from datetime import datetime

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:0.5b")
REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = Path(__file__).resolve().parent / "agentic_review_log.jsonl"


def call_ollama(system_prompt, user_prompt):
    prompt = f"{system_prompt}\n\n{user_prompt}"
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60,
        )
        return resp.json().get("response", "")
    except Exception as e:
        return f"ERROR: {e}"


def log_review(student, evidence_preview, review):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "student": student,
        "evidence_preview": evidence_preview,
        "review": review,
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"\n[{student}] AI REVIEW:\n{review}\n")
    return entry


def collect_database_evidence():
    schemas = []
    for path in REPO_ROOT.glob("student-*/*/schema.sql"):
        schemas.append(f"--- {path.relative_to(REPO_ROOT)} ---\n{path.read_text()}")
    return "\n\n".join(schemas) if schemas else "No schema.sql files found."


def collect_architecture_evidence():
    compose_path = REPO_ROOT / "docker-compose.yml"
    return compose_path.read_text() if compose_path.exists() else "docker-compose.yml not found."


def collect_devops_evidence():
    workflows = []
    for path in (REPO_ROOT / ".github" / "workflows").glob("*.yml"):
        workflows.append(f"--- {path.name} ---\n{path.read_text()}")
    return "\n\n".join(workflows) if workflows else "No workflow files found."


def collect_implementation_evidence():
    lines = []
    for student_dir in sorted(REPO_ROOT.glob("student-*-*")):
        files = [str(p.relative_to(student_dir)) for p in student_dir.rglob("*.py")]
        lines.append(f"{student_dir.name}: {files}")
    return "\n".join(lines)


COLLECTORS = {
    "database": collect_database_evidence,
    "architecture": collect_architecture_evidence,
    "devops": collect_devops_evidence,
    "implementation": collect_implementation_evidence,
}


def load_prompt(student_folder):
    prompt_path = Path(__file__).resolve().parent / "prompts" / student_folder / "review_prompt.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"No prompt found for {student_folder} at {prompt_path}")
    return prompt_path.read_text()


def run_review(student_folder, evidence_category):
    print(f"[PLAN] Collecting {evidence_category} evidence for {student_folder}...")
    evidence = COLLECTORS[evidence_category]()

    print(f"[ACT] Loading prompt and sending to {OLLAMA_MODEL}...")
    system_prompt = load_prompt(student_folder)
    review = call_ollama(system_prompt, f"Evidence:\n{evidence[:3000]}")

    print("[OBSERVE] Review received.")
    log_review(student_folder, evidence[:300], review)
    print("[ADAPT] Saved to agentic_review_log.jsonl")
    return review


def main():
    students = sorted(p.name for p in (Path(__file__).resolve().parent / "prompts").iterdir() if p.is_dir())
    print("=" * 60)
    print("SHARED AGENTIC REVIEW LOOP")
    for i, s in enumerate(students, 1):
        print(f"{i} - {s}")
    print("0 - Exit")
    print("=" * 60)

    while True:
        choice = input("\nChoose a student folder to review: ").strip()
        if choice == "0":
            print("Loop closed.")
            break
        try:
            idx = int(choice) - 1
            student_folder = students[idx]
        except (ValueError, IndexError):
            print("Invalid choice.")
            continue

        print("\nWhich evidence category?")
        for key in COLLECTORS:
            print(f"- {key}")
        category = input("Category: ").strip().lower()
        if category not in COLLECTORS:
            print("Invalid category.")
            continue

        run_review(student_folder, category)


if __name__ == "__main__":
    main()
