"""``X.of()`` called before mount must name the timing, not blame the provider.

Two premature cases exist: before ``super().__init__()`` (no ``_parent``
attribute at all) and after ``__init__`` but before the widget is attached
(``_parent is None``). Both must report "before ... mounted"; a widget that *is*
attached, or a mounted root, must keep the ordinary "no such provider" message.
"""

import logging

import pytest

from nuiitivet.layout.geometry import Geometry
from nuiitivet.layout.container import Container
from nuiitivet.navigation.navigator import Navigator
from nuiitivet.overlay.overlay import Overlay
from nuiitivet.runtime.app import App
from nuiitivet.theme.theme import Theme
from nuiitivet.widgeting.widget import Widget


class _EarlyLookup(Widget):
    """Calls ``of()`` before ``super().__init__()`` — no ``_parent`` yet."""

    def __init__(self, lookup) -> None:  # type: ignore[no-untyped-def]
        self.result = lookup(self)
        super().__init__()


def _lookups():
    """(id, callable) for every ``of()`` that raises on failure."""
    return [
        ("Geometry", lambda w: Geometry.of(w)),
        ("Navigator", lambda w: Navigator.of(w)),
        ("Overlay", lambda w: Overlay.of(w)),
        ("App", lambda w: App.of(w)),
    ]


@pytest.mark.parametrize("name,lookup", _lookups(), ids=[n for n, _ in _lookups()])
def test_of_before_super_init_reports_premature(name, lookup) -> None:
    with pytest.raises(RuntimeError, match=r"before super\(\).__init__\(\) had run"):
        _EarlyLookup(lookup)


@pytest.mark.parametrize("name,lookup", _lookups(), ids=[n for n, _ in _lookups()])
def test_of_after_init_before_mount_reports_premature(name, lookup) -> None:
    widget = Widget()

    with pytest.raises(RuntimeError, match="before it was mounted"):
        lookup(widget)


@pytest.mark.parametrize("name,lookup", _lookups(), ids=[n for n, _ in _lookups()])
def test_premature_message_points_at_on_mount(name, lookup) -> None:
    with pytest.raises(RuntimeError, match="on_mount"):
        lookup(Widget())


@pytest.mark.parametrize("name,lookup", _lookups(), ids=[n for n, _ in _lookups()])
def test_attached_widget_keeps_provider_not_found_message(name, lookup) -> None:
    """A parent link exists, so the failure really is a missing provider."""
    child = Widget()
    Container().add_child(child)

    with pytest.raises(RuntimeError) as excinfo:
        lookup(child)

    assert "before it was mounted" not in str(excinfo.value)


@pytest.mark.parametrize("name,lookup", _lookups(), ids=[n for n, _ in _lookups()])
def test_mounted_root_keeps_provider_not_found_message(name, lookup) -> None:
    """A mounted root has no parent, but its chain is real: not premature."""
    root = Widget()
    root.mount(None)

    with pytest.raises(RuntimeError) as excinfo:
        lookup(root)

    assert "before it was mounted" not in str(excinfo.value)


def test_geometry_of_resolves_after_attach() -> None:
    """The premature check must not disturb a lookup that should succeed."""
    child = Widget()
    container = Container()
    container.add_child(child)
    geometry = Geometry(container)

    assert Geometry.of(child) is geometry


def test_theme_of_on_an_unattached_widget_falls_back_quietly(caplog) -> None:
    """Measuring a widget outside an App is legitimate, not a mistake.

    A constructed-but-unattached widget is indistinguishable at runtime from a
    widget being measured offscreen, so this resolves the light default rather
    than raising or warning. Under a pull the fallback is self-correcting: the
    next read, once the widget is attached, sees the real theme.
    """

    class _ThemeProbe(Widget):
        pass

    with caplog.at_level(logging.WARNING, logger="nuiitivet.theme.theme"):
        theme = Theme.of(_ThemeProbe())

    assert theme.mode == "light"
    assert caplog.records == []


def test_theme_of_before_super_init_raises() -> None:
    """No ``_parent`` attribute at all can only mean one thing: still in
    ``__init__``. There is no chain to resolve against and no identity to hang a
    dependency on, so the call is undefined rather than merely early."""
    with pytest.raises(RuntimeError, match=r"before super\(\)\.__init__\(\)"):
        _EarlyLookup(Theme.of)


def test_theme_of_attached_but_detached_tree_stays_quiet(caplog) -> None:
    """No AppScope above, but the chain is real — nothing to warn about."""
    child = Widget()
    Container().add_child(child)

    with caplog.at_level(logging.WARNING, logger="nuiitivet.theme.theme"):
        theme = Theme.of(child)

    assert theme.mode == "light"
    assert [r for r in caplog.records if "before it was mounted" in r.getMessage()] == []
