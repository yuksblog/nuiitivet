"""Auto window sizing must measure against the app's own theme.

A widget reaches its theme by walking up to the ``AppScope``, so a tree measured
before it is attached resolves against the default light theme -- and the window
comes out sized for a theme the app never installed. ``App`` therefore mounts
the tree before it measures anything.
"""

from __future__ import annotations

from nuiitivet.layout.container import Container
from nuiitivet.material.card import Card
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.text import Text
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.theme.theme import Theme
from nuiitivet.widgeting.widget import Widget

_PROBE = "Hello world, sizing probe"


def _theme_with(**theme_data_fields) -> Theme:
    return Theme(mode="light", extensions=[MaterialThemeData(roles={}, **theme_data_fields)])


def _auto_app(content: Widget, theme: Theme) -> App:
    return App(Window(content=content, width="auto", height="auto"), theme=theme)


def test_root_is_mounted_by_the_time_construction_returns() -> None:
    app = _auto_app(Container(child=Text(_PROBE)), _theme_with())

    assert app.main_window.root._mounted is True


def test_auto_size_follows_the_themes_typography() -> None:
    """A pull-based widget: ``Text`` reads its style at measure time."""
    default = _auto_app(Container(child=Text(_PROBE)), _theme_with())
    monospace = _auto_app(
        Container(child=Text(_PROBE)),
        _theme_with(_text_style=TextStyle(font_family="Courier New")),
    )

    # The two fonts do not measure the same, so a window sized against the real
    # theme cannot come out identical to one sized against the default.
    assert monospace.main_window.width != default.main_window.width


def test_auto_size_sees_styles_adopted_at_mount() -> None:
    """A push-based widget: ``Card`` adopts the theme's style in ``on_mount``.

    Measuring before mount would use the framework preset, whose border is
    0px wide, and undersize the window by the border on both edges.
    """
    bordered = CardStyle.filled().copy_with(border_width=12)
    card = Card(child=Text("probe"), padding=0)
    app = _auto_app(Container(child=card), _theme_with(_filled_card_style=bordered))

    assert card.border_width == 12
    assert (app.main_window.width, app.main_window.height) == card.preferred_size()


def test_explicit_window_size_is_not_measured() -> None:
    app = App(Window(content=Container(child=Text(_PROBE)), width=321, height=234), theme=_theme_with())

    assert (app.main_window.width, app.main_window.height) == (321, 234)


def test_on_mount_can_call_back_into_the_app(caplog) -> None:
    """``mount()`` runs inside ``App.__init__``, so the App must be usable.

    ``on_mount`` is arbitrary user code and routinely calls back into the App --
    ``invalidate()`` alone reads the window size and the debug-instrumentation
    fields. Mounting before those are initialized turns every such call into a
    swallowed ``AttributeError``, so the hook must run last.
    """
    ran: list[bool] = []

    class _CallsBackIntoApp(Container):
        def on_mount(self) -> None:
            super().on_mount()
            self.invalidate()
            self.mark_needs_layout()
            ran.append(True)

    with caplog.at_level("ERROR"):
        _auto_app(_CallsBackIntoApp(child=Text(_PROBE)), _theme_with())

    assert ran == [True]
    assert [r.message for r in caplog.records if r.levelname == "ERROR"] == []
