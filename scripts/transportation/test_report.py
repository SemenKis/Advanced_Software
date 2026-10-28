"""Run endpoint/workflow tests and save text, JUnit and machine-readable evidence."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from defusedxml import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("transportation_security", Path(__file__).with_name("security_report.py"))
security = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(security)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "student-4-sam/evidence")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    junit = args.output_dir / "transportation-tests.xml"
    junit.unlink(missing_ok=True)
    command = [sys.executable, "-m", "pytest", "student-4-sam/tests",
               "ai-services/multi-agent-server/tests", "scripts/transportation/tests",
               "-v", f"--junitxml={junit}"]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)  # noqa: S603
    output = result.stdout + "\n" + result.stderr
    print(output)
    (args.output_dir / "student-4-test-results.txt").write_text(output)
    cases = []
    if junit.exists():
        for case in ET.parse(junit).iter("testcase"):
            status = "passed"
            for tag in ("failure", "error", "skipped"):
                if case.find(tag) is not None:
                    status = tag
            cases.append({"name": case.get("name"), "class": case.get("classname"), "status": status})
    record = {
        "schema_version": 1, "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": "ci" if os.getenv("GITHUB_ACTIONS") else "local-test",
        "commit": os.getenv("GITHUB_SHA"), "source_index_sha256": security.source_fingerprint(),
        "run_url": (f"https://github.com/{os.getenv('GITHUB_REPOSITORY')}/actions/runs/{os.getenv('GITHUB_RUN_ID')}"
                    if os.getenv("GITHUB_ACTIONS") else None),
        "exit_code": result.returncode, "command": command, "test_cases": cases,
        "endpoint_functions": {"get_shipments": "GET /api/shipments", "create_shipment": "POST /api/shipments"},
    }
    (args.output_dir / "post-commit-report.json").write_text(json.dumps(record, indent=2) + "\n")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
