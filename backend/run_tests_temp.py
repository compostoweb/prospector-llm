import subprocess
import sys

r = subprocess.run(
    [
        sys.executable, "-m", "pytest",
        "tests/test_services/",
        "tests/test_workers/",
        "tests/test_api/test_cadences.py",
        "tests/test_api/test_leads.py",
        "tests/test_api/test_tenants.py",
        "--tb=no", "-q", "-p", "no:warnings",
    ],
    capture_output=True,
    text=True,
)
with open("pytest_result.txt", "w") as f:
    f.write(f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}\nEXITCODE: {r.returncode}\n")
print(f"STDOUT:\n{r.stdout}")
print(f"STDERR:\n{r.stderr}")
print(f"EXITCODE: {r.returncode}")
