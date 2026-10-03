"""A skia-python-shaped adapter over CanvasKit, for the Pyodide spike.

It covers what the benchmark scene calls and nothing else. Geometry and paint
state live in Python and cross to JS once per draw call. Every font resolves
to the one typeface ``run.mjs`` loaded.
"""

from __future__ import annotations

from typing import Any

import js
from pyodide.ffi import to_js

CK = js.CK
H = js.H

__version__ = "canvaskit-shim"


def ColorSetARGB(a: int, r: int, g: int, b: int) -> int:
    return ((a & 255) << 24) | ((r & 255) << 16) | ((g & 255) << 8) | (b & 255)


class Rect:
    __slots__ = ("fLeft", "fTop", "fRight", "fBottom")

    def __init__(self, *args: float) -> None:
        if len(args) == 4:
            self.fLeft, self.fTop, self.fRight, self.fBottom = (float(v) for v in args)
        elif len(args) == 2:
            self.fLeft, self.fTop, self.fRight, self.fBottom = 0.0, 0.0, float(args[0]), float(args[1])
        else:
            self.fLeft = self.fTop = self.fRight = self.fBottom = 0.0

    @staticmethod
    def MakeXYWH(x: float, y: float, w: float, h: float) -> "Rect":
        return Rect(x, y, x + w, y + h)

    @staticmethod
    def MakeWH(w: float, h: float) -> "Rect":
        return Rect(0.0, 0.0, w, h)

    @staticmethod
    def MakeLTRB(left: float, top: float, right: float, bottom: float) -> "Rect":
        return Rect(left, top, right, bottom)

    def setXYWH(self, x: float, y: float, w: float, h: float) -> None:
        self.fLeft, self.fTop, self.fRight, self.fBottom = float(x), float(y), float(x + w), float(y + h)

    def left(self) -> float:
        return self.fLeft

    def top(self) -> float:
        return self.fTop

    def right(self) -> float:
        return self.fRight

    def bottom(self) -> float:
        return self.fBottom

    def x(self) -> float:
        return self.fLeft

    def y(self) -> float:
        return self.fTop

    def width(self) -> float:
        return self.fRight - self.fLeft

    def height(self) -> float:
        return self.fBottom - self.fTop

    def isEmpty(self) -> bool:
        return self.fRight <= self.fLeft or self.fBottom <= self.fTop


class RRect:
    __slots__ = ("rc", "rx", "ry")

    def __init__(self) -> None:
        self.rc = Rect()
        self.rx = self.ry = 0.0

    @staticmethod
    def MakeRectXY(rect: Rect, rx: float, ry: float) -> "RRect":
        out = RRect()
        out.rc, out.rx, out.ry = rect, float(rx), float(ry)
        return out

    def setRectXY(self, rect: Rect, rx: float, ry: float) -> None:
        self.rc, self.rx, self.ry = rect, float(rx), float(ry)

    def rect(self) -> Rect:
        return self.rc


class Color4f:
    def __init__(self, r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 1.0) -> None:
        self.fR, self.fG, self.fB, self.fA = r, g, b, a


class Point:
    __slots__ = ("fX", "fY")

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.fX, self.fY = float(x), float(y)

    def x(self) -> float:
        return self.fX

    def y(self) -> float:
        return self.fY


class Paint:
    kFill_Style = 0
    kStroke_Style = 1
    kButt_Cap = 0
    kRound_Cap = 1
    kSquare_Cap = 2

    __slots__ = ("_p", "_dirty", "color", "aa", "style", "stroke_width", "cap")

    def __init__(self, **kwargs: Any) -> None:
        self._p = None
        self._dirty = True
        self.color = 0xFF000000
        self.aa = False
        self.style = 0
        self.stroke_width = 0.0
        self.cap = 0
        for key, value in kwargs.items():
            getattr(self, "set" + key)(value)

    def setAntiAlias(self, aa: bool) -> None:
        self.aa = bool(aa)
        self._dirty = True

    def setStyle(self, style: int) -> None:
        self.style = int(style)
        self._dirty = True

    def setStrokeWidth(self, width: float) -> None:
        self.stroke_width = float(width)
        self._dirty = True

    def setStrokeCap(self, cap: int) -> None:
        self.cap = int(cap)
        self._dirty = True

    def setColor(self, color: int) -> None:
        self.color = int(color) & 0xFFFFFFFF
        self._dirty = True

    def getColor(self) -> int:
        return self.color

    def setAlphaf(self, alpha: float) -> None:
        a = max(0, min(255, int(round(alpha * 255))))
        self.color = (self.color & 0x00FFFFFF) | (a << 24)
        self._dirty = True

    def setAlpha(self, alpha: int) -> None:
        self.color = (self.color & 0x00FFFFFF) | ((int(alpha) & 255) << 24)
        self._dirty = True

    def js(self) -> Any:
        """The CanvasKit paint, synced in one crossing when state changed."""
        if self._dirty:
            self._p = H.paint(self._p, self.color, self.aa, self.style, self.stroke_width, self.cap)
            self._dirty = False
        return self._p

    def __del__(self) -> None:
        if self._p is not None:
            H.release(self._p)


