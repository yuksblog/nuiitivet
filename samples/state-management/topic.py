"""Events with Topic

Demonstrates:
- Logic on a worker thread publishing an event with nv.Topic
- A screen showing a snackbar for every event
"""

import threading
import time

import nuiitivet.material as nv


class CsvImporter:
    """Imports CSV files on a worker thread and publishes each finished file."""

    finished = nv.Topic[str]()

    def start(self, paths: list[str]) -> None:
        threading.Thread(target=self._run, args=(paths,), daemon=True).start()

    def _run(self, paths: list[str]) -> None:
        for path in paths:
            time.sleep(0.5)  # stand-in for importing one file
            self.finished.publish(path)  # on the worker thread


class ImportScreen(nv.ComposableWidget):
    """Starts an import and shows a snackbar for every file the importer finishes."""

    def __init__(self, importer: CsvImporter) -> None:
        super().__init__()
        self._importer = importer

    def on_mount(self) -> None:
        super().on_mount()
        self.bind(self._importer.finished.subscribe(self.show_finished))

    def show_finished(self, path: str) -> None:
        nv.Overlay.of(self).snackbar(f"Imported {path}")

    def _import(self) -> None:
        self._importer.start(["contacts.csv", "orders.csv", "products.csv"])

    def build(self) -> nv.Widget:
        return nv.Column(
            padding=24,
            children=[nv.Button("Import", on_click=self._import, style=nv.ButtonStyle.filled())],
        )


importer = CsvImporter()


def build_root() -> nv.Widget:
    return ImportScreen(importer)


def main() -> None:
    nv.App(nv.Window(content=build_root, width=360, height=480, title="Events with Topic")).run()


if __name__ == "__main__":
    main()
