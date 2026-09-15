"""Tests for how the pyglet runner offers input to the dev-only layers."""

from __future__ import annotations

from typing import Any

from nuiitivet.backends.pyglet.runner import _dev_consumed


class _Takes:
    def __init__(self) -> None:
        self.seen: list[str] = []

    def on_text(self, app: Any, text: str) -> bool:
        self.seen.append(text)
        return True

    def on_text_motion(self, app: Any, motion: int, select: bool) -> bool:
        self.seen.append(f"motion {motion} {select}")
        return True


class _KeysOnly:
    def on_key_press(self, app: Any, name: str, modifier_keys: int) -> bool:
        return True


class _App:
    def __init__(self) -> None:
        self._source_jump: Any = _KeysOnly()
        self._select_mode: Any = _KeysOnly()
        self._layout_edit_mode: Any = _Takes()


def test_a_layer_without_the_hook_is_skipped_and_the_next_one_takes_it() -> None:
    app = _App()

    assert _dev_consumed(app, "on_text", app, "a") is True
    assert app._layout_edit_mode.seen == ["a"]


def test_nothing_taking_it_means_not_consumed() -> None:
    app = _App()
    app._layout_edit_mode = _KeysOnly()

    assert _dev_consumed(app, "on_text", app, "a") is False


def test_a_layer_that_raises_does_not_swallow_the_input() -> None:
    class _Broken:
        def on_text(self, app: Any, text: str) -> bool:
            raise RuntimeError("boom")

    app = _App()
    app._select_mode = _Broken()
    app._layout_edit_mode = _KeysOnly()

    assert _dev_consumed(app, "on_text", app, "a") is False


def test_a_text_motion_is_offered_the_same_way() -> None:
    app = _App()

    assert _dev_consumed(app, "on_text_motion", app, 3, True) is True
    assert app._layout_edit_mode.seen == ["motion 3 True"]
