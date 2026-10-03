"""Tests for ThemeKept: a theme-resolved value kept until the theme or its key moves."""

from unittest.mock import MagicMock

from nuiitivet.testing import mount
from nuiitivet.theme.dependency import ThemeKept
from nuiitivet.theme.plain_theme import PlainTheme
from nuiitivet.widgets.text import TextBase


def _resolver() -> MagicMock:
    return MagicMock(side_effect=lambda: object())


def test_same_key_resolves_once() -> None:
    widget = TextBase("x")
    kept: ThemeKept[object] = ThemeKept()
    resolve = _resolver()
    with mount(widget, theme=PlainTheme.light()):
        first = kept.get(widget, ("a", 1), resolve)
        second = kept.get(widget, ("a", 1), resolve)

    assert second is first
    assert resolve.call_count == 1


def test_key_change_resolves_again() -> None:
    widget = TextBase("x")
    kept: ThemeKept[object] = ThemeKept()
    resolve = _resolver()
    with mount(widget, theme=PlainTheme.light()):
        first = kept.get(widget, ("a", 1), resolve)
        second = kept.get(widget, ("a", 2), resolve)

    assert second is not first
    assert resolve.call_count == 2


def test_theme_change_resolves_again() -> None:
    widget = TextBase("x")
    kept: ThemeKept[object] = ThemeKept()
    resolve = _resolver()
    with mount(widget, theme=PlainTheme.light()) as host:
        host.layout(100, 20)
        first = kept.get(widget, None, resolve)
        host.push_theme(PlainTheme.dark())
        second = kept.get(widget, None, resolve)

    assert second is not first
    assert resolve.call_count == 2


def test_detached_widget_resolves_every_time() -> None:
    widget = TextBase("x")
    kept: ThemeKept[object] = ThemeKept()
    resolve = _resolver()
    with mount(widget, scope=False):
        kept.get(widget, None, resolve)
        kept.get(widget, None, resolve)

    assert resolve.call_count == 2


def test_clear_drops_the_value() -> None:
    widget = TextBase("x")
    kept: ThemeKept[object] = ThemeKept()
    resolve = _resolver()
    with mount(widget, theme=PlainTheme.light()):
        kept.get(widget, None, resolve)
        kept.clear()
        kept.get(widget, None, resolve)

    assert resolve.call_count == 2
