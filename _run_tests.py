import subprocess
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(script_dir, "backend")
print(f"Changing to: {backend_dir}", flush=True)
os.chdir(backend_dir)
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
output = f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}\nEXITCODE: {r.returncode}\n"
result_path = os.path.join(script_dir, "test_runner_result.txt")
print(f"Writing to: {result_path}", flush=True)
with open(result_path, "w", encoding="utf-8") as f:
    f.write(output)
print(output, flush=True)
