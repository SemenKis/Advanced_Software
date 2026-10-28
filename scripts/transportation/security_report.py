"""Run transportation security scans and preserve their real exit codes and output."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "student-4-sam/evidence"
GIT = shutil.which("git") or "/usr/bin/git"
SOURCE_PATHS = [
    "student-4-sam/backend", "student-4-sam/tests", "student-4-sam/database",
    "student-4-sam/Dockerfile", "student-4-sam/.dockerignore", "student-4-sam/frontend", "student-4-sam/docker-compose.yml",
    "scripts/transportation", "scripts/deploy", "agentic-review/review_loop.py",
    ".pre-commit-config.yaml", ".github/workflows/student-4-ci.yml",
    ".github/workflows/cloud-deployment.yml", "pyproject.toml",
]


def source_fingerprint():
    # Index entries are identical in a normal pre-commit run and checkout of that commit.
    result = subprocess.run(  # noqa: S603 - fixed git command and repository paths
        [GIT, "ls-files", "--stage", "--", *SOURCE_PATHS],
        cwd=ROOT, capture_output=True, check=True,
    )
    return hashlib.sha256(result.stdout).hexdigest()


def run_scan(name, output_dir, context):
    python_files = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "student-4-sam").rglob("*.py"))
    scan_files = [str(p.relative_to(ROOT)) for p in (ROOT / "student-4-sam").rglob("*")
                  if p.is_file() and "evidence" not in p.parts and "__pycache__" not in p.parts
                  and p.suffix in {".py", ".txt", ".sql", ".html", ".yml", ".conf"}]
    commands = {
        "ruff": [sys.executable, "-m", "ruff", "check", *python_files],
        "detect-secrets": [sys.executable, "-m", "detect_secrets", "scan", "--all-files", *sorted(scan_files)],
        "pip-audit": [sys.executable, "-m", "pip_audit", "-r", "student-4-sam/backend/requirements.txt",
                      "-r", "student-4-sam/database/requirements.txt", "--progress-spinner", "off"],
    }
    command = commands[name]
    result = subprocess.run(  # noqa: S603 - commands are fixed scanner invocations
        command, cwd=ROOT, capture_output=True, text=True, check=False,
    )
    status = result.returncode
    if name == "detect-secrets" and status == 0:
        try:
            findings = json.loads(result.stdout)["results"]
            if not isinstance(findings, dict):
                raise ValueError("Expected a results object")
            # The scan subcommand returns zero even when it finds potential secrets.
            status = 1 if any(findings.values()) else 0
        except (ValueError, KeyError):
            status = 2
    record = {
        "scanner": name, "context": context, "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_index_sha256": source_fingerprint(), "commit": os.getenv("GITHUB_SHA") or subprocess.check_output(  # noqa: S603 - fixed git metadata command
            [GIT, "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),  # noqa: S603
        "command": command, "tool_exit_code": result.returncode, "exit_code": status,
        "stdout": result.stdout, "stderr": result.stderr,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    # Reusing identical results avoids endlessly modifying staged evidence on every commit.
    previous_path = output_dir / f"security-{name}.json"
    if previous_path.exists():
        previous = json.loads(previous_path.read_text())
        def stable_output(value):
            try:
                decoded = json.loads(value)
                if isinstance(decoded, dict):
                    decoded.pop("generated_at", None)
                return decoded
            except ValueError:
                return value
        keys = ("scanner", "context", "source_index_sha256", "exit_code", "tool_exit_code")
        if (all(previous.get(key) == record[key] for key in keys)
                and stable_output(previous.get("stdout", "")) == stable_output(record["stdout"])
                and previous.get("stderr") == record["stderr"]):
            record = previous
    (output_dir / f"security-{name}.json").write_text(json.dumps(record, indent=2) + "\n")
    records = [json.loads(p.read_text()) for p in sorted(output_dir.glob("security-*.json"))]
    report = {"schema_version": 1, "scans": records}
    (output_dir / "pre-commit-report.json").write_text(json.dumps(report, indent=2) + "\n")
    text = "Transportation security testing report\n\n" + "\n\n".join(
        f"{r['scanner']}: {'PASS' if r['exit_code'] == 0 else 'FAIL'}\n"
        f"Context: {r['context']}\nTime: {r['timestamp']}\nSource index: {r['source_index_sha256']}\n"
        f"Command: {' '.join(r['command'])}\n{r['stdout']}\n{r['stderr']}" for r in records
    )
    (output_dir / "pre-commit-report.txt").write_text(text + "\n")
    print(f"{name}: {'PASS' if status == 0 else 'FAIL'} (exit {status}); report: {output_dir / 'pre-commit-report.txt'}")
    if status:
        print(result.stdout)
        print(result.stderr)
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scanner", choices=["ruff", "detect-secrets", "pip-audit", "all"])
    parser.add_argument("--output-dir", type=Path, default=EVIDENCE)
    parser.add_argument("--context", choices=["local-pre-commit", "local-manual", "ci"], default="local-manual")
    args = parser.parse_args()
    names = ["ruff", "detect-secrets", "pip-audit"] if args.scanner == "all" else [args.scanner]
    codes = [run_scan(name, args.output_dir, args.context) for name in names]
    return int(any(codes))


if __name__ == "__main__":
    sys.exit(main())
