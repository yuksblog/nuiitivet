"""The pyglet runner hands the App's icon to every window it makes, and survives a file it cannot read."""

from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from nuiitivet.backends.pyglet.runner import _apply_app_icon, load_app_icon
from nuiitivet.common.logging_once import _clear_log_once_keys_for_tests

ICON = Path(__file__).resolve().parents[2] / "samples" / "window" / "assets" / "app_icon.png"


class _Window:
    def __init__(self) -> None:
        self.icons: list[object] = []

    def set_icon(self, *images: object) -> None:
        self.icons.extend(images)


@pytest.fixture(autouse=True)
def _fresh_once_log() -> None:
    _clear_log_once_keys_for_tests()


def test_the_sample_icon_decodes() -> None:
    image = load_app_icon(ICON)
    assert image is not None
    assert (image.width, image.height) == (256, 256)


def test_a_missing_file_is_logged_once_and_yields_no_icon(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    missing = tmp_path / "nope.png"
    with caplog.at_level(logging.ERROR, logger="nuiitivet.backends.pyglet.runner"):
        assert load_app_icon(missing) is None
        assert load_app_icon(missing) is None
    assert [record.getMessage() for record in caplog.records] == [f"App icon could not be loaded: {missing}"]


def test_every_window_gets_the_icon() -> None:
    app = SimpleNamespace(icon_path=ICON)
    first, second = _Window(), _Window()
    _apply_app_icon(app, first)
    _apply_app_icon(app, second)
    assert len(first.icons) == 1
    assert len(second.icons) == 1


def test_no_icon_path_sets_nothing() -> None:
    window = _Window()
    _apply_app_icon(SimpleNamespace(icon_path=None), window)
    assert window.icons == []
