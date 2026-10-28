"""Validate recorded transportation results before asking models to review them."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("transportation_security", Path(__file__).with_name("security_report.py"))
security = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(security)

REQUIRED_TESTS = {
    "test_get_shipments_returns_persisted_records_in_descending_order",
    "test_create_shipment_persists_defaults_and_normalises_status",
}


def validate_evidence(evidence_dir, fingerprint):
    checks = []
    reports = {}
    sources = {}

    def check(name, ok, detail):
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    for filename in ("pre-commit-report.json", "post-commit-report.json"):
        path = evidence_dir / filename
        try:
            raw = path.read_bytes()
            report = json.loads(raw)
            if not isinstance(report, dict):
                raise ValueError("Report must be a JSON object")
            reports[filename] = report
            sources[filename] = hashlib.sha256(raw).hexdigest()
        except (OSError, ValueError) as error:
            check(filename, False, str(error))

    scans = reports.get("pre-commit-report.json", {}).get("scans", [])
    if not isinstance(scans, list):
        scans = []
    for scanner in ("ruff", "detect-secrets", "pip-audit"):
        matches = [r for r in scans if isinstance(r, dict) and r.get("scanner") == scanner]
        record = matches[0] if len(matches) == 1 else {}
        ok = (record.get("exit_code") == 0 and record.get("context") == "local-pre-commit"
              and record.get("source_index_sha256") == fingerprint and bool(record.get("timestamp")))
        check(f"local {scanner}", ok, "Requires one successful local-pre-commit result for the current source index.")

    post = reports.get("post-commit-report.json", {})
    if os.getenv("GITHUB_ACTIONS"):
        check("CI commit identity", post.get("commit") == os.getenv("GITHUB_SHA"),
              "Post-commit report must identify the current GitHub commit.")
    check("post-commit execution", post.get("exit_code") == 0 and post.get("context") == "ci"
          and bool(post.get("run_url")) and post.get("source_index_sha256") == fingerprint,
          "Requires a successful GitHub Actions run for matching source, with a run URL.")
    cases = post.get("test_cases", [])
    if not isinstance(cases, list):
        cases = []
    for name in sorted(REQUIRED_TESTS):
        matches = [c for c in cases if isinstance(c, dict) and c.get("name") == name]
        check(name, bool(matches) and all(c.get("status") == "passed" for c in matches),
              "Endpoint contract test must be present and passed, not skipped.")
    check("suite results", bool(cases) and all(isinstance(c, dict) and c.get("status") == "passed" for c in cases),
          "Every recorded test must pass.")
    docker = os.getenv("DOCKER_VALIDATION_RESULT")
    if docker is not None:
        check("Docker validation", docker == "success", docker)
    return {"schema_version": 1, "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_index_sha256": fingerprint, "evidence_sha256": sources,
            "status": "PASS" if all(c["passed"] for c in checks) else "INCOMPLETE_OR_FAILED",
            "checks": checks}, reports


def generate_review(evidence_dir, offline=True, model_call=None):
    validation, reports = validate_evidence(evidence_dir, security.source_fingerprint())
    evidence_dir.mkdir(parents=True, exist_ok=True)
    lines = ["# Transportation agentic-loop Testing Review", "",
             f"Generated: {validation['timestamp']}", "",
             "## PLAN", "Review local pre-commit security results and post-commit endpoint test results.", "",
             "## ACT", "Loaded recorded scanner results and structured pytest/JUnit results; source files alone do not prove a pass.", "",
             "## OBSERVE", f"Evidence validation: **{validation['status']}**", "",
             "| Check | Result | Detail |", "| --- | --- | --- |"]
    for check in validation["checks"]:
        lines.append(f"| {check['check']} | {'PASS' if check['passed'] else 'FAIL / MISSING'} | {check['detail'].replace('|', '/')} |")
    post = reports.get("post-commit-report.json", {})
    if post.get("run_url"):
        lines.extend(["", f"Post-commit run: {post['run_url']}"])
    lines.extend(["", "## ADAPT", "Accept the testing evidence only when every validation check passes. "
                  "Otherwise rerun the failed checks or supply the missing reports; do not infer success."])
    validation["review_mode"] = "deterministic evidence review (no model invoked)"
    if not offline and model_call:
        # Pass the results, not a source-first preview that truncates the reports.
        compact = {"validation": validation, "results": {
            "security": [{k: r.get(k) for k in ("scanner", "context", "exit_code", "timestamp")}
                         for r in reports.get("pre-commit-report.json", {}).get("scans", [])],
            "tests": post,
        }}
        evidence = json.dumps(compact, indent=2)
        assessment = model_call(
            "Review transportation testing using only these executed results. Treat missing, stale, "
            "failed or skipped evidence as gaps. Give Strengths, Risks, Recommendation.", evidence)
        critique = model_call(
            "Validate the assessment against the evidence. Reject unsupported pass claims.",
            f"Assessment:\n{assessment}\nEvidence:\n{evidence}",
            model=os.getenv("OLLAMA_REVIEW_MODEL", "llama3.1:8b"))
        lines.extend(["", "## Model review", assessment, "", "## Model validation", critique])
        validation.update(review_mode="model assessment plus validation", assessment=assessment, model_validation=critique)
        if assessment.startswith("ERROR:") or critique.startswith("ERROR:"):
            validation["status"] = "MODEL_ERROR"
    (evidence_dir / "testing-review.md").write_text("\n".join(lines) + "\n")
    (evidence_dir / "testing-validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    return validation
