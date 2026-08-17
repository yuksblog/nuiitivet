"""Material Widgets - deriving a typed value from a text field.

``DockedDatePicker`` binds the field's *text*. The date, the error state and the
supporting text are all derived from that one observable, so nothing has to be
kept in sync and each has exactly one writer.

The two spellings of the derivation mean different things, and both are here:

- ``arrival`` uses ``map``, which reports ``None`` while the text is not a date.
  That is what drives the error state.
- ``chart_date`` uses ``filter().map()``, which holds the last valid date. That
  is what you want behind something that should not flinch at a keystroke.
"""

from __future__ import annotations

from datetime import date

import nuiitivet.material as nv

# Dates the room is already taken. A parseable date can still be unacceptable,
# which is exactly why the application, not the widget, decides what is an error.
BOOKED = {date(2026, 7, 4), date(2026, 7, 5)}


def _error(text: str) -> str | None:
    """What is wrong with this text, if anything -- the whole decision, once.

    Parse failures and business rules are branches of one expression, so they
    cannot disagree about whether the field is in error.
    """
    if not text:
        return None
    parsed = nv.parse_date(text)
    if parsed is None:
        return "Invalid date"
    if parsed in BOOKED:
        return "Already booked"
    return None


class Booking(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        # The observable the field writes into. Everything below derives from it.
        self.arrival_text = nv.Observable("")

        self.arrival = self.arrival_text.map(nv.parse_date)
        # One decision, two presentations of it. Deriving both from this rather
        # than from the text twice is what keeps them from disagreeing.
        self.arrival_error = self.arrival_text.map(_error)
        # Holds the last date that parsed, so it does not go blank while the
        # user is halfway through typing the next one.
        self.chart_date = self.arrival_text.filter(nv.is_date, initial="").map(nv.parse_date)

    def build(self) -> nv.Widget:
        return nv.Container(
            padding=24,
            child=nv.Column(
                gap=16,
                cross_alignment="start",
                children=[
                    nv.DockedDatePicker(
                        value=self.arrival_text,
                        label="Arrival",
                        supporting_text=self.arrival_error,
                        is_error=self.arrival_error.map(lambda e: e is not None),
                        # The calendar cannot offer a date outside these; typed
                        # text can, and _error is what polices that.
                        min_date=date(2026, 1, 1),
                        max_date=date(2026, 12, 31),
                    ),
                    nv.Text(self.arrival.map(lambda d: f"arrival:    {d}")),
                    nv.Text(self.chart_date.map(lambda d: f"last valid: {d}")),
                ],
            ),
        )


def main(png_path: str = "") -> None:
    app = nv.App(
        content=Booking(),
        title="Derived date value",
        width=460,
        height=600,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
