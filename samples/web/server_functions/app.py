"""Call a server function from the screen: progress, cancel, and the errors.

Run on the desktop:   python app.py
Run in a browser:     python -m nuiitivet.web run app.py
"""

import asyncio

import nuiitivet.material as nv
from backend import scan  # on the web this import resolves to the stub


class ScanScreen(nv.ComposableWidget):
    query = nv.Observable("word1")
    status = nv.Observable("")
    progress = nv.Observable(0.0)
    matches: nv.Observable[list[str]] = nv.Observable([])

    def __init__(self) -> None:
        super().__init__()
        self._task: asyncio.Task | None = None

    def build(self) -> nv.Widget:
        return nv.Box(
            padding=24,
            child=nv.Column(
                gap=12,
                children=[
                    nv.TextField(value=self.query, label="Look for"),
                    nv.Row(
                        gap=12,
                        children=[
                            nv.Button("Scan", on_click=self.scan, style=nv.ButtonStyle.filled()),
                            nv.Button("Cancel", on_click=self.cancel, style=nv.ButtonStyle.outlined()),
                        ],
                    ),
                    nv.LinearProgressIndicator(value=self.progress),
                    nv.Text(self.status),
                    nv.Text(self.matches.map(lambda words: ", ".join(words[:20]))),
                ],
            ),
        )

    async def scan(self) -> None:
        self.status.value = "scanning"
        self._task = asyncio.ensure_future(scan(self.query.value, self.progress))  # await the call
        try:
            report = await self._task
            self.status.value = f"scanned {report.scanned} words, {len(report.matches)} match"
            self.matches.value = report.matches
        except asyncio.CancelledError:
            self.status.value = "cancelled"
        except ValueError as error:
            self.status.value = str(error)
        except nv.ServerError as error:
            self.status.value = str(error)  # "Rejected: not for you"
        self.progress.value = 0.0

    def cancel(self) -> None:
        if self._task is not None:
            self._task.cancel()


def main() -> None:
    nv.App(nv.Window(content=ScanScreen, title="Server functions", width=480, height=320)).run()


if __name__ == "__main__":
    main()
