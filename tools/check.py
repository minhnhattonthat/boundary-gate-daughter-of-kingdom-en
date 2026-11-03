"""Tests + text lint, the one-command check (the pre-commit hook runs this). Usage: python -X utf8 tools/check.py
Exit code = pytest's: ROM-dependent tests skip when rom/ is absent."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.exit(subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pytest', '-q', 'tests'], cwd=ROOT).returncode)
