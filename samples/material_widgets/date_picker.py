"""Material Widgets - DockedDatePicker.

An inline calendar that always stays visible (not a dialog) and writes the
selected :class:`datetime.date` back to a shared observable.
"""

from __future__ import annotations

from datetime import date

from nuiitivet.material import App, DockedDatePicker
from nuiitivet.layout.container import Container
from nuiitivet.observable import Observable


def main(png_path: str = "") -> None:
    selected: Observable[date | None] = Observable(date(2026, 6, 25))
    content = Container(
        padding=24,
        child=DockedDatePicker(
            selected,
            on_change=lambda value: print(f"Selected: {value}"),
        ),
    )
    app = App(
        content=content,
        title="DockedDatePicker",
        width=460,
        height=560,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
