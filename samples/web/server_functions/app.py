"""Call a server function from the screen: progress, cancel, the errors, and a screen that keeps answering.

Run on the desktop:   python app.py
Run in a browser:     python -m nuiitivet.web run app.py
"""

import asyncio

import nuiitivet.material as nv
from jobs import search


class SearchScreen(nv.ComposableWidget):
    query = nv.Observable("word1")
    status = nv.Observable("")
    progress = nv.Observable(0.0)
    clicks = nv.Observable(0)

    def __init__(self) -> None:
        super().__init__()
        self._task: asyncio.Task | None = None

    def build(self) -> nv.Widget:
        return nv.Box(
            padding=24,
            child=nv.Column(
                gap=12,
                children=[
                    nv.TextField(value=self.query, label="Look for", key="query"),
                    nv.Row(
                        gap=12,
                        children=[
                            nv.Button("Search", on_click=self.search, style=nv.ButtonStyle.filled(), key="search"),
                            nv.Button("Cancel", on_click=self.cancel, style=nv.ButtonStyle.outlined(), key="cancel"),
                        ],
                    ),
                    nv.LinearProgressIndicator(value=self.progress),
                    nv.Row(
                        gap=12,
                        children=[
                            nv.Text(self.progress.map(lambda p: f"{p:.0%}"), key="progress"),
                            nv.Text(self.status, key="status"),
                        ],
                    ),
                    nv.Row(
                        gap=12,
                        children=[
                            # The screen answers while the search runs: the work is not on the UI thread.
                            nv.Button("Click meanwhile", on_click=self.clicked, key="click"),
                            nv.Text(self.clicks.map(lambda n: f"{n} clicks"), key="clicks"),
                        ],
                    ),
                ],
            ),
        )

    async def search(self) -> None:
        self.status.value = "searching"
        self._task = asyncio.ensure_future(search(self.query.value, self.progress))  # await the call
        try:
            matches = await self._task
            self.status.value = f"{len(matches)} words within one edit of {self.query.value}"
        except asyncio.CancelledError:
            self.status.value = "cancelled"
        except ValueError as error:
            self.status.value = str(error)
        except nv.RemoteError as error:
            self.status.value = str(error)  # "Rejected: not for you"
        self.progress.value = 0.0

    def cancel(self) -> None:
        if self._task is not None:
            self._task.cancel()

    def clicked(self) -> None:
        self.clicks.value += 1


def main() -> None:
    nv.App(nv.Window(content=SearchScreen, title="Server functions", width=480, height=320)).run()


if __name__ == "__main__":
    main()
