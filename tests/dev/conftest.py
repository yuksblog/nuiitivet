"""Fixtures the layout edit mode tests share: the user module the widgets are built from."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

import pytest

from nuiitivet.dev import source


@pytest.fixture
def app_file(tmp_path: Path) -> Iterator[Path]:
    """A user module on disk, imported with site capture on; its text is the mode tests' ``_APP``."""
    from .test_layout_edit_mode import _APP, _SIDE

    path = tmp_path / "layout_app.py"
    path.write_text(_APP, encoding="utf-8")
    (tmp_path / "layout_side.py").write_text(_SIDE, encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    source.install()
    try:
        yield path
    finally:
        source.uninstall()
        sys.path.remove(str(tmp_path))
        sys.modules.pop("layout_app", None)
        sys.modules.pop("layout_side", None)
