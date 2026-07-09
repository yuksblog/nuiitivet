"""Material Widgets - DockedDatePicker.

A text field with a trailing calendar icon button. Tapping the icon opens a
:class:`DatePicker` in a dropdown anchored below the field; the date can also be
typed directly. Both routes write back to the same shared observable.
"""

from __future__ import annotations

from datetime import date

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    selected: nv.Observable[date | None] = nv.Observable(date(2026, 6, 25))

    if png_path:
        # For screenshot: place the dropdown calendar directly in the layout,
        # since render_to_png does not capture overlay content.
        style = nv.DockedDatePickerStyle()
        content = nv.Column(
            children=[
                nv.DockedDatePicker(value=selected),
                nv.DatePicker(selected, style=style.calendar),
            ],
            gap=int(style.dropdown_gap),
            padding=24,
        )
        app = nv.App(content=content, title="DockedDatePicker", width=460, height=600)
        app.render_to_png(png_path)
        return

    content = nv.Container(
        padding=24,
        child=nv.DockedDatePicker(
            value=selected,
            on_change=lambda value: print(f"Selected: {value}"),
        ),
    )
    # Tall enough for the anchored dropdown: the calendar hangs ~460dp below the
    # field, and the overlay is clipped to the window.
    app = nv.App(
        content=content,
        title="DockedDatePicker",
        width=460,
        height=600,
    )
    app.run()


if __name__ == "__main__":
    main()
