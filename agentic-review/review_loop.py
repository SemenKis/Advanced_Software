import os
import json
import requests
from pathlib import Path
from datetime import datetime, timezone

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:0.5b")
OLLAMA_REVIEW_MODEL = os.environ.get("OLLAMA_REVIEW_MODEL", "llama3.1:8b")
REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = Path(__file__).resolve().parent / "agentic_review_log.jsonl"


def call_ollama(system_prompt, user_prompt, model=None):
    prompt = f"{system_prompt}\n\n{user_prompt}"
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": model or OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=600,
        )
        return resp.json().get("response", "")
    except Exception as e:
        return f"ERROR: {e}"


def log_review(student, evidence_preview, review):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
        except Exception:  # noqa: S112 - skip files that cannot be read
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


def _read_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def collect_multi_agent_evidence(student_folder):
    sections = []
    server_dir = REPO_ROOT / "ai-services" / "multi-agent-server"
    if server_dir.exists():
        for name in ("app.py", "coordinator.py"):
            p = server_dir / name
            if p.exists():
                sections.append(f"--- ai-services/multi-agent-server/{name} ---\n{p.read_text()[:1200]}")
        history = _read_jsonl(server_dir / "workflow_history.jsonl")
        audit = _read_jsonl(server_dir / "coordination_audit.jsonl")
        domain = {
            "student-1-bea": "orders",
            "student-3-lois": "warehouse",
            "student-4-sam": "transportation",
        }.get(student_folder, student_folder)
        history = [row for row in history if row.get("domain", "warehouse") == domain]
        audit = [row for row in audit if row.get("domain", "warehouse") == domain]
        sections.append(f"Workflow evidence domain: {domain}")
        if history:
            last = history[-1]
            worker = last.get("worker", {})
            sections.append(
                "--- Latest workflow (workflow_history.jsonl) ---\n"
                f"workflow_id: {last.get('workflow_id')}\n"
                f"request: {last.get('user_request')}\n"
                f"planner status: {last.get('planner', {}).get('status')}\n"
                f"worker status: {worker.get('status')}, evidence_count={worker.get('evidence_count')}\n"
                f"worker output: {worker.get('output')}\n"
                f"reviewer status: {last.get('reviewer', {}).get('status')}\n"
                f"reviewer output: {last.get('reviewer', {}).get('output')}\n"
                f"human decision: {json.dumps(last.get('human_decision', {}))}\n"
                f"duration_ms: {last.get('duration_ms')}"
            )
            sections.append(f"Total workflows recorded: {len(history)}")
            verdicts = []
            for h in history:
                out = h.get("reviewer", {}).get("output", "")
                idx = out.find("Verdict:")
                verdicts.append(out[idx:idx + 24].split("\n")[0] if idx != -1 else "no verdict")
            sections.append("Reviewer verdicts across all workflows: " + "; ".join(verdicts))
        else:
            sections.append("No workflow history found. Run a workflow first.")
        decisions = [a for a in audit if a.get("event") == "human_decision"]
        sections.append(f"Audit events: {len(audit)}; human decisions recorded: {len(decisions)}")
        if decisions:
            sections.append("Latest human decision: " + str(decisions[-1].get("detail")))
    else:
        sections.append("Shared ai-services/multi-agent-server/ directory not found at repo root.")

    student_dir = REPO_ROOT / student_folder
    for rel in ("backend/app.py", "backend/htmx_routes.py", "frontend/app.py"):
        p = student_dir / rel
        if p.exists():
            lines = [l for l in p.read_text().splitlines() if "multi" in l.lower() and "agent" in l.lower()]
            if lines:
                sections.append(f"--- {student_folder}/{rel} (Multi-Agent integration lines) ---\n" + "\n".join(lines))

    compose = student_dir / "docker-compose.yml"
    if compose.exists():
        env_lines = [l.strip() for l in compose.read_text().splitlines() if "MULTI_AGENT" in l]
        if env_lines:
            sections.append(f"--- {student_folder}/docker-compose.yml (Multi-Agent environment) ---\n" + "\n".join(env_lines))

    return "\n\n".join(sections)


def collect_testing_evidence(student_folder):
    sections = []
    student_dir = REPO_ROOT / student_folder
    tests_dir = student_dir / "tests"
    test_files = sorted(tests_dir.glob("test_*.py")) if tests_dir.exists() else []
    if test_files:
        for p in test_files:
            sections.append(f"--- {student_folder}/tests/{p.name} ---\n{p.read_text()[:1500]}")
    else:
        sections.append(f"No test files found in {student_folder}/tests/.")

    parts = student_folder.split("-")
    number = parts[1] if len(parts) > 1 else ""
    workflow = REPO_ROOT / ".github" / "workflows" / f"student-{number}-ci.yml"
    if workflow.exists():
        keys = ("pytest", "test", "upload-artifact", "name:")
        lines = [l for l in workflow.read_text().splitlines() if any(k in l.lower() for k in keys)]
        sections.append(f"--- .github/workflows/{workflow.name} (test-related lines) ---\n" + "\n".join(lines))
    else:
        sections.append(f"Workflow student-{number}-ci.yml not found.")

    precommit = REPO_ROOT / ".pre-commit-config.yaml"
    if precommit.exists():
        sections.append(f"--- .pre-commit-config.yaml ---\n{precommit.read_text()[:800]}")
    else:
        sections.append(".pre-commit-config.yaml not found at repo root.")

    evidence_dir = student_dir / "evidence"
    for name in ("pre-commit-report.txt", f"student-{number}-test-results.txt"):
        report = evidence_dir / name
        if report.exists():
            sections.append(f"--- {student_folder}/evidence/{name} ---\n{report.read_text()[:3000]}")
        else:
            sections.append(f"Report not found: {student_folder}/evidence/{name}.")

    return "\n\n".join(sections)


