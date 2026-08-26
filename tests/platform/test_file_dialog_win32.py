"""Windows-only smoke tests for the in-process IFileDialog backend.

CI runs on Linux, so these exercise nothing there; run them manually on a
Windows machine. They construct real COM objects but never show a dialog.
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="IFileDialog backend is Windows-only"
)


def test_backend_constructs_and_initializes_com():
    from nuiitivet.platform.file_dialog_win32 import Win32FileDialogBackend

    backend = Win32FileDialogBackend()
    assert backend.runs_on_ui_thread is True


def test_selected_backend_is_in_process():
    import nuiitivet.platform.file_dialog as fd
    from nuiitivet.platform.file_dialog_win32 import Win32FileDialogBackend

    assert isinstance(fd._create_backend(), Win32FileDialogBackend)
