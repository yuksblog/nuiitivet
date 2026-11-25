"""Material Widgets - Image showing a photo decoded on a thread, so the window never pauses."""

from __future__ import annotations

import asyncio
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageOps

import nuiitivet.material as nv


def load(path: Path) -> nv.Raster:  # on a thread
    picture = ImageOps.exif_transpose(PILImage.open(path)).convert("RGBA")
    return nv.Raster.rgba(picture.tobytes(), picture.width, picture.height)


def build_root() -> nv.Widget:
    photo: nv.State[nv.Raster | None] = nv.State(None)

    async def open_photo() -> None:
        path = await nv.FileDialog.open_file(title="Open a photo", file_types=["jpg", "jpeg", "png"])
        if path is not None:
            photo.value = await asyncio.to_thread(load, path)

    return nv.Container(
        padding=16,
        child=nv.Column(
            gap=12,
            children=[
                nv.Button("Open photo…", on_click=open_photo, key="open"),
                nv.Image(photo, width=260, height=200, key="photo"),
            ],
        ),
    )


def main(png_path: str = "") -> None:
    app = nv.App(nv.Window(content=build_root, title="Open a photo", width=320, height=300))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
