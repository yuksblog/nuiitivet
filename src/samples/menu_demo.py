"""Material Design 3 Menu widget demo."""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.material import FilledButton, Menu, MenuDivider, MenuItem, SubMenuItem, Text
from nuiitivet.material import App
from nuiitivet.modifiers.popup import light_dismiss
from nuiitivet.observable.value import Observable


is_open: Observable[bool] = Observable(False)


def _close_menu() -> None:
    is_open.value = False


def _toggle_menu() -> None:
    is_open.value = not is_open.value


def _build_menu() -> Menu:
    return Menu(
        items=[
            MenuItem("New", on_click=lambda: print("New")),
            MenuItem("Open...", on_click=lambda: print("Open")),
            MenuDivider(),
            MenuItem("Save", leading_icon="save", on_click=lambda: print("Save")),
            MenuItem("Save As...", trailing="Shift+Ctrl+S", disabled=True),
            SubMenuItem(
                "Export",
                items=[
                    MenuItem("PNG", on_click=lambda: print("PNG")),
                    MenuItem("SVG", on_click=lambda: print("SVG")),
                ],
            ),
            MenuDivider(),
            MenuItem("Exit", on_click=lambda: print("Exit")),
        ],
        on_dismiss=_close_menu,
    )


def main() -> None:
    menu = _build_menu()

    trigger = FilledButton("File", on_click=_toggle_menu).modifier(
        light_dismiss(
            menu,
            is_open=is_open,
            alignment="bottom-left",
            anchor="top-left",
        )
    )

    content = Column(
        children=[
            Text("Menu Demo"),
            trigger,
        ],
        gap=16,
        padding=24,
    )

    app = App(content=content, width=500, height=600)
    app.run()


if __name__ == "__main__":
    main()
