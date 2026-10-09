"""Tests for the pyglet runner's initial window placement.

``client_location`` is the pure arithmetic; the OS queries are exercised with
fakes standing in for AppKit, user32 and Xlib, since no test host has all three.
"""

import ctypes
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from nuiitivet.backends.pyglet import window_placement as placement
from nuiitivet.backends.pyglet.window_placement import (
    FrameExtents,
    ScreenRect,
    apply_initial_position,
    client_location,
    frame_extents_of,
    work_area_of,
)
from nuiitivet.runtime.window_sizing import WindowPosition

WORK = ScreenRect(0, 0, 2560, 1392)
NO_FRAME = FrameExtents()
WIN32_FRAME = FrameExtents(left=8, top=31, right=8, bottom=8)


def _rect(x: float, y: float, width: float, height: float) -> SimpleNamespace:
    """An NSRect stand-in: ``origin.x/y`` and ``size.width/height``."""
    return SimpleNamespace(origin=SimpleNamespace(x=x, y=y), size=SimpleNamespace(width=width, height=height))


class TestClientLocation:
    def test_top_right_puts_the_top_edge_at_the_work_area_top(self) -> None:
        assert client_location(WindowPosition("top-right"), WORK, NO_FRAME, 640, 480) == (1920, 0)

    def test_bottom_left_puts_the_bottom_edge_at_the_work_area_bottom(self) -> None:
        assert client_location(WindowPosition("bottom-left"), WORK, NO_FRAME, 640, 480) == (0, 912)

    def test_center(self) -> None:
        assert client_location(WindowPosition("center"), WORK, NO_FRAME, 640, 480) == (960, 456)

    def test_single_axis_alignments(self) -> None:
        assert client_location(WindowPosition("top-center"), WORK, NO_FRAME, 640, 480) == (960, 0)
        assert client_location(WindowPosition("center-right"), WORK, NO_FRAME, 640, 480) == (1920, 456)

    def test_positive_y_offset_moves_the_window_down(self) -> None:
        pos = WindowPosition("top-left", offset=(-20, 20))
        assert client_location(pos, WORK, NO_FRAME, 640, 480) == (-20, 20)

    def test_frame_extents_keep_the_title_bar_inside_the_work_area(self) -> None:
        assert client_location(WindowPosition("top-right"), WORK, WIN32_FRAME, 640, 480) == (1912, 31)
        assert client_location(WindowPosition("bottom-left"), WORK, WIN32_FRAME, 640, 480) == (8, 904)

    def test_work_area_origin_is_added(self) -> None:
        work = ScreenRect(2560, 100, 1920, 1080)
        assert client_location(WindowPosition("top-left"), work, NO_FRAME, 640, 480) == (2560, 100)


class TestApplyInitialPosition:
    def _window(self) -> MagicMock:
        window = MagicMock()
        window.width = 640
        window.height = 480
        return window

    def test_moves_the_client_area_to_the_computed_point(self, monkeypatch: pytest.MonkeyPatch) -> None:
        screen = SimpleNamespace(x=0, y=0, width=2560, height=1440)
        display = SimpleNamespace(get_screens=lambda: [screen])
        monkeypatch.setattr(placement.pyglet.display, "get_display", lambda: display)
        monkeypatch.setattr(placement, "work_area_of", lambda s, w: WORK)
        monkeypatch.setattr(placement, "frame_extents_of", lambda w: WIN32_FRAME)
        window = self._window()

        apply_initial_position(window, WindowPosition("top-right"))

        window.set_location.assert_called_once_with(1912, 31)

    def test_screen_index_is_clamped_to_the_last_screen(self, monkeypatch: pytest.MonkeyPatch) -> None:
        first = SimpleNamespace(x=0, y=0, width=1920, height=1080)
        second = SimpleNamespace(x=1920, y=0, width=1280, height=720)
        display = SimpleNamespace(get_screens=lambda: [first, second])
        monkeypatch.setattr(placement.pyglet.display, "get_display", lambda: display)
        seen: list[object] = []

        def work_area_of(screen: object, window: object) -> ScreenRect:
            seen.append(screen)
            return ScreenRect(1920, 0, 1280, 720)

        monkeypatch.setattr(placement, "work_area_of", work_area_of)
        monkeypatch.setattr(placement, "frame_extents_of", lambda w: NO_FRAME)
        window = self._window()

        apply_initial_position(window, WindowPosition("top-left", screen_index=5))

        assert seen == [second]
        window.set_location.assert_called_once_with(1920, 0)

    def test_falls_back_to_the_window_screen_when_none_listed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(placement.pyglet.display, "get_display", lambda: SimpleNamespace(get_screens=list))
        monkeypatch.setattr(placement, "work_area_of", lambda s, w: WORK)
        monkeypatch.setattr(placement, "frame_extents_of", lambda w: NO_FRAME)
        window = self._window()

        apply_initial_position(window, WindowPosition("bottom-right"))

        window.set_location.assert_called_once_with(1920, 912)