class FontStyle:
    kNormal_Width = 5
    kUpright_Slant = 0

    def __init__(self, weight: int = 400, width: int = 5, slant: int = 0) -> None:
        self._weight = weight

    def weight(self) -> int:
        return self._weight


class Typeface:
    def __init__(self, handle: Any) -> None:
        self._t = handle

    @staticmethod
    def MakeFromName(family: Any, style: Any = None) -> "Typeface":
        return _default_typeface()

    @staticmethod
    def MakeFromFile(path: str, index: int = 0) -> "Typeface":
        return _default_typeface()

    @staticmethod
    def MakeDefault() -> "Typeface":
        return _default_typeface()


_TYPEFACE: Typeface | None = None


def _default_typeface() -> Typeface:
    global _TYPEFACE
    if _TYPEFACE is None:
        _TYPEFACE = Typeface(CK.Typeface.MakeTypefaceFromData(js.FONT_DATA))
    return _TYPEFACE


class FontMgr:
    @staticmethod
    def RefDefault() -> "FontMgr":
        return FontMgr()

    def matchFamilyStyle(self, family: Any, style: Any) -> Typeface:
        return _default_typeface()

    def countFamilies(self) -> int:
        return 0


class Font:
    def __init__(self, typeface: Typeface | None = None, size: float = 12.0) -> None:
        tf = typeface if isinstance(typeface, Typeface) else _default_typeface()
        self._f = CK.Font.new(tf._t, float(size))
        self._size = float(size)

    def getSize(self) -> float:
        return self._size

    def measureText(self, text: str) -> float:
        return float(H.measure(self._f, text))

    def textToGlyphs(self, text: str) -> list[int]:
        return self._f.getGlyphIDs(text).to_py().tolist()

    def getWidths(self, glyphs: list[int]) -> list[float]:
        return self._f.getGlyphWidths(to_js(glyphs)).to_py().tolist()

    def getWidthsBounds(self, glyphs: list[int]) -> tuple[list[float], list[Rect]]:
        arr = to_js(glyphs)
        widths = self._f.getGlyphWidths(arr).to_py().tolist()
        flat = self._f.getGlyphBounds(arr).to_py().tolist()
        bounds = [Rect(*flat[i : i + 4]) for i in range(0, len(flat), 4)]
        return widths, bounds


class TextBlob:
    def __init__(self, handle: Any) -> None:
        self._b = handle

    @staticmethod
    def MakeFromString(text: str, font: Font) -> "TextBlob":
        return TextBlob(CK.TextBlob.MakeFromText(text, font._f))

    @staticmethod
    def MakeFromPosTextH(text: str, xpos: list[float], y: float, font: Font) -> "TextBlob":
        return TextBlob(H.posBlob(text, to_js(xpos), float(y), font._f))

    def __del__(self) -> None:
        H.release(self._b)


class Image:
    def __init__(self, handle: Any) -> None:
        self._i = handle
        self._w = int(handle.width())
        self._h = int(handle.height())

    def width(self) -> int:
        return self._w

    def height(self) -> int:
        return self._h

    def __del__(self) -> None:
        H.release(self._i)


class Matrix:
    __slots__ = ("sx", "sy")

    def __init__(self, sx: float = 1.0, sy: float = 1.0) -> None:
        self.sx, self.sy = sx, sy

    def getScaleX(self) -> float:
        return self.sx

    def getScaleY(self) -> float:
        return self.sy


