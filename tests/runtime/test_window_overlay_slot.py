"""``overlay`` takes an instance or a factory, under the ``content`` reload rule."""

from __future__ import annotations

import logging
from typing import Iterator

import pytest

from nuiitivet.dev.session import DevSession, set_dev_session
from nuiitivet.layout.container import Container
from nuiitivet.material.navigator import MaterialNavigator
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.window import MaterialWindow
from nuiitivet.overlay.overlay import Overlay
from nuiitivet.runtime.window import Window
from nuiitivet.testing import AppHarness

SIZE = (200, 120)


@pytest.fixture
def dev_session() -> Iterator[None]:
    set_dev_session(DevSession())
    try:
        yield
    finally:
        set_dev_session(None)


def test_overlay_factory_is_not_inert() -> None:
    assert Window(content=Container, overlay=Overlay)._hot_reload_inert is False


def test_overlay_instance_is_inert() -> None:
    assert Window(content=Container, overlay=Overlay())._hot_reload_inert is True


def test_overlay_instance_warns_under_dev_session(
    dev_session: None, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="nuiitivet.runtime.window"):
        window = Window(content=Container, overlay=MaterialOverlay())

    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert f"Window id={window.id}" in warnings[0]
    assert "MaterialOverlay" in warnings[0]
    assert "overlay=" in warnings[0]


def test_overlay_factory_is_silent_under_dev_session(
    dev_session: None, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="nuiitivet.runtime.window"):
        Window(content=Container, overlay=Overlay)

    assert not caplog.records


def test_overlay_rejects_a_non_callable() -> None:
    with pytest.raises(TypeError, match="'overlay'"):
        Window(content=Container, overlay=42)  # type: ignore[arg-type]


@pytest.mark.parametrize("keyword", ["overlay_factory", "overlay_intents", "overlay_routes"])
def test_removed_overlay_keywords_are_rejected(keyword: str) -> None:
    with pytest.raises(TypeError):
        MaterialWindow(content=Container, **{keyword: {}})  # type: ignore[arg-type]


def test_replacing_the_overlay_keeps_the_material_navigator() -> None:
    with AppHarness(Container(), size=SIZE, overlay=Overlay) as app:
        assert type(app.window.overlay) is Overlay
        assert isinstance(app.window.navigator, MaterialNavigator)


def test_a_reload_rebuilds_a_factory_overlay_and_keeps_an_instance() -> None:
    with AppHarness(Container(), size=SIZE, overlay=MaterialOverlay) as app:
        assert app.window._rebuild_content_root().overlay is not app.window.overlay

    instance = MaterialOverlay()
    with AppHarness(Container(), size=SIZE, overlay=instance) as app:
        assert app.window.overlay is instance
        assert app.window._rebuild_content_root().overlay is instance
