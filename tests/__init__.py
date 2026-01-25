"""Test package bootstrap.

Ensures the local `src/` tree is importable before test modules run so
`uv run pytest` works without PYTHONPATH tweaks.
"""

from __future__ import annotations

import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
_SRC_STR = str(_SRC)
if _SRC_STR not in sys.path:
    sys.path.insert(0, _SRC_STR)
