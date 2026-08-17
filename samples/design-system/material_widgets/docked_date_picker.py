"""Material Widgets - DockedDatePicker.

A text field with a trailing calendar icon button. Tapping the icon opens a
:class:`DatePicker` in a dropdown anchored below the field; the date can also be
typed directly.

``value`` is the field's *text*, so typing and the calendar write to the same
observable. The date is derived from it -- see ``date_field_derived_value.py``
for what an application does with it, including reporting errors.
"""

from __future__ import annotations

from datetime import date

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    text = nv.Observable(nv.format_date(date(2026, 6, 25)))
    selected = text.map(nv.parse_date)

    if png_path:
        # For screenshot: place the dropdown calendar directly in the layout,
        # since render_to_png does not capture overlay content.
        style = nv.DockedDatePickerStyle()
        content = nv.Column(
            children=[
                nv.DockedDatePicker(value=text),
                nv.DatePicker(nv.Observable(selected.value), style=style.calendar),
            ],
            gap=int(style.dropdown_gap),
            padding=24,
        )
        app = nv.App(content=content, title="DockedDatePicker", width=460, height=600)
        app.render_to_png(png_path)
        return

    content = nv.Container(
        padding=24,
        child=nv.Column(
            gap=16,
            cross_alignment="start",
            children=[
                nv.DockedDatePicker(value=text),
                # The derived date, not the text: this is what the rest of an
                # application would work with.
                nv.Text(selected.map(lambda d: f"Selected: {d}")),
            ],
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
