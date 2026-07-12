"""Focus traversal groups — Tab between widgets, arrows/Tab inside a group.

Run it and drive it from the keyboard:

- Tab / Shift+Tab move between the Tab stops: checkbox, range slider, text field,
  and the "Open menu" button. Each widget is one stop, no matter how many
  focusable parts it has inside.
- Inside the range slider, Tab moves between its two handles and only leaves the
  slider once it steps past the last one; Shift+Tab entering from the right lands
  on the far handle. Left/Right change the focused handle's value.
- The menu is a group too: opening it focuses the first enabled item, Up/Down rove
  between items, Right/Left walk into and out of the submenu, and Tab (like Escape)
  dismisses it rather than stepping through the items.
"""

from __future__ import annotations

import nuiitivet.material as nv

is_menu_open: nv.Observable[bool] = nv.Observable(False)
last_action: nv.Observable[str] = nv.Observable("(nothing yet)")


def _toggle_menu() -> None:
    is_menu_open.value = not is_menu_open.value


def _close_menu() -> None:
    is_menu_open.value = False


def _pick(label: str) -> None:
    last_action.value = label
    _close_menu()


def main() -> None:
    menu = nv.Menu(
        items=[
            nv.MenuItem("New", leading_icon="add", on_click=lambda: _pick("New")),
            nv.MenuItem("Open...", leading_icon="folder_open", on_click=lambda: _pick("Open")),
            nv.MenuDivider(),
            nv.MenuItem("Save", leading_icon="save", trailing="Ctrl+S", on_click=lambda: _pick("Save")),
            nv.MenuItem("Save As...", disabled=True),
            nv.SubMenuItem(
                "Export",
                items=[
                    nv.MenuItem("PNG", on_click=lambda: _pick("Export PNG")),
                    nv.MenuItem("SVG", on_click=lambda: _pick("Export SVG")),
                ],
            ),
        ],
        on_dismiss=_close_menu,
    )

    menu_button = nv.Button("Open menu", on_click=_toggle_menu).modifier(
        nv.light_dismiss(
            menu,
            is_open=is_menu_open,
            alignment="bottom-left",
            anchor="top-left",
            offset=(0.0, 4.0),
        )
    )

    content = nv.Container(
        padding=24,
        child=nv.Column(
            gap=16,
            cross_alignment="start",
            children=[
                nv.Text("Tab moves between widgets. Inside a group, the group decides."),
                nv.Checkbox(),
                nv.Text("RangeSlider — one Tab stop, two handles roved with Tab"),
                nv.HorizontalRangeSlider(
                    value_start=0.25,
                    value_end=0.75,
                    width=360,
                    min_value=0.0,
                    max_value=1.0,
                ),
                nv.TextField(label="A plain Tab stop"),
                menu_button,
                nv.Text(last_action.map(lambda v: f"Last menu action: {v}")),
            ],
        ),
    )

    nv.App(content=content, title="Focus traversal", width=520, height=460).run()


if __name__ == "__main__":
    main()
