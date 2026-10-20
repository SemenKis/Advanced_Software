"""Run pip-audit on the requirements files that pre-commit passes in."""
import subprocess
import sys

# chromadb 1.5.9 has known advisories but pip-audit lists no fixed release yet.
IGNORED_ADVISORIES = ["PYSEC-2026-311", "PYSEC-2026-3813", "PYSEC-2026-3814", "PYSEC-2026-3815"]


def main(files):
    failed = False
    for path in files:
        cmd = [sys.executable, "-m", "pip_audit", "-r", path, "--progress-spinner", "off"]
        for advisory in IGNORED_ADVISORIES:
            cmd += ["--ignore-vuln", advisory]
        if subprocess.call(cmd) != 0:  # noqa: S603 - fixed pip-audit invocation, file names come from git
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
