"""Scanner finding and error statuses must survive report generation."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location("security_report_test", Path(__file__).resolve().parents[1] / "security_report.py")
security = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(security)


@pytest.mark.parametrize("tool_code,payload,expected", [
    (0, '{"results": {}}', 0),
    (0, '{"results": {"backend.py": [{"type": "potential secret"}]}}', 1),
    (0, 'not JSON', 2),
    (3, '', 3),
])
def test_secret_findings_and_errors_fail_the_hook(tmp_path, monkeypatch, tool_code, payload, expected):
    monkeypatch.setattr(security.subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=tool_code, stdout=payload, stderr=""))
    monkeypatch.setattr(security, "source_fingerprint", lambda: "current")
    monkeypatch.setenv("GITHUB_SHA", "commit")
    assert security.run_scan("detect-secrets", tmp_path, "local-pre-commit") == expected
    record = json.loads((tmp_path / "security-detect-secrets.json").read_text())
    assert record["tool_exit_code"] == tool_code
    assert record["exit_code"] == expected


def test_identical_scans_do_not_keep_modifying_staged_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(security.subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=0, stdout="All checks passed!", stderr=""))
    monkeypatch.setattr(security, "source_fingerprint", lambda: "current")
    monkeypatch.setenv("GITHUB_SHA", "commit")
    security.run_scan("ruff", tmp_path, "local-pre-commit")
    before = (tmp_path / "pre-commit-report.json").read_bytes()
    security.run_scan("ruff", tmp_path, "local-pre-commit")
    assert (tmp_path / "pre-commit-report.json").read_bytes() == before
