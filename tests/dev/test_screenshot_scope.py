"""Tests for element-scoped screenshots: target → clip rect, and the clipped render."""

from __future__ import annotations

import struct
from typing import Any, Optional

import pytest

from nuiitivet._interaction.action import (
    DEFAULT_CAPTURE_PADDING,
    TargetNotFoundError,
    TargetNotVisibleError,
    resolve_capture_rect,
)


class _Node:
    def __init__(self, *, rect: Optional[tuple] = (100, 50, 80, 40), **identity: Any) -> None:
        self.children: list[_Node] = []
        self.built_child: Optional[_Node] = None
        self.global_layout_rect = rect
        for name, value in identity.items():
            setattr(self, name, value)

    def layout(self, width: int, height: int) -> None:
        pass

    def clear_needs_layout(self) -> None:
        pass


class _App:
    def __init__(self, root: _Node, *, width: int = 360, height: int = 240) -> None:
        self.root = root
        self.width = width
        self.height = height

    def invalidate(self) -> None:
        pass


def _app(**identity: Any) -> _App:
    root = _Node(rect=(0, 0, 360, 240), key="root")
    root.children.append(_Node(**identity))
    return _App(root)


# --- Resolution --------------------------------------------------------------


def test_key_target_is_padded_on_every_side() -> None:
    clip, info = resolve_capture_rect(_app(key="save"), key="save", padding=8)
    assert clip == (92, 42, 96, 56)
    assert info == {"type": "_Node", "key": "save"}


def test_default_padding_applies_when_unspecified() -> None:
    clip, _ = resolve_capture_rect(_app(key="save"), key="save")
    pad = DEFAULT_CAPTURE_PADDING
    assert clip == (100 - pad, 50 - pad, 80 + 2 * pad, 40 + 2 * pad)


def test_label_target_resolves_like_click() -> None:
    clip, info = resolve_capture_rect(_app(label="Save"), label="Save", padding=0)
    assert clip == (100, 50, 80, 40)
    assert info == {"type": "_Node"}


def test_padding_is_clamped_to_the_window() -> None:
    app = _app(key="corner", rect=(0, 0, 20, 20))
    clip, _ = resolve_capture_rect(app, key="corner", padding=8)
    assert clip == (0, 0, 28, 28)


def test_partly_visible_target_yields_its_visible_part() -> None:
    app = _app(key="edge", rect=(340, 100, 80, 40))
    clip, _ = resolve_capture_rect(app, key="edge", padding=0)
    assert clip == (340, 100, 20, 40)


def test_target_outside_window_is_not_visible() -> None:
    app = _app(key="gone", rect=(0, 500, 80, 40))
    with pytest.raises(TargetNotVisibleError, match="scroll_into_view"):
        resolve_capture_rect(app, key="gone")


def test_missing_target_raises() -> None:
    with pytest.raises(TargetNotFoundError, match="no widget matched"):
        resolve_capture_rect(_app(key="save"), key="nope")


def test_target_without_rect_raises() -> None:
    with pytest.raises(TargetNotFoundError, match="no layout rect"):
        resolve_capture_rect(_app(key="save", rect=None), key="save")


def test_raw_rect_is_never_padded() -> None:
    clip, info = resolve_capture_rect(_app(), rect=[10, 20, 30, 40], padding=8)
    assert clip == (10, 20, 30, 40)
    assert info == {}


def test_raw_rect_is_clamped_to_the_window() -> None:
    clip, _ = resolve_capture_rect(_app(), rect=[-10, -10, 50, 50])
    assert clip == (0, 0, 40, 40)


@pytest.mark.parametrize("rect", [[1, 2, 3], [0, 0, 0, 10], [0, 0, 10, -1], [1000, 0, 10, 10]])
def test_bad_raw_rect_raises(rect: list[float]) -> None:
    with pytest.raises(ValueError):
        resolve_capture_rect(_app(), rect=rect)


def test_requires_a_scope() -> None:
    with pytest.raises(ValueError, match="requires"):
        resolve_capture_rect(_app())


# --- Rendering ---------------------------------------------------------------


def _png_size(png: bytes) -> tuple[int, int]:
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", png[16:24])
    return (width, height)


@pytest.fixture
def boxed_app() -> Any:
    """A 300x200 window with one solid red 80x40 box at (100, 50) on blue."""
    import nuiitivet.material as nv
    from nuiitivet.runtime.app import App
    from nuiitivet.runtime.window import Window

    box = nv.Box(width=80, height=40, background_color="#ff0000", key="box")
    content = nv.Stack([nv.Box(box, padding=(100, 50, 0, 0))])
    window = Window(content=content, background="#0000ff", width=300, height=200)
    return App(window).main_window


def _rgb(img: Any, x: int, y: int) -> tuple[int, int, int]:
    rgba = img.tobytes()
    offset = (y * img.width() + x) * 4
    return (rgba[offset], rgba[offset + 1], rgba[offset + 2])


def test_clipped_render_is_the_target_region(boxed_app: Any) -> None:
    clip, _ = resolve_capture_rect(boxed_app, key="box", padding=10)
    assert clip == (90, 40, 100, 60)

    png = boxed_app._render_to_png_bytes(clip=clip)
    assert _png_size(png) == (100, 60)
    assert len(png) < len(boxed_app._render_to_png_bytes())


def test_clipped_render_paints_the_target_where_it_sits(boxed_app: Any) -> None:
    img = boxed_app._render_snapshot(scale=1.0, settle=True, clip=(90.0, 40.0, 100.0, 60.0))
    full = boxed_app._render_snapshot(scale=1.0, settle=True)

    # The clip's centre is the box, its corner is the padded background -- and
    # each matches the same logical point of the full frame, whatever the
    # backend's channel order.
    assert _rgb(img, 50, 30) == _rgb(full, 140, 70)
    assert _rgb(img, 2, 2) == _rgb(full, 92, 42)
    assert _rgb(img, 50, 30) != _rgb(img, 2, 2)


def test_clipped_render_honours_scale(boxed_app: Any) -> None:
    img = boxed_app._render_snapshot(scale=2.0, settle=True, clip=(90.0, 40.0, 100.0, 60.0))
    assert (img.width(), img.height()) == (200, 120)


def test_clipped_render_excludes_the_action_overlay(
    boxed_app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from nuiitivet.dev import action_overlay

    calls: list[str] = []
    monkeypatch.setattr(action_overlay, "paint_markers", lambda **kw: calls.append("painted"))
    boxed_app._render_to_png_bytes(clip=(90.0, 40.0, 100.0, 60.0))
    assert calls == []
