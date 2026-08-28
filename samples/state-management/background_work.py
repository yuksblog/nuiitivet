"""Observable: Background Work

Demonstrates:
- A long job on a worker thread, reported through observables
- An indeterminate progress bar until the total is known, determinate after
- A live step display fed by the worker
- Cancellation from the UI thread with a per-run threading.Event
- A worker exception surfaced through an observable instead of vanishing
"""

import threading
import time

import nuiitivet.material as nv

_ROW_COUNT = 400


def read_csv(path: str) -> list[str]:
    """Stand-in for reading a real file; the delay is the I/O."""
    time.sleep(1.0)
    return [f"{path}#{index}" for index in range(_ROW_COUNT)]


def validate(row: str) -> str:
    """Stand-in for per-row validation."""
    time.sleep(0.005)
    return row


class CsvImportScreen(nv.ComposableWidget):
    """Imports one CSV file on a worker thread."""

    running: nv.Observable[bool] = nv.Observable(False)
    step: nv.Observable[str] = nv.Observable("")
    total_rows: nv.Observable[int] = nv.Observable(0)
    imported_rows: nv.Observable[int] = nv.Observable(0)
    error: nv.Observable[str | None] = nv.Observable(None)

    def __init__(self) -> None:
        super().__init__()
        # Derived from dispatched sources, so these are dispatched too.
        self.progress = nv.combine(self.imported_rows, self.total_rows).compute(
            lambda done, total: done / total if total else 0.0
        )
        self.counting = self.total_rows.map(lambda total: total == 0)
        self.error_text = self.error.map(lambda message: f"⚠ {message}" if message else "")
        self.count_text = nv.combine(self.imported_rows, self.total_rows).compute(
            lambda done, total: f"{done} / {total} rows" if total else ""
        )
        self._cancel = threading.Event()

    def start(self, path: str, *, should_fail: bool = False) -> None:
        """Kick off the import and return immediately."""
        # Supersede whatever is still running: a second Import must not leave
        # the previous worker alive writing into the same observables.
        self._cancel.set()
        cancel = self._cancel = threading.Event()

        self.error.value = None
        self.imported_rows.value = 0
        self.total_rows.value = 0
        self.step.value = ""
        self.running.value = True
        threading.Thread(target=self._run, args=(path, should_fail, cancel), daemon=True).start()

    def cancel(self) -> None:
        """Ask the worker to stop, and settle the screen now.

        Called on the UI thread, which owns the outcome of an interrupted run:
        the worker may be mid-row, and the screen should not wait for it.
        """
        self._cancel.set()
        self.step.value = "Cancelled"
        self.running.value = False

    def _run(self, path: str, should_fail: bool, cancel: threading.Event) -> None:
        # Everything below runs off the UI thread; every write is marshalled.
        # `cancel` belongs to *this* run, so a superseded worker never mistakes
        # a later run's flag for its own.
        try:
            self.step.value = "Reading"
            rows = read_csv(path)
            self.total_rows.value = len(rows)

            self.step.value = "Importing"
            for index, row in enumerate(rows, start=1):
                if cancel.is_set():
                    return  # Cancelled or superseded: this run writes nothing more.
                if should_fail and index == len(rows) // 3:
                    raise RuntimeError(f"malformed row: {row}")
                validate(row)
                self.imported_rows.value = index

            self.step.value = "Done"
        except Exception as exc:
            if cancel.is_set():
                return
            self.error.value = str(exc)
            self.step.value = "Failed"
        finally:
            if not cancel.is_set():
                self.running.value = False

    def build(self) -> nv.Widget:
        return nv.Box(
            padding=24,
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Observable: Background Work"),
                    nv.Text("A worker imports a CSV file; the screen stays responsive."),
                    nv.Text(self.step),
                    nv.Text(self.count_text),
                    # Hidden while idle; indeterminate until the row count is
                    # known, determinate after.
                    nv.Deck(
                        index=self.counting.map(lambda counting: 0 if counting else 1),
                        children=[
                            nv.IndeterminateLinearProgressIndicator(width=320),
                            nv.LinearProgressIndicator(value=self.progress, width=320),
                        ],
                    ).modifier(nv.visible(self.running)),
                    nv.Text(self.error_text),
                    nv.Row(
                        gap=12,
                        children=[
                            nv.Button(
                                "Import",
                                on_click=lambda: self.start("contacts.csv"),
                                style=nv.ButtonStyle.filled(),
                            ),
                            nv.Button(
                                "Import (fails)",
                                on_click=lambda: self.start("broken.csv", should_fail=True),
                                style=nv.ButtonStyle.outlined(),
                            ),
                            nv.Button(
                                "Cancel",
                                on_click=self.cancel,
                                style=nv.ButtonStyle.tonal(),
                            ),
                        ],
                    ),
                ],
            ),
        )


if __name__ == "__main__":
    widget = CsvImportScreen()
    app = nv.App(nv.Window(content=widget))
    try:
        app.run()
    except Exception:
        print("Background Work demo requires pyglet/skia to run.")
