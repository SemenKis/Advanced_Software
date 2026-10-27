import subprocess, pytest, sys, json
pytestmark = pytest.mark.pre_commit

# def run(*cmd):
#     return subprocess.run(cmd, capture_output=True, text=True).returncode

def test_ruff_scan_passes():
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--output-format=concise", "."],
        capture_output=True,
        text=True,
    )
    returncode = result.returncode  # avoid pytest reprinting the full CompletedProcess in the assert
    assert returncode == 0, result.stdout + result.stderr



def test_detect_secrets_scan_passes():
    result = subprocess.run(
        [sys.executable, "-m", "detect_secrets", "scan", "--exclude-files", "legacy-lab3/.*"],
        capture_output=True,
        text=True,
    )
    returncode = result.returncode  # avoid pytest reprinting the full CompletedProcess in the assert
    assert returncode == 0, result.stderr
    findings = json.loads(result.stdout)
    assert findings.get("results", {}) == {}, "Potential secrets detected"