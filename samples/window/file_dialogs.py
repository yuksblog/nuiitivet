"""FileDialog: native open / save / choose-directory dialogs

Demonstrates:
- Awaiting nv.FileDialog from an async event handler
- Cancel (None) distinguished from a selection (Path)
- The tick counter visualizes the UI thread: it counts while the app idles
  and pauses while a modal dialog owns the thread
"""

import threading
import time

import nuiitivet.material as nv


class FileDialogApp(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.result: nv.Observable[str] = nv.Observable("(nothing picked yet)")
        # UI-thread heartbeat, driven from a worker thread (the write is
        # marshalled onto the UI thread, so the label stalls exactly when the
        # UI thread is busy — e.g. while a modal dialog is up).
        self.tick: nv.Observable[int] = nv.Observable(0)
        self._ticking = True
        threading.Thread(target=self._beat, daemon=True).start()

    def _beat(self) -> None:
        while self._ticking:
            time.sleep(0.5)
            self.tick.value += 1

    def _stop_ticker(self) -> None:
        self._ticking = False

    def build(self) -> nv.Widget:
        return nv.Column(
            padding=24,
            gap=12,
            children=[
                nv.Text(self.tick.map(lambda n: f"UI alive: {n}")),
                nv.Text(self.result, max_lines=3),
                nv.Row(
                    gap=8,
                    children=[
                        nv.Button("Open…", on_click=self._open),
                        nv.Button("Open many…", on_click=self._open_many),
                        nv.Button("Save…", on_click=self._save),
                        nv.Button("Folder…", on_click=self._folder),
                    ],
                ),
            ],
        ).modifier(nv.on_unmount(self._stop_ticker))

    async def _open(self) -> None:
        path = await nv.FileDialog.open_file(
            title="Pick an image", file_types=["png", "jpg", "gif"]
        )
        self.result.value = "cancelled" if path is None else f"open: {path}"

    async def _open_many(self) -> None:
        paths = await nv.FileDialog.open_files(title="Pick files")
        self.result.value = (
            "cancelled" if not paths else f"open {len(paths)}: " + ", ".join(p.name for p in paths)
        )

    async def _save(self) -> None:
        path = await nv.FileDialog.save_file(default_name="untitled.txt")
        self.result.value = "cancelled" if path is None else f"save: {path}"

    async def _folder(self) -> None:
        path = await nv.FileDialog.open_directory(title="Pick a folder")
        self.result.value = "cancelled" if path is None else f"folder: {path}"


def main() -> None:
    nv.App(nv.Window(content=FileDialogApp, title="File dialogs")).run()


if __name__ == "__main__":
    main()
