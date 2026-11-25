"""Material Widgets - Image showing frames from a camera, each one a Raster."""

from __future__ import annotations

import threading
import time
from typing import Callable

import numpy as np

import nuiitivet.material as nv

FrameHandler = Callable[[np.ndarray], None]


class Camera:
    """Stand-in for a camera library: hands RGBA frames to a function, on its own thread."""

    def __init__(self, on_frame: FrameHandler, width: int = 1280, height: int = 720) -> None:
        self._on_frame = on_frame
        self._size = (width, height)
        self._stop = threading.Event()

    def start(self) -> None:
        # Each run gets its own event, so a run stopped a moment ago cannot be restarted by this one.
        self._stop = threading.Event()
        threading.Thread(target=self._run, args=(self._stop,), name="Camera", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self, stopped: threading.Event) -> None:
        width, height = self._size
        ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
        rgba = np.empty((height, width, 4), dtype=np.uint8)
        rgba[..., 3] = 255
        started = time.perf_counter()
        while not stopped.is_set():
            t = time.perf_counter() - started
            rgba[..., 0] = (127 + 127 * np.sin(xs / 90.0 + t * 2.0)).astype(np.uint8)
            rgba[..., 1] = (127 + 127 * np.sin(ys / 70.0 - t * 1.5)).astype(np.uint8)
            rgba[..., 2] = (127 + 127 * np.sin((xs + ys) / 160.0 + t)).astype(np.uint8)
            self._on_frame(rgba)
            time.sleep(1 / 30)


def build_root() -> nv.Widget:
    frame: nv.State[nv.Raster | None] = nv.State(None)

    def on_camera_frame(rgba: np.ndarray) -> None:  # on the camera's thread
        height, width = rgba.shape[:2]
        frame.value = nv.Raster.rgba(rgba, width, height)

    camera = Camera(on_camera_frame)
    preview = nv.Image(frame, fit="cover", width="wt", height="wt", key="preview")
    return nv.Container(padding=16, child=preview).modifier(nv.on_mount(camera.start) | nv.on_unmount(camera.stop))


def main(png_path: str = "") -> None:
    app = nv.App(nv.Window(content=build_root, title="Camera preview", width=480, height=300))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
