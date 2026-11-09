"""Fixtures shared by the platform tests."""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Iterator

import pytest

_TIMEOUT = 5.0


@pytest.fixture
def session_bus(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """A private session bus; ``DBUS_SESSION_BUS_ADDRESS`` points at it."""
    if sys.platform != "linux":
        pytest.skip("The session bus backends are Linux-only")
    pytest.importorskip("jeepney")
    daemon = shutil.which("dbus-daemon")
    if daemon is None:
        pytest.skip("dbus-daemon is not installed")
    process = subprocess.Popen(
        [daemon, "--session", "--nofork", "--print-address"], stdout=subprocess.PIPE, text=True
    )
    assert process.stdout is not None
    address = process.stdout.readline().strip()
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", address)
    try:
        yield address
    finally:
        process.terminate()
        process.wait(timeout=_TIMEOUT)
