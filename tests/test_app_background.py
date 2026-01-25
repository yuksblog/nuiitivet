from __future__ import annotations

from typing import List

import pytest

from nuiitivet.runtime.app import App
from nuiitivet.widgeting.widget import Widget
from nuiitivet.theme import Theme, manager as theme_manager
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.colors.utils import hex_to_rgba


class _DummyWidget(Widget):
    def __init__(self):
        super().__init__()

    def build(self) -> "Widget":
        return self

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        return None


def test_app_background_uses_resolve_color(monkeypatch):
    captured: List[tuple] = []
    # Return a concrete RGBA tuple from the resolver and capture args.
    sentinel_rgba = (0x12, 0x34, 0x56, 255)

    def fake_resolve(value, default=None, role_resolver=None, theme=None):
        captured.append((value, default))
        return sentinel_rgba

    monkeypatch.setattr("nuiitivet.runtime.app.resolve_color_to_rgba", fake_resolve)

    widget = _DummyWidget()
    app = App(content=widget, background="#123456")

    assert app._background_clear_color() == sentinel_rgba
    assert captured[-1] == ("#123456", None)


def test_app_background_updates_on_theme_change(monkeypatch):
    prev_theme = theme_manager.current
    app: App | None = None
    try:
        roles = {role: "#FFFFFF" for role in ColorRole}
        roles[ColorRole.SURFACE] = "#222222"
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme_manager.set_theme(Theme(mode="light", extensions=[MaterialThemeData(roles=roles)]))

        colors = {"count": 0}

        def fake_resolve(value, default=None, role_resolver=None, theme=None):
            colors["count"] += 1
            mat = theme_manager.current.extension(MaterialThemeData)
            assert mat is not None
            hexv = mat.roles.get(ColorRole.SURFACE)
            return hex_to_rgba(hexv)

        monkeypatch.setattr("nuiitivet.runtime.app.resolve_color_to_rgba", fake_resolve)

        widget = _DummyWidget()
        # Pass theme explicitly to avoid App overwriting it with default MaterialTheme
        app = App(content=widget, theme=theme_manager.current)
        app._dirty = False
        initial_color = app._background_clear_color()

        new_roles = {role: "#EEEEEE" for role in ColorRole}
        new_roles[ColorRole.SURFACE] = "#101010"
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme_manager.set_theme(Theme(mode="dark", extensions=[MaterialThemeData(roles=new_roles)]))

        expected_initial = hex_to_rgba("#222222")
        expected_after = hex_to_rgba("#101010")

        assert initial_color == expected_initial
        assert app._background_clear_color() == expected_after
        assert colors["count"] >= 2
        assert app._dirty is True
    finally:
        if app is not None:
            app._unsubscribe_theme_updates()
        theme_manager.set_theme(prev_theme)


def test_app_background_raises_when_unresolved():
    widget = _DummyWidget()
    with pytest.raises(ValueError):
        App(content=widget, background=None)
