"""Material Widgets - DatePicker.

An inline calendar that always stays visible (not a dialog) and writes the
selected :class:`datetime.date` back to a shared observable.
"""

from __future__ import annotations

from datetime import date

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    selected: nv.Observable[date | None] = nv.Observable(date(2026, 6, 25))
    content = nv.Container(
        padding=24,
        child=nv.DatePicker(
            selected,
            on_change=lambda value: print(f"Selected: {value}"),
        ),
    )
    app = nv.App(nv.Window(content=content, title="DatePicker", width=460, height=560))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