def collect_cloud_deployment_evidence(student_folder):
    sections = []
    workflow = REPO_ROOT / ".github" / "workflows" / "cloud-deployment.yml"
    if workflow.exists():
        sections.append(f"--- .github/workflows/cloud-deployment.yml ---\n{workflow.read_text()[:1500]}")
    else:
        sections.append("cloud-deployment.yml not found yet.")

    deploy_dir = REPO_ROOT / "scripts" / "deploy"
    scripts = [p for p in sorted(deploy_dir.glob("*")) if p.is_file()] if deploy_dir.exists() else []
    if scripts:
        for p in scripts:
            sections.append(f"--- scripts/deploy/{p.name} ---\n{p.read_text()[:800]}")
    else:
        sections.append("No deployment scripts found in scripts/deploy/ yet.")

    compose = REPO_ROOT / student_folder / "docker-compose.yml"
    if compose.exists():
        flags = [l.strip() for l in compose.read_text().splitlines() if "ENABLED" in l]
        sections.append(f"--- {student_folder}/docker-compose.yml (feature flags) ---\n" + "\n".join(flags))

    return "\n\n".join(sections)


COLLECTORS = {
    "database": collect_database_evidence,
    "architecture": collect_architecture_evidence,
    "devops": collect_devops_evidence,
    "implementation": collect_implementation_evidence,
    "mcp": collect_mcp_evidence,
    "rag": collect_rag_evidence,
    "multi_agent": collect_multi_agent_evidence,
    "testing": collect_testing_evidence,
    "cloud_deployment": collect_cloud_deployment_evidence,
}


MODE_PROMPTS = {
    "multi_agent": (
        "You review the Multi-Agent Server workflow (Planner, Worker, Reviewer, Human Review). "
        "Use ONLY the evidence supplied and do not mention topics that are not in it. "
        "Assess: did all three agents complete, is the Worker output supported by its evidence, "
        "did the Reviewer catch errors, and was a human decision recorded in the audit log. "
        "Reply in at most 80 words as Strengths, Risks, Recommendation."
    ),
    "testing": (
        "You review automated tests for one student's backend. The evidence has the test files, "
        "the CI workflow test steps and the pre-commit configuration. Use ONLY the evidence. "
        "Assess: which endpoints are tested, assertion quality, whether the tests run in CI and "
        "results are uploaded, and whether pre-commit security scans exist. "
        "Reply in at most 80 words as Strengths, Risks, Recommendation."
    ),
    "cloud_deployment": (
        "You review cloud deployment readiness. The evidence has the deployment workflow, "
        "deployment scripts and the feature flags in docker-compose. Use ONLY the evidence. "
        "Assess: whether a deployment workflow and scripts exist, and whether AI Mode, MCP, RAG "
        "and Multi-Agent are disabled by default for the cloud. State clearly what is missing. "
        "Reply in at most 80 words as Strengths, Risks, Recommendation."
    ),
}

VALIDATION_PROMPT = (
    "You validate an AI assessment against the supplied evidence. "
    "Point out any claim that the evidence does not support and any important gap. "
    "Reply in at most 50 words."
)


def load_prompt(student_folder):
    prompt_path = Path(__file__).resolve().parent / "prompts" / student_folder / "review_prompt.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"No prompt found for {student_folder} at {prompt_path}")
    return prompt_path.read_text()


def run_review(student_folder, evidence_category):
    print(f"[PLAN] Collecting {evidence_category} evidence for {student_folder} only...")
    evidence = COLLECTORS[evidence_category](student_folder)

    if evidence_category in MODE_PROMPTS:
        print(f"[ACT] Implementation review with {OLLAMA_MODEL}...")
        implementation = call_ollama(MODE_PROMPTS[evidence_category], f"Evidence:\n{evidence[:3500]}")
        print(f"[ADAPT] Validation review with {OLLAMA_REVIEW_MODEL}...")
        validation = call_ollama(
            VALIDATION_PROMPT,
            f"Assessment:\n{implementation}\n\nEvidence:\n{evidence[:3500]}",
            model=OLLAMA_REVIEW_MODEL,
        )
        review = (
            f"IMPLEMENTATION ({OLLAMA_MODEL}):\n{implementation}\n\n"
            f"REVIEW ({OLLAMA_REVIEW_MODEL}):\n{validation}"
        )
    else:
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
