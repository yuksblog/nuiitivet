"""In-app menu bar behavior, driven through the AppHarness."""

from __future__ import annotations

from typing import List

from nuiitivet.input.shortcut import Shortcut
from nuiitivet.layout.column import Column
from nuiitivet.material.text import Text
from nuiitivet.menubar.bar import MenuBarWidget
from nuiitivet.menubar.model import MenuBar, MenuBarItem
from nuiitivet.menubar.slots import MenuBarArea
from nuiitivet.menubar.style import MenuBarStyle
from nuiitivet.observable import Observable


def _find_bar(root) -> MenuBarWidget:
    found: List[MenuBarWidget] = []

    def walk(widget) -> None:
        if isinstance(widget, MenuBarWidget):
            found.append(widget)
        for child in widget.children_snapshot():
            walk(child)
        built = getattr(widget, "built_child", None)
        if built is not None and built is not widget:
            walk(built)

    walk(root)
    assert found, "no MenuBarWidget in the tree"
    return found[0]


def _simple_model(record: List[str], *, save_enabled=True) -> MenuBar:
    return MenuBar(
        [
            MenuBarItem(
                "File",
                submenu=[
                    MenuBarItem("Open...", on_select=lambda: record.append("open")),
                    MenuBarItem.separator(),
                    MenuBarItem(
                        "Save",
                        on_select=lambda: record.append("save"),
                        shortcut="Accel+S",
                        enabled=save_enabled,
                    ),
                ],
            ),
            MenuBarItem(
                "Edit",
                submenu=[MenuBarItem("Undo", on_select=lambda: record.append("undo"))],
            ),
        ]
    )


def test_menu_param_renders_bar(nuiitivet_app) -> None:
    record: List[str] = []
    app = nuiitivet_app(Text("content"), size=(800, 600), menu=_simple_model(record))
    assert app.get(label="File") is not None
    assert app.get(label="Edit") is not None


def test_no_menu_means_no_bar(nuiitivet_app) -> None:
    app = nuiitivet_app(Text("content"), size=(800, 600))
    assert app.query(label="File") is None


def test_click_opens_popup_and_activates_item(nuiitivet_app) -> None:
    record: List[str] = []
    app = nuiitivet_app(Text("content"), size=(800, 600), menu=_simple_model(record))

    assert app.query(label="Open...") is None
    app.click(label="File")
    assert app.get(label="Open...") is not None

    app.click(label="Open...")
    assert record == ["open"]
    # Activation closes the whole popup.
    assert app.query(label="Open...") is None


def test_click_again_closes_popup(nuiitivet_app) -> None:
    record: List[str] = []
    app = nuiitivet_app(Text("content"), size=(800, 600), menu=_simple_model(record))
    app.click(label="File")
    assert app.get(label="Open...") is not None
    app.click(label="File")
    assert app.query(label="Open...") is None


async def test_escape_closes_popup(nuiitivet_app) -> None:
    record: List[str] = []
    app = nuiitivet_app(Text("content"), size=(800, 600), menu=_simple_model(record))
    app.click(label="File")
    assert app.get(label="Open...") is not None
    # The release half of Escape also feeds App back-navigation, which is
    # async work; run on a real loop as production does.
    app.key("escape")
    await app.idle()
    assert app.query(label="Open...") is None


def test_accelerator_is_displayed(nuiitivet_app) -> None:
    record: List[str] = []
    app = nuiitivet_app(Text("content"), size=(800, 600), menu=_simple_model(record))
    app.click(label="File")
    expected = Shortcut.parse("Accel+S").display
    assert app.get(label=expected) is not None


def test_shortcut_fires_without_opening_menu(nuiitivet_app) -> None:
    record: List[str] = []
    app = nuiitivet_app(Text("content"), size=(800, 600), menu=_simple_model(record))
    app.key("s", modifiers=["accel"])
    assert record == ["save"]
    assert app.query(label="Open...") is None


def test_shortcut_respects_enabled(nuiitivet_app) -> None:
    record: List[str] = []
    enabled = Observable(False)
    app = nuiitivet_app(
        Text("content"),
        size=(800, 600),
        menu=_simple_model(record, save_enabled=enabled),
    )
    app.key("s", modifiers=["accel"], require_handled=False)
    assert record == []
    enabled.value = True
    app.key("s", modifiers=["accel"])
    assert record == ["save"]


