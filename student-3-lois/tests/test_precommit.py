
import json
import subprocess
import sys
from pathlib import Path
 
import pytest
 
pytestmark = pytest.mark.pre_commit
 
STUDENT_DIR = Path(__file__).resolve().parents[1]
 
 
def test_ruff_scan_passes():
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--output-format=concise", "."],
        capture_output=True,
        text=True,
        cwd=STUDENT_DIR,
    )
    returncode = result.returncode
    assert returncode == 0, result.stdout + result.stderr
 
 
def test_detect_secrets_scan_passes():
    result = subprocess.run(
        [sys.executable, "-m", "detect_secrets", "scan"],
        capture_output=True,
        text=True,
        cwd=STUDENT_DIR,
    )
    returncode = result.returncode
    assert returncode == 0, result.stderr
    findings = json.loads(result.stdout)
    assert findings.get("results", {}) == {}, "Potential secrets detected"