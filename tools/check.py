"""Tests + text lint, the one-command check (the pre-commit hook runs this).
Usage: python -X utf8 tools/check.py
Exit code = pytest's, then the extraction lint's. ROM-dependent tests skip when rom/ is absent."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
r = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pytest', '-q', 'tests'], cwd=ROOT)
if r.returncode:
    sys.exit(r.returncode)
# text lint: extraction roundtrip + coverage (prints one summary line)
lint = subprocess.run([sys.executable, '-X', 'utf8', 'tools/extract.py', 'check'], cwd=ROOT,
                      capture_output=True, text=True, encoding='utf-8', errors='replace')
for line in (lint.stdout or '').splitlines():
    if line.startswith(('FAIL', 'check:')):
        print(line)
sys.exit(lint.returncode)
