"""Window sizing / positioning shorthand parsing."""
from __future__ import annotations

import pytest

from nuiitivet.layout.container import Container
from nuiitivet.runtime.window import Window
from nuiitivet.runtime.window_sizing import (
    WindowPosition,
    WindowSizing,
    parse_window_position,
    parse_window_sizing,
)


class TestParseWindowSizing:
    def test_int_is_fixed(self) -> None:
        assert parse_window_sizing(800) == WindowSizing.fixed(800)

    def test_auto_string(self) -> None:
        assert parse_window_sizing("auto") == WindowSizing.auto()

    def test_passthrough(self) -> None:
        sizing = WindowSizing.fixed(640)
        assert parse_window_sizing(sizing) is sizing

    def test_rejects_other_types(self) -> None:
        with pytest.raises(TypeError):
            parse_window_sizing(1.5)  # type: ignore[arg-type]


class TestParseWindowPosition:
    def test_alignment_string(self) -> None:
        assert parse_window_position("center") == WindowPosition("center")

    def test_string_is_normalized(self) -> None:
        assert parse_window_position("Top_Right") == WindowPosition("top-right")

    def test_passthrough(self) -> None:
        position = WindowPosition("bottom-left", offset=(10.0, -5.0), screen_index=1)
        assert parse_window_position(position) is position

    def test_rejects_invalid_alignment(self) -> None:
        with pytest.raises(ValueError):
            parse_window_position("middle")

    def test_rejects_other_types(self) -> None:
        with pytest.raises(TypeError):
            parse_window_position(("center",))  # type: ignore[arg-type]


class TestWindowPositionShorthand:
    def test_window_accepts_alignment_string(self) -> None:
        window = Window(content=Container(), window_position="center")
        assert window.window_position == WindowPosition("center")

    def test_window_accepts_explicit_position(self) -> None:
        position = WindowPosition.alignment("top-right", offset=(-20, 20), screen_index=0)
        window = Window(content=Container(), window_position=position)
        assert window.window_position is position

    def test_window_position_defaults_to_none(self) -> None:
        window = Window(content=Container())
        assert window.window_position is None
