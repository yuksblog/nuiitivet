"""A one-month calendar: click a day, type a title, and the event lands on it.

The sample app the README's "Building with an AI" GIFs are recorded on.
"""

import calendar
import datetime

import nuiitivet.material as nv

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


class AddEventDialog(nv.ComposableWidget):
    """Ask for an event title; closes with the typed title, or None on cancel."""

    def __init__(self, overlay: nv.Overlay, date: datetime.date) -> None:
        super().__init__()
        self.overlay = overlay
        self.date = date
        self.title = nv.Observable("")

    def build(self) -> nv.Widget:
        return nv.Card(
            width=260,
            child=nv.Column(
                padding=18,
                gap=12,
                children=[
                    nv.Text(
                        self.date.strftime("Add event — %b %d"),
                        type_scale=nv.TypeScale.TITLE_MEDIUM,
                    ),
                    nv.TextField(
                        value=self.title,
                        label="Event",
                        width="wt",
                        on_submit=lambda _: self._add(),
                    ),
                    nv.Row(
                        gap=8,
                        main_alignment="end",
                        children=[
                            nv.Button(
                                "Cancel", on_click=lambda: self.overlay.close(None), style=nv.ButtonStyle.outlined()
                            ),
                            nv.Button("Add", on_click=self._add),
                        ],
                    ),
                ],
            ),
        )

    def _add(self) -> None:
        self.overlay.close(self.title.value.strip() or None)


class CalendarApp(nv.ComposableWidget):
    """The current month as a grid; each day cell collects typed-in events."""

    def __init__(self) -> None:
        super().__init__()
        self.today = datetime.date.today()
        self.events: nv.Observable[dict[int, list[str]]] = nv.Observable({})

    def build(self) -> nv.Widget:
        return nv.Column(
            padding=18,
            gap=9,
            children=[
                self._build_header(),
                self._build_weekday_row(),
                self._build_grid(),
            ],
        )

    def _build_header(self) -> nv.Widget:
        total = self.events.map(lambda events: sum(len(titles) for titles in events.values()))
        return nv.Row(
            width="wt",
            padding=(0, 0, 0, 9),
            cross_alignment="center",
            main_alignment="space-between",
            children=[
                nv.Text(self.today.strftime("%B %Y"), type_scale=nv.TypeScale.TITLE_LARGE),
                nv.Text(
                    total.map(lambda count: f"{count} events"),
                    padding=(9, 4),
                    type_scale=nv.TypeScale.LABEL_MEDIUM,
                    style=nv.TextStyle(color=nv.ColorRole.ON_PRIMARY_CONTAINER),
                ).modifier(nv.background(nv.ColorRole.PRIMARY_CONTAINER) | nv.corner_radius(11)),
            ],
        )

    def _build_weekday_row(self) -> nv.Widget:
        return nv.UniformFlow(
            columns=7,
            cross_gap=6,
            children=[nv.Text(name, alignment="center", type_scale=nv.TypeScale.LABEL_SMALL) for name in WEEKDAYS],
        )

    def _build_grid(self) -> nv.Widget:
        first_weekday, day_count = calendar.monthrange(self.today.year, self.today.month)
        cells: list[nv.Widget] = [nv.Container() for _ in range(first_weekday)]
        cells += [self._build_day_cell(day) for day in range(1, day_count + 1)]
        return nv.UniformFlow(columns=7, main_gap=6, cross_gap=6, children=cells)

    def _build_day_cell(self, day: int) -> nv.Widget:
        is_today = day == self.today.day
        number: nv.Widget = nv.Text(
            str(day),
            width=20,
            height=20,
            alignment="center",
            type_scale=nv.TypeScale.LABEL_MEDIUM,
            style=nv.TextStyle(color=nv.ColorRole.ON_PRIMARY) if is_today else None,
        )
        if is_today:
            number = number.modifier(nv.background(nv.ColorRole.PRIMARY) | nv.corner_radius(10))
        chips = nv.Column.builder(
            self.events.map(lambda events: events.get(day, [])),
            lambda title, _index: nv.Text(
                title,
                padding=(4, 1),
                width="wt",
                max_lines=1,
                overflow="ellipsis",
                type_scale=nv.TypeScale.LABEL_SMALL,
                style=nv.TextStyle(color=nv.ColorRole.ON_TERTIARY_CONTAINER),
            ).modifier(nv.background(nv.ColorRole.TERTIARY_CONTAINER) | nv.corner_radius(3)),
            gap=2,
            width="wt",
        )
        return nv.Column(
            padding=4,
            gap=3,
            width="wt",
            height=72,
            children=[number, chips],
        ).modifier(
            nv.background(nv.ColorRole.SURFACE_CONTAINER)
            | nv.corner_radius(6)
            | nv.clickable(lambda: self._open_add_dialog(day))
        )

    async def _open_add_dialog(self, day: int) -> None:
        overlay = nv.Overlay.of(self)
        date = datetime.date(self.today.year, self.today.month, day)
        result = await overlay.dialog(AddEventDialog(overlay, date))
        if result.value:
            self._add_event(day, result.value)

    def _add_event(self, day: int, title: str) -> None:
        events = dict(self.events.value)
        events[day] = [*events.get(day, []), title]
        self.events.value = events


def build_root() -> nv.Widget:
    return CalendarApp()


def main() -> None:
    nv.App(nv.Window(content=build_root, title="Calendar", width=570, height="auto")).run()


if __name__ == "__main__":
    main()
