"""Material Widgets - Image rendered with four fit modes."""

from __future__ import annotations

import struct
import zlib

import nuiitivet.material as nv


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    length = struct.pack(">I", len(payload))
    crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
    return length + chunk_type + payload + struct.pack(">I", crc)


def _make_demo_png_bytes(width: int = 200, height: int = 200) -> bytes:
    """Create a small RGB PNG for the Image demo."""
    raw = bytearray()
    cx = width // 2
    cy = height // 2
    for y in range(height):
        raw.append(0)
        for x in range(width):
            r = int(220 * x / max(1, width - 1))
            g = int(220 * y / max(1, height - 1))
            b = 120
            if ((x // 16) + (y // 16)) % 2 == 0:
                r = min(255, r + 20)
                g = min(255, g + 20)
                b = min(255, b + 20)
            if x < 3 or x >= width - 3 or y < 3 or y >= height - 3:
                r, g, b = 255, 40, 40
            if abs(x - cx) <= 2 or abs(y - cy) <= 2:
                r, g, b = 30, 30, 30
            raw.extend((r, g, b))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw), level=9)
    signature = b"\x89PNG\r\n\x1a\n"
    return signature + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", idat) + _png_chunk(b"IEND", b"")


def _fit_card(label: str, fit: str, source: bytes) -> nv.Container:
    return nv.Container(
        padding=8,
        child=nv.Column(
            gap=4,
            children=[
                nv.Text(label),
                nv.Container(
                    width=180,
                    height=120,
                    child=nv.Image(source, fit=fit, width="100%", height="100%"),  # type: ignore[arg-type]
                ),
            ],
        ),
    )


def main(png_path: str = "") -> None:
    source = _make_demo_png_bytes()
    content = nv.Container(
        padding=16,
        child=nv.Column(
            gap=12,
            children=[
                nv.Row(
                    gap=8,
                    children=[
                        _fit_card("fit=contain", "contain", source),
                        _fit_card("fit=cover", "cover", source),
                    ],
                ),
                nv.Row(
                    gap=8,
                    children=[
                        _fit_card("fit=fill", "fill", source),
                        _fit_card("fit=none", "none", source),
                    ],
                ),
            ],
        ),
    )
    app = nv.App(
        content=content,
        title="Image",
        width=420,
        height=340,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
