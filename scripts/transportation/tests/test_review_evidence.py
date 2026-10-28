"""Evidence review must not turn missing, stale or skipped results into a pass."""
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("review_evidence_test", Path(__file__).resolve().parents[1] / "review_evidence.py")
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


@pytest.fixture(autouse=True)
def isolated_ci_environment(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("DOCKER_VALIDATION_RESULT", raising=False)


def reports(path):
    security = {"scans": [{"scanner": scanner, "exit_code": 0, "context": "local-pre-commit",
                           "source_index_sha256": "current", "timestamp": "2026-10-28T00:00:00Z"}
                          for scanner in ("ruff", "detect-secrets", "pip-audit")]}
    post = {"exit_code": 0, "context": "ci", "run_url": "https://github.com/example/repo/actions/runs/1",
            "source_index_sha256": "current", "test_cases": [
                {"name": name, "status": "passed"} for name in sorted(review.REQUIRED_TESTS)]}
    (path / "pre-commit-report.json").write_text(json.dumps(security))
    (path / "post-commit-report.json").write_text(json.dumps(post))
    return security, post


def test_missing_evidence_fails(tmp_path):
    result, _ = review.validate_evidence(tmp_path, "current")
    assert result["status"] == "INCOMPLETE_OR_FAILED"


def test_matching_successful_evidence_passes(tmp_path):
    reports(tmp_path)
    result, _ = review.validate_evidence(tmp_path, "current")
    assert result["status"] == "PASS"
    assert len(result["evidence_sha256"]) == 2


def test_stale_evidence_fails(tmp_path):
    reports(tmp_path)
    result, _ = review.validate_evidence(tmp_path, "new-source")
    assert result["status"] == "INCOMPLETE_OR_FAILED"


def test_ci_scans_cannot_claim_local_commit_evidence(tmp_path):
    security, _ = reports(tmp_path)
    security["scans"][0]["context"] = "ci"
    (tmp_path / "pre-commit-report.json").write_text(json.dumps(security))
    assert review.validate_evidence(tmp_path, "current")[0]["status"] != "PASS"


def test_skipped_endpoint_test_fails(tmp_path):
    _, post = reports(tmp_path)
    post["test_cases"][0]["status"] = "skipped"
    (tmp_path / "post-commit-report.json").write_text(json.dumps(post))
    assert review.validate_evidence(tmp_path, "current")[0]["status"] != "PASS"


def test_post_commit_report_must_match_current_ci_commit(tmp_path, monkeypatch):
    reports(tmp_path)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_SHA", "different-commit")
    result, _ = review.validate_evidence(tmp_path, "current")
    assert result["status"] != "PASS"
    assert any(c["check"] == "CI commit identity" and not c["passed"] for c in result["checks"])
