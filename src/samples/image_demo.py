from __future__ import annotations

import struct
import zlib
from typing import Callable

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.material import FilledButton, MaterialApp, OutlinedButton, Text
from nuiitivet.observable import Observable
from nuiitivet.rendering.fit import Fit
from nuiitivet.widgets import Image


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    length = struct.pack(">I", len(payload))
    crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
    return length + chunk_type + payload + struct.pack(">I", crc)


def _make_demo_png_bytes(width: int = 320, height: int = 120) -> bytes:
    """Create a small RGB PNG in memory for Image demo.

    Use a wide image with high-contrast markers so fit differences are obvious.
    """
    raw = bytearray()
    cx = width // 2
    cy = height // 2
    for y in range(height):
        raw.append(0)  # PNG filter type 0
        for x in range(width):
            # Base gradient
            r = int(220 * x / max(1, width - 1))
            g = int(220 * y / max(1, height - 1))
            b = 120

            # Add a checker overlay to visualize stretching.
            if ((x // 16) + (y // 16)) % 2 == 0:
                r = min(255, r + 20)
                g = min(255, g + 20)
                b = min(255, b + 20)

            # Draw strong border so cropping is easy to notice.
            if x < 3 or x >= width - 3 or y < 3 or y >= height - 3:
                r, g, b = 255, 40, 40

            # Draw center cross marker.
            if abs(x - cx) <= 2 or abs(y - cy) <= 2:
                r, g, b = 30, 30, 30

            raw.extend((r, g, b))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw), level=9)

    signature = b"\x89PNG\r\n\x1a\n"
    return signature + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", idat) + _png_chunk(b"IEND", b"")


def _fit_card(title: str, fit: Fit, source: Observable[bytes | None]) -> Container:
    return Container(
        child=Column(
            gap=8,
            children=[
                Text(title),
                Container(
                    width=200,
                    height=200,
                    padding=8,
                    alignment="center",
                    child=Image(source, fit=fit, width="100%", height="100%"),
                ),
            ],
        ),
        padding=8,
    )


def main() -> None:
    source: Observable[bytes | None] = Observable(None)
    demo_png = _make_demo_png_bytes()

    def _set_source(data: bytes | None) -> Callable[[], None]:
        def _apply() -> None:
            source.value = data

        return _apply

    controls = Row(
        gap=8,
        children=[
            FilledButton("Load Image", on_click=_set_source(demo_png)),
            OutlinedButton("Clear (None)", on_click=_set_source(None)),
        ],
    )

    root = Column(
        padding=16,
        gap=12,
        children=[
            Text("Image Demo (bytes | None | Observable)"),
            Text("Load image to compare fit modes. Clear sets source to None."),
            controls,
            Row(
                gap=12,
                children=[
                    _fit_card("fit=contain", "contain", source),
                    _fit_card("fit=cover", "cover", source),
                ],
            ),
            Row(
                gap=12,
                children=[
                    _fit_card("fit=fill", "fill", source),
                    _fit_card("fit=none", "none", source),
                ],
            ),
        ],
    )

    app = MaterialApp(root)
    app.run()


if __name__ == "__main__":
    main()
