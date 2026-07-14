import asyncio
import random

import nuiitivet.material as nv


class EventLog:
    """Screen-level log, so unmount events stay visible after the widget is gone."""

    def __init__(self) -> None:
        self.text = nv.Observable("(no events yet)")
        self._lines: list[str] = []

    def add(self, line: str) -> None:
        self._lines.append(line)
        self.text.value = "\n".join(self._lines[-6:])


LOG = EventLog()


class LiveScreen(nv.ComposableWidget):
    """Polls a sensor for as long as the polled Column is in the tree."""

    def __init__(self) -> None:
        super().__init__()
        self.reading = nv.Observable("--")

    async def _poll(self) -> None:
        # Started as a task on mount, cancelled automatically on unmount.
        LOG.add("poll started")
        try:
            while True:
                self.reading.value = f"{random.uniform(20.0, 25.0):.2f} °C"
                await asyncio.sleep(0.5)
        finally:
            LOG.add("poll cancelled")

    def _stopped(self) -> None:
        LOG.add("column unmounted")

    def build(self) -> nv.Widget:
        # Every rebuild produces a *new* Column, so the callbacks fire again:
        # press Rebuild and watch the log.
        return nv.Column(
            children=[
                nv.Text("Live reading (updates every 0.5s):"),
                nv.Text(self.reading),
                nv.Row(
                    children=[
                        nv.Button("Rebuild", on_click=self.rebuild, style=nv.ButtonStyle.text()),
                        nv.Button(
                            "Back",
                            on_click=lambda: nv.Navigator.root().pop(),
                            style=nv.ButtonStyle.text(),
                        ),
                    ],
                    gap=10,
                ),
                nv.Text(LOG.text),
            ],
            gap=14,
            cross_alignment="start",
            padding=24,
        ).modifier(nv.on_mount(self._poll) | nv.on_unmount(self._stopped))


class HomeScreen(nv.ComposableWidget):
    def build(self) -> nv.Widget:
        return nv.Column(
            children=[
                nv.Text("Open the live view, then rebuild it, then come back."),
                nv.Button(
                    "Open live view",
                    on_click=lambda: nv.Navigator.root().push(LiveScreen()),
                    style=nv.ButtonStyle.filled(),
                ),
                nv.Text(LOG.text),
            ],
            gap=14,
            cross_alignment="start",
            padding=24,
        )


def main(png: str = "") -> None:
    app = nv.App(content=HomeScreen(), title="on_mount() / on_unmount()", width=420, height=320)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