class TestCocoa:
    def test_work_area_is_flipped_to_top_left_coordinates(self) -> None:
        # A 1080-high screen with a 25 px menu bar and an 80 px dock.
        ns_screen = SimpleNamespace(visibleFrame=lambda: _rect(0, 80, 1920, 975))
        screen = SimpleNamespace(_ns_screen=ns_screen)
        window_screen = SimpleNamespace(frame=lambda: _rect(0, 0, 1920, 1080))
        window = SimpleNamespace(_nswindow=SimpleNamespace(screen=lambda: window_screen))

        assert placement._cocoa_work_area(screen, window) == ScreenRect(0, 25, 1920, 975)

    def test_frame_extents_are_the_title_bar(self) -> None:
        frame = _rect(100, 200, 800, 628)
        nswindow = SimpleNamespace(frame=lambda: frame, contentRectForFrameRect_=lambda f: _rect(100, 200, 800, 600))

        assert placement._cocoa_frame_extents(nswindow) == FrameExtents(top=28)


class _FakeUser32:
    """user32 whose calls fill the structures passed by reference."""

    def __init__(self, *, work: tuple[int, int, int, int], frame: tuple[int, int, int, int]) -> None:
        self.work = work
        self.frame = frame
        self.handles: list[int] = []

    def GetMonitorInfoW(self, handle: ctypes.c_void_p, info_ref: object) -> int:
        self.handles.append(handle.value or 0)
        rc = info_ref._obj.rcWork  # type: ignore[attr-defined]
        rc.left, rc.top, rc.right, rc.bottom = self.work
        return 1

    def GetWindowRect(self, handle: ctypes.c_void_p, rect_ref: object) -> int:
        self.handles.append(handle.value or 0)
        rect = rect_ref._obj  # type: ignore[attr-defined]
        rect.left, rect.top, rect.right, rect.bottom = self.frame
        return 1

    def GetClientRect(self, handle: ctypes.c_void_p, rect_ref: object) -> int:
        rect = rect_ref._obj  # type: ignore[attr-defined]
        rect.left, rect.top, rect.right, rect.bottom = (0, 0, 640, 480)
        return 1

    def ClientToScreen(self, handle: ctypes.c_void_p, point_ref: object) -> int:
        point = point_ref._obj  # type: ignore[attr-defined]
        point.x, point.y = (self.frame[0] + 8, self.frame[1] + 31)
        return 1


class TestWin32:
    def test_work_area_comes_from_the_monitor_handle(self) -> None:
        user32 = _FakeUser32(work=(0, 0, 2560, 1392), frame=(0, 0, 0, 0))
        screen = SimpleNamespace(_handle=ctypes.c_void_p(0x1_0000_0001))

        assert placement._win32_work_area(screen, user32) == ScreenRect(0, 0, 2560, 1392)
        assert user32.handles == [0x1_0000_0001]

    def test_frame_extents_from_window_and_client_rects(self) -> None:
        # The frame of a 640x480 client at (1912, 0): 8 px borders, a 31 px title bar.
        user32 = _FakeUser32(work=(0, 0, 0, 0), frame=(1904, -31, 2560, 488))

        assert placement._win32_frame_extents(0x2000, user32) == WIN32_FRAME
        assert user32.handles == [0x2000]

    def test_missing_handles_give_none(self) -> None:
        user32 = _FakeUser32(work=(0, 0, 0, 0), frame=(0, 0, 0, 0))

        assert placement._win32_work_area(SimpleNamespace(), user32) is None
        assert placement._win32_frame_extents(None, user32) is None


class TestX11:
    def _patch_cardinals(self, monkeypatch: pytest.MonkeyPatch, values: dict[bytes, list[int]]) -> None:
        monkeypatch.setattr(placement, "_x11_cardinals", lambda xlib, display, xwindow, name: values.get(name, []))

    def test_work_area_of_the_current_desktop_clipped_to_the_screen(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_cardinals(
            monkeypatch,
            {
                b"_NET_WORKAREA": [0, 0, 3840, 1080, 0, 0, 3840, 1050],
                b"_NET_CURRENT_DESKTOP": [1],
            },
        )
        screen = SimpleNamespace(x=1920, y=0, width=1920, height=1080)
        window = SimpleNamespace(_x_display=object(), _x_screen_id=0, _window=7)
        xlib = SimpleNamespace(XRootWindow=lambda display, screen_id: 1)

        assert placement._x11_work_area(screen, window, xlib) == ScreenRect(1920, 0, 1920, 1050)

    def test_frame_extents_property_order_is_left_right_top_bottom(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_cardinals(monkeypatch, {b"_NET_FRAME_EXTENTS": [4, 5, 28, 6]})
        window = SimpleNamespace(_x_display=object(), _window=7)

        assert placement._x11_frame_extents(window, None) == FrameExtents(left=4, top=28, right=5, bottom=6)

    def test_missing_properties_give_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_cardinals(monkeypatch, {})
        screen = SimpleNamespace(x=0, y=0, width=1920, height=1080)
        window = SimpleNamespace(_x_display=object(), _x_screen_id=0, _window=7)
        xlib = SimpleNamespace(XRootWindow=lambda display, screen_id: 1)

        assert placement._x11_work_area(screen, window, xlib) is None
        assert placement._x11_frame_extents(window, xlib) is None


class TestFallbacks:
    def test_work_area_falls_back_to_the_screen_bounds(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(placement.sys, "platform", "darwin")
        screen = SimpleNamespace(x=0, y=0, width=1920, height=1080, _ns_screen=None, get_nsscreen=lambda: None)

        assert work_area_of(screen, SimpleNamespace()) == ScreenRect(0, 0, 1920, 1080)

    def test_frame_extents_fall_back_to_zero_on_a_query_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(placement.sys, "platform", "darwin")

        assert frame_extents_of(SimpleNamespace()) == FrameExtents()
