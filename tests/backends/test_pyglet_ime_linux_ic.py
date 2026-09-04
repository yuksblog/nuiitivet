"""Tests for the input-context handover in the Linux IME patch.

``install_patch`` swaps pyglet's input context for a callback-style one so inline
preedit can be rendered. If it retires pyglet's IC before knowing whether the
replacement exists, an IM that cannot honour ``XIMPreeditCallbacks`` -- the
built-in ``@im=none`` used when no IME server runs -- leaves ``_x_ic = None``.
pyglet then calls ``XUnsetICFocus(None)`` on the next FocusOut and libX11
segfaults. These tests pin the ordering with a fake xlib, so no X server or IM
is involved.
"""

import sys
from types import SimpleNamespace
from typing import Any

import pytest

from nuiitivet.backends.pyglet.ime import linux as ime_linux


# The module only defines its internals under `sys.platform == "linux"`, so a
# mypy run on any other platform cannot see them.
_ime: Any = ime_linux

pytestmark = pytest.mark.skipif(
    sys.platform != "linux" or getattr(ime_linux, "xlib", None) is None,
    reason="The Linux IME patch is only defined when libX11 is loadable",
)

ORIGINAL_IC = 0x1111
NEW_IC = 0x2222


class _FakeXlib:
    """A libX11 stand-in that records XDestroyIC calls and fakes XCreateIC."""

    def __init__(self, created_ic: int) -> None:
        self._created_ic = created_ic
        self.destroyed: list[int] = []
        self.create_ic_calls = 0

    def XVaCreateNestedList(self, *args: Any) -> object:
        return object()

    def XCreateIC(self, *args: Any) -> int:
        self.create_ic_calls += 1
        # Non-zero when the IM supports the requested style, 0 (NULL) otherwise.
        return self._created_ic

    def XDestroyIC(self, ic: int) -> None:
        self.destroyed.append(ic)


def _fake_window() -> Any:
    return SimpleNamespace(
        _x_display=object(),
        _window=0x3333,
        _x_ic=ORIGINAL_IC,
        display=SimpleNamespace(_x_im=0x4444),
        register_event_type=lambda name: None,
    )


@pytest.fixture(autouse=True)
def _isolated_globals(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the module's IC map and callback anchors out of other tests."""
    monkeypatch.setattr(ime_linux, "_ic_map", {})
    monkeypatch.setattr(ime_linux, "_callbacks", [])


def test_original_ic_kept_when_the_im_rejects_the_callback_style(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    xlib = _FakeXlib(created_ic=0)
    monkeypatch.setattr(ime_linux, "xlib", xlib)
    window = _fake_window()

    ime_linux.install_patch(window, None)

    # Never None -- that is the pointer pyglet hands to XUnsetICFocus on FocusOut.
    assert window._x_ic == ORIGINAL_IC
    assert xlib.destroyed == []


def test_original_ic_destroyed_only_after_the_replacement_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    xlib = _FakeXlib(created_ic=NEW_IC)
    monkeypatch.setattr(ime_linux, "xlib", xlib)
    window = _fake_window()

    ime_linux.install_patch(window, None)

    assert window._x_ic == NEW_IC
    assert xlib.destroyed == [ORIGINAL_IC]
    assert _ime._ic_map[NEW_IC] is window


def test_callback_trampolines_are_not_retained_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    xlib = _FakeXlib(created_ic=0)
    monkeypatch.setattr(ime_linux, "xlib", xlib)

    ime_linux.install_patch(_fake_window(), None)

    # A failed patch has nothing to invoke them; anchoring them would leak.
    assert _ime._callbacks == []


def test_callback_trampolines_are_retained_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    xlib = _FakeXlib(created_ic=NEW_IC)
    monkeypatch.setattr(ime_linux, "xlib", xlib)

    ime_linux.install_patch(_fake_window(), None)

    # The IM calls these from C; dropping the references would crash later.
    assert len(_ime._callbacks) == 4
