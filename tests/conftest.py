"""Ensures the repo root is importable as `src.*` regardless of pytest's
invocation directory or import-mode, matching the explicit sys.path
bootstrap convention used throughout src/."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
