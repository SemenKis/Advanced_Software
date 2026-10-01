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


def collect_database_evidence(student_folder):
    schemas = []
    for path in (REPO_ROOT / student_folder).glob("*/schema.sql"):
        schemas.append(f"--- {path.relative_to(REPO_ROOT)} ---\n{path.read_text()}")
    return "\n\n".join(schemas) if schemas else f"No schema.sql found for {student_folder}."


def collect_architecture_evidence(student_folder):
    compose_path = REPO_ROOT / student_folder / "docker-compose.yml"
    if compose_path.exists():
        return compose_path.read_text()
    return f"docker-compose.yml not found for {student_folder}."


def collect_devops_evidence(student_folder):
    workflow_name = f"{student_folder.split('-')[0]}-{student_folder.split('-')[1]}-ci.yml"
    matches = list((REPO_ROOT / ".github" / "workflows").glob(f"*{student_folder.split('-')[1]}*.yml"))
    if matches:
        return "\n\n".join(f"--- {p.name} ---\n{p.read_text()}" for p in matches)
    return f"No workflow file found for {student_folder}."


def collect_implementation_evidence(student_folder):
    student_dir = REPO_ROOT / student_folder
    if not student_dir.exists():
        return f"Folder not found: {student_folder}"
    contents = []
    for py_file in student_dir.rglob("*.py"):
        try:
            text = py_file.read_text()
            contents.append(f"--- {py_file.relative_to(student_dir)} ---\n{text[:500]}")
        except Exception: 
            continue
    return "\n\n".join(contents) if contents else f"No Python files found for {student_folder}."
   


def collect_mcp_evidence(student_folder):
    sections = []
    mcp_dir = REPO_ROOT / "mcp-server"
    if mcp_dir.exists():
        for name in ("tools.py", "mcp_http_server.py"):
            p = mcp_dir / name
            if p.exists():
                sections.append(f"--- mcp-server/{name} ---\n{p.read_text()[:1200]}")
    else:
        sections.append("Shared mcp-server/ directory not found at repo root.")

    student_dir = REPO_ROOT / student_folder
    for rel in ("backend/app.py", "frontend/app.py"):
        p = student_dir / rel
        if p.exists():
            mcp_lines = [l for l in p.read_text().splitlines() if "mcp" in l.lower()]
            if mcp_lines:
                sections.append(f"--- {student_folder}/{rel} (MCP integration lines) ---\n" + "\n".join(mcp_lines))

    return "\n\n".join(sections) if sections else f"No MCP evidence found for {student_folder}."


def collect_rag_evidence(student_folder):
    sections = []
    rag_dir = REPO_ROOT / "ai-services" / "rag-server"
    if rag_dir.exists():
        pipeline_path = rag_dir / "rag_pipeline.py"
        if pipeline_path.exists():
            sections.append(f"--- ai-services/rag-server/rag_pipeline.py ---\n{pipeline_path.read_text()[:1200]}")
        corpus_dir = rag_dir / "corpus_sources"
        if corpus_dir.exists():
            for src in corpus_dir.glob("*.py"):
                sections.append(f"--- ai-services/rag-server/corpus_sources/{src.name} ---\n{src.read_text()[:800]}")
    else:
        sections.append("Shared ai-services/rag-server/ directory not found at repo root.")

    student_dir = REPO_ROOT / student_folder
    for rel in ("backend/app.py", "frontend/app.py"):
        p = student_dir / rel
        if p.exists():
            rag_lines = [l for l in p.read_text().splitlines() if "rag" in l.lower()]
            if rag_lines:
                sections.append(f"--- {student_folder}/{rel} (RAG integration lines) ---\n" + "\n".join(rag_lines))

    return "\n\n".join(sections) if sections else f"No RAG evidence found for {student_folder}."


COLLECTORS = {
    "database": collect_database_evidence,
    "architecture": collect_architecture_evidence,
    "devops": collect_devops_evidence,
    "implementation": collect_implementation_evidence,
    "mcp": collect_mcp_evidence,
    "rag": collect_rag_evidence,
}


def load_prompt(student_folder):
    prompt_path = Path(__file__).resolve().parent / "prompts" / student_folder / "review_prompt.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"No prompt found for {student_folder} at {prompt_path}")
    return prompt_path.read_text()


def run_review(student_folder, evidence_category):
    print(f"[PLAN] Collecting {evidence_category} evidence for {student_folder} only...")
    evidence = COLLECTORS[evidence_category](student_folder)

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
