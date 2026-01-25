"""Test Icon name Observable integration."""

from nuiitivet.material.icon import Icon
from nuiitivet.material.symbols import Symbols
from nuiitivet.observable import _ObservableValue


def test_icon_name_observable_updates_from_str() -> None:
    name_obs = _ObservableValue("home")
    icon = Icon(name_obs)

    icon.on_mount()
    assert icon.name == "home"

    name_obs.value = "menu"
    assert icon.name == "menu"


def test_icon_name_observable_updates_from_symbol() -> None:
    name_obs = _ObservableValue(Symbols.home)
    icon = Icon(name_obs)

    icon.on_mount()
    assert icon.name == Symbols.home.ligature()
    assert icon._symbol_codepoint == Symbols.home.glyph()

    name_obs.value = Symbols.menu
    assert icon.name == Symbols.menu.ligature()
    assert icon._symbol_codepoint == Symbols.menu.glyph()


def test_icon_name_observable_unsubscribes_on_unmount() -> None:
    name_obs = _ObservableValue("home")
    icon = Icon(name_obs)

    icon.on_mount()
    icon.on_unmount()

    name_obs.value = "menu"
    assert icon.name == "home"
