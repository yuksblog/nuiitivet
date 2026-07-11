"""Raw pointer handling with ``pointer_input()``: a tiny paint canvas.

The framework ships no canvas widget on purpose — you produce the bitmap
yourself (here with Pillow) and display it through :class:`Image`. ``pointer_input``
surfaces the raw press/move/release stream with widget-local coordinates so the
strokes land where the pointer is.

Interactions:
    - Drag with the left button to draw.
    - Hold Ctrl and click to pick the color under the pointer instead of drawing.
    - ``capture=True`` keeps the stroke going even if the pointer runs off the
      image edge.
"""

from __future__ import annotations

import io

from PIL import Image as PILImage, ImageDraw

import nuiitivet.material as nv

BUTTON_LEFT = nv.BUTTON_LEFT
MOD_CTRL = nv.MOD_CTRL

_CANVAS_W = 320
_CANVAS_H = 240


class PaintDemo(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self._bitmap = PILImage.new("RGB", (_CANVAS_W, _CANVAS_H), "#FFFFFF")
        self._draw = ImageDraw.Draw(self._bitmap)
        self._brush = "#1565C0"
        self._last_point: tuple[float, float] | None = None
        self.png = nv.Observable(self._encode())
        self.status = nv.Observable("Drag to draw · Ctrl+click to pick a color")

    def _encode(self) -> bytes:
        buf = io.BytesIO()
        self._bitmap.save(buf, format="PNG")
        return buf.getvalue()

    def _publish(self) -> None:
        self.png.value = self._encode()

    def _clamp(self, e: nv.PointerEvent) -> tuple[int, int]:
        # The Image is shown 1:1 here (fixed size == source size), so local
        # coordinates map straight to source pixels. Clamp to stay in bounds.
        x = int(min(max(e.local_x, 0), _CANVAS_W - 1))
        y = int(min(max(e.local_y, 0), _CANVAS_H - 1))
        return x, y

    def _on_press(self, e: nv.PointerEvent) -> None:
        x, y = self._clamp(e)
        if e.modifier_keys & MOD_CTRL:
            px = self._bitmap.getpixel((x, y))
            if isinstance(px, tuple):
                r, g, b = int(px[0]), int(px[1]), int(px[2])
                self._brush = "#%02X%02X%02X" % (r, g, b)
                self.status.value = f"Picked {self._brush}"
            self._last_point = None
            return
        self._draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=self._brush)
        self._last_point = (x, y)
        self._publish()

    def _on_move(self, e: nv.PointerEvent) -> None:
        # Only extend the stroke while the left button is held down.
        if not (e.buttons & BUTTON_LEFT):
            return
        x, y = self._clamp(e)
        if self._last_point is not None:
            self._draw.line((self._last_point[0], self._last_point[1], x, y), fill=self._brush, width=5)
        self._last_point = (x, y)
        self._publish()

    def _on_release(self, e: nv.PointerEvent) -> None:
        self._last_point = None

    def build(self):
        canvas = nv.Image(
            self.png,
            fit="fill",
            width=_CANVAS_W,
            height=_CANVAS_H,
        ).modifier(
            nv.corner_radius(8)
            | nv.pointer_input(
                on_press=self._on_press,
                on_move=self._on_move,
                on_release=self._on_release,
                buttons=(BUTTON_LEFT,),
                capture=True,
            )
        )

        return nv.Column(
            children=[
                nv.Text(self.status),
                canvas,
            ],
            gap=12,
            padding=16,
        )


def main(png: str = ""):
    app = nv.App(content=PaintDemo(), title="pointer_input — paint canvas")
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