def test_checked_item_toggles_before_on_select(nuiitivet_app) -> None:
    checked = Observable(False)
    seen: List[bool] = []
    model = MenuBar(
        [
            MenuBarItem(
                "View",
                submenu=[
                    MenuBarItem(
                        "Word Wrap",
                        on_select=lambda: seen.append(checked.value),
                        checked=checked,
                    )
                ],
            )
        ]
    )
    app = nuiitivet_app(Text("content"), size=(800, 600), menu=model)
    app.click(label="View")
    app.click(label="Word Wrap")
    assert checked.value is True
    assert seen == [True]


def test_menu_bar_area_takes_over_from_default_slot(nuiitivet_app) -> None:
    record: List[str] = []
    content = Column(children=[MenuBarArea(), Text("content")])
    app = nuiitivet_app(content, size=(800, 600), menu=_simple_model(record))
    # Exactly one bar renders: the area's; the default slot stays empty.
    assert len(app.get_all(label="File")) == 1
    app.click(label="File")
    app.click(label="Open...")
    assert record == ["open"]


def test_menu_replacement_rebuilds_bar(nuiitivet_app) -> None:
    record: List[str] = []
    app = nuiitivet_app(Text("content"), size=(800, 600), menu=_simple_model(record))
    assert app.get(label="File") is not None

    app._app.menu = MenuBar(
        [MenuBarItem("View", submenu=[MenuBarItem("Zoom", on_select=lambda: None)])]
    )
    app.settle()
    assert app.query(label="File") is None
    assert app.get(label="View") is not None


def test_submenu_survives_overlay_restack(nuiitivet_app) -> None:
    # Opening a nested submenu adds an overlay entry, which restacks and
    # transiently remounts the open popup; the bar must not read that as a
    # dismissal (popup_gone checks handle.done()).
    record: List[str] = []
    model = MenuBar(
        [
            MenuBarItem(
                "Edit",
                submenu=[
                    MenuBarItem("Undo", on_select=lambda: record.append("undo")),
                    MenuBarItem(
                        "Advanced",
                        submenu=[MenuBarItem("Sort", on_select=lambda: record.append("sort"))],
                    ),
                ],
            )
        ]
    )
    app = nuiitivet_app(Text("content"), size=(800, 600), menu=model)
    app.click(label="Edit")
    app.key("down")  # focus Undo
    app.key("down")  # focus Advanced
    app.key("right")  # enter the submenu
    assert app.get(label="Sort") is not None
    # The top-level popup is still open and the bar still tracks it.
    assert app.get(label="Undo") is not None
    app.click(label="Sort")
    assert record == ["sort"]
    assert app.query(label="Undo") is None


def test_outside_click_closes_and_next_click_reopens(nuiitivet_app) -> None:
    record: List[str] = []
    app = nuiitivet_app(Text("content"), size=(800, 600), menu=_simple_model(record))
    app.click(label="File")
    assert app.get(label="Open...") is not None
    app.click(x=400, y=400)
    assert app.query(label="Open...") is None
    # The bar state was reconciled, so one click reopens.
    app.click(label="File")
    assert app.get(label="Open...") is not None


def test_popup_opens_flush_below_the_bar(nuiitivet_app) -> None:
    # The anchor rect is global but the overlay starts below the bar; a
    # popup must not inherit that offset as a gap (seen on Windows/Linux).
    record: List[str] = []
    app = nuiitivet_app(Text("content"), size=(800, 600), menu=_simple_model(record))
    app.click(label="File")
    app.settle()
    bar = _find_bar(app._app.root)
    popup = bar._popup
    assert popup is not None
    rect = popup.global_layout_rect
    assert rect is not None
    assert rect[1] == MenuBarStyle().bar_height


def test_standard_item_dispatches_role_intent(nuiitivet_app) -> None:
    from nuiitivet.runtime.intents import RestoreWindowIntent

    model = MenuBar([MenuBarItem("Window", submenu=[MenuBarItem.restore()])])
    app = nuiitivet_app(Text("content"), size=(800, 600), menu=model)
    seen: List[object] = []
    app._app.dispatch = seen.append  # type: ignore[method-assign]
    app.click(label="Window")
    app.click(label="Restore")
    assert [type(intent) for intent in seen] == [RestoreWindowIntent]


def test_top_level_label_updates_live(nuiitivet_app) -> None:
    label = Observable("File")
    model = MenuBar(
        [MenuBarItem(label, submenu=[MenuBarItem("Open", on_select=lambda: None)])]
    )
    app = nuiitivet_app(Text("content"), size=(800, 600), menu=model)
    assert app.get(label="File") is not None
    label.value = "Datei"
    app.settle()
    assert app.query(label="File") is None
    assert app.get(label="Datei") is not None