class Canvas:
    """Forwards draws to CanvasKit; tracks translate, scale and clip in Python."""

    def __init__(self, handle: Any, width: float, height: float) -> None:
        self._c = handle
        self._tx = self._ty = 0.0
        self._sx = self._sy = 1.0
        self._clip = (0.0, 0.0, float(width), float(height))
        self._stack: list[tuple[float, float, float, float, tuple[float, float, float, float]]] = []

    def save(self) -> int:
        self._stack.append((self._tx, self._ty, self._sx, self._sy, self._clip))
        self._c.save()
        return len(self._stack)

    def restore(self) -> None:
        if self._stack:
            self._tx, self._ty, self._sx, self._sy, self._clip = self._stack.pop()
        self._c.restore()

    def translate(self, dx: float, dy: float) -> None:
        l, t, r, b = self._clip
        self._clip = (l - dx, t - dy, r - dx, b - dy)
        self._tx += dx * self._sx
        self._ty += dy * self._sy
        self._c.translate(dx, dy)

    def scale(self, sx: float, sy: float) -> None:
        l, t, r, b = self._clip
        self._clip = (l / sx, t / sy, r / sx, b / sy)
        self._sx *= sx
        self._sy *= sy
        self._c.scale(sx, sy)

    def clipRect(self, rect: Rect, *args: Any, **kwargs: Any) -> None:
        l, t, r, b = self._clip
        self._clip = (max(l, rect.fLeft), max(t, rect.fTop), min(r, rect.fRight), min(b, rect.fBottom))
        H.clipRect(self._c, rect.fLeft, rect.fTop, rect.fRight, rect.fBottom)

    def getLocalClipBounds(self) -> Rect:
        return Rect(*self._clip)

    def getTotalMatrix(self) -> Matrix:
        return Matrix(self._sx, self._sy)

    def clear(self, color: Any) -> None:
        if isinstance(color, Color4f):
            H.clear(self._c, color.fA, color.fR, color.fG, color.fB)
        else:
            argb = int(color)
            H.clear(
                self._c,
                (argb >> 24 & 255) / 255,
                (argb >> 16 & 255) / 255,
                (argb >> 8 & 255) / 255,
                (argb & 255) / 255,
            )

    def drawRRect(self, rrect: RRect, paint: Paint) -> None:
        rc = rrect.rc
        H.drawRRect(self._c, rc.fLeft, rc.fTop, rc.fRight, rc.fBottom, rrect.rx, rrect.ry, paint.js())

    def drawRect(self, rect: Rect, paint: Paint) -> None:
        self._c.drawRect4f(rect.fLeft, rect.fTop, rect.fRight, rect.fBottom, paint.js())

    def drawOval(self, rect: Rect, paint: Paint) -> None:
        H.drawOval(self._c, rect.fLeft, rect.fTop, rect.fRight, rect.fBottom, paint.js())

    def drawLine(self, *args: Any) -> None:
        if len(args) == 5:
            x0, y0, x1, y1, paint = args
        else:
            p0, p1, paint = args
            x0, y0, x1, y1 = p0.fX, p0.fY, p1.fX, p1.fY
        self._c.drawLine(x0, y0, x1, y1, paint.js())

    def drawTextBlob(self, blob: TextBlob, x: float, y: float, paint: Paint) -> None:
        self._c.drawTextBlob(blob._b, x, y, paint.js())

    def drawImage(self, image: Image, x: float, y: float, *args: Any) -> None:
        self._c.drawImage(image._i, x, y, None)


class Surface:
    def __init__(self, width: int, height: int) -> None:
        self._w, self._h = int(width), int(height)
        self._s = CK.MakeSurface(self._w, self._h)
        self._canvas = Canvas(self._s.getCanvas(), self._w, self._h)

    def getCanvas(self) -> Canvas:
        return self._canvas

    def width(self) -> int:
        return self._w

    def height(self) -> int:
        return self._h

    def makeImageSnapshot(self) -> Image:
        return Image(self._s.makeImageSnapshot())


class PictureRecorder:
    def __init__(self) -> None:
        self._r = CK.PictureRecorder.new()

    def beginRecording(self, bounds: Rect) -> Canvas:
        handle = self._r.beginRecording(CK.LTRBRect(bounds.fLeft, bounds.fTop, bounds.fRight, bounds.fBottom))
        return Canvas(handle, bounds.width(), bounds.height())

    def finishRecordingAsPicture(self) -> Any:
        return self._r.finishRecordingAsPicture()
