"""A skia-python-shaped adapter over CanvasKit, for the browser backend.

The adapter owns the canvas matrix. CanvasKit has no ``setMatrix``, so a matrix
pushed to it could only be replaced by multiplying with an inverse, and that
leaves a matrix that is almost the identity at a device pixel ratio such as
1.5. The matrix therefore lives in Python. It reaches CanvasKit once per run of
draws, inside a save level the host pops before every save, restore and clip,
and clips are applied in device coordinates.

Geometry and paint state live in Python as well and cross to JS once per draw.
Every family name resolves to the one typeface the page loaded; a font file
loads as its own typeface.
"""

from __future__ import annotations

import math
from typing import Any, Optional, Sequence

import js
from pyodide.ffi import to_js

H = js.NV_HOST
CK = H.CK

__version__ = "canvaskit"

kPNG = "png"
kNormal_BlurStyle = 0
ColorTRANSPARENT = 0x00000000
ColorBLACK = 0xFF000000
ColorWHITE = 0xFFFFFFFF

_Radii = tuple[float, float, float, float, float, float, float, float]
_Bounds = tuple[float, float, float, float]
_NO_RADII: _Radii = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def ColorSetARGB(a: int, r: int, g: int, b: int) -> int:
    return ((a & 255) << 24) | ((r & 255) << 16) | ((g & 255) << 8) | (b & 255)


def Color(r: int, g: int, b: int, a: int = 255) -> int:
    return ColorSetARGB(a, r, g, b)


class Color4f:
    def __init__(self, r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 1.0) -> None:
        self.fR, self.fG, self.fB, self.fA = float(r), float(g), float(b), float(a)


def _argb(color: Any) -> int:
    if isinstance(color, Color4f):
        return ColorSetARGB(
            round(color.fA * 255),
            round(color.fR * 255),
            round(color.fG * 255),
            round(color.fB * 255),
        )
    return int(color) & 0xFFFFFFFF


class ClipOp:
    kDifference = 0
    kIntersect = 1


class FilterMode:
    kNearest = 0
    kLinear = 1


class SamplingOptions:
    def __init__(self, filter: int = FilterMode.kNearest, *args: Any) -> None:
        self.linear = filter == FilterMode.kLinear


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

    def makeOutset(self, dx: float, dy: float) -> "Rect":
        return Rect(self.fLeft - dx, self.fTop - dy, self.fRight + dx, self.fBottom + dy)

    def makeInset(self, dx: float, dy: float) -> "Rect":
        return Rect(self.fLeft + dx, self.fTop + dy, self.fRight - dx, self.fBottom - dy)

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


class Point:
    __slots__ = ("fX", "fY")

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.fX, self.fY = float(x), float(y)

    def x(self) -> float:
        return self.fX

    def y(self) -> float:
        return self.fY


def _radii8(radii: Sequence[Any]) -> _Radii:
    """Corner radii as x and y per corner, clockwise from the top left.

    Accepts the two shapes skia-python does: eight numbers, or one point or
    pair per corner.
    """
    flat: list[float] = []
    for item in radii:
        if isinstance(item, Point):
            flat += [item.fX, item.fY]
        elif isinstance(item, (tuple, list)):
            flat += [float(item[0]), float(item[1])]
        else:
            flat.append(float(item))
    if len(flat) != 8:
        raise ValueError("an RRect takes a radius pair for each of its four corners")
    return (flat[0], flat[1], flat[2], flat[3], flat[4], flat[5], flat[6], flat[7])


class RRect:
    __slots__ = ("rc", "radii")

    def __init__(self) -> None:
        self.rc = Rect()
        self.radii: _Radii = _NO_RADII

    @staticmethod
    def MakeRectXY(rect: Rect, rx: float, ry: float) -> "RRect":
        out = RRect()
        out.setRectXY(rect, rx, ry)
        return out

    @staticmethod
    def MakeOval(rect: Rect) -> "RRect":
        return RRect.MakeRectXY(rect, rect.width() / 2.0, rect.height() / 2.0)

    @staticmethod
    def MakeRectRadii(rect: Rect, radii: Sequence[Any]) -> "RRect":
        out = RRect()
        out.setRectRadii(rect, radii)
        return out

    def setRectXY(self, rect: Rect, rx: float, ry: float) -> None:
        rx, ry = float(rx), float(ry)
        self.rc, self.radii = rect, (rx, ry, rx, ry, rx, ry, rx, ry)

    def setRectRadii(self, rect: Rect, radii: Sequence[Any]) -> None:
        self.rc, self.radii = rect, _radii8(radii)

    def rect(self) -> Rect:
        return self.rc

    def _flat(self) -> tuple[float, ...]:
        rc = self.rc
        return (rc.fLeft, rc.fTop, rc.fRight, rc.fBottom) + self.radii


class MaskFilter:
    def __init__(self, handle: Any) -> None:
        self._h = handle

    @staticmethod
    def MakeBlur(style: int, sigma: float, respectCTM: bool = True) -> "MaskFilter":
        return MaskFilter(H.blur(float(sigma), bool(respectCTM)))

    def __del__(self) -> None:
        H.release(self._h)


class PathEffect:
    def __init__(self, handle: Any) -> None:
        self._h = handle

    def __del__(self) -> None:
        H.release(self._h)


class DashPathEffect:
    @staticmethod
    def Make(intervals: Sequence[float], phase: float = 0.0) -> PathEffect:
        return PathEffect(H.dash(to_js([float(v) for v in intervals]), float(phase)))


class Paint:
    kFill_Style = 0
    kStroke_Style = 1
    kButt_Cap = 0
    kRound_Cap = 1
    kSquare_Cap = 2

    __slots__ = ("_p", "_dirty", "color", "aa", "style", "stroke_width", "cap", "mask_filter", "path_effect")

    def __init__(self, **kwargs: Any) -> None:
        self._p = None
        self._dirty = True
        self.color = 0xFF000000
        self.aa = False
        self.style = 0
        self.stroke_width = 0.0
        self.cap = 0
        self.mask_filter: Optional[MaskFilter] = None
        self.path_effect: Optional[PathEffect] = None
        for key, value in kwargs.items():
            getattr(self, "set" + key)(value)

    def setAntiAlias(self, aa: bool) -> None:
        self.aa = bool(aa)
        self._dirty = True

    def isAntiAlias(self) -> bool:
        return self.aa

    def setStyle(self, style: int) -> None:
        self.style = int(style)
        self._dirty = True

    def getStyle(self) -> int:
        return self.style

    def setStrokeWidth(self, width: float) -> None:
        self.stroke_width = float(width)
        self._dirty = True

    def getStrokeWidth(self) -> float:
        return self.stroke_width

    def setStrokeCap(self, cap: int) -> None:
        self.cap = int(cap)
        self._dirty = True

    def setColor(self, color: Any) -> None:
        self.color = _argb(color)
        self._dirty = True

    def getColor(self) -> int:
        return self.color

    def setAlphaf(self, alpha: float) -> None:
        self.setAlpha(max(0, min(255, int(round(alpha * 255)))))

    def setAlpha(self, alpha: int) -> None:
        self.color = (self.color & 0x00FFFFFF) | ((int(alpha) & 255) << 24)
        self._dirty = True

    def getAlpha(self) -> int:
        return self.color >> 24

    def setMaskFilter(self, mask_filter: Optional[MaskFilter]) -> None:
        self.mask_filter = mask_filter
        self._dirty = True

    def setPathEffect(self, path_effect: Optional[PathEffect]) -> None:
        self.path_effect = path_effect
        self._dirty = True

    def js(self) -> Any:
        """The CanvasKit paint, synced in one crossing when state changed."""
        if self._dirty:
            self._p = H.paint(
                self._p,
                self.color,
                self.aa,
                self.style,
                self.stroke_width,
                self.cap,
                self.mask_filter._h if self.mask_filter is not None else None,
                self.path_effect._h if self.path_effect is not None else None,
            )
            self._dirty = False
        return self._p

    def __del__(self) -> None:
        if self._p is not None:
            H.release(self._p)


class Data:
    def __init__(self, data: bytes) -> None:
        self._bytes = bytes(data)

    @staticmethod
    def MakeFromBytes(data: bytes) -> "Data":
        return Data(data)

    @staticmethod
    def MakeWithCopy(data: bytes) -> "Data":
        return Data(data)

    @staticmethod
    def MakeFromFileName(path: str) -> "Data":
        with open(path, "rb") as file:
            return Data(file.read())

    def size(self) -> int:
        return len(self._bytes)

    def __bytes__(self) -> bytes:
        return self._bytes


def _raw(data: Any) -> bytes:
    return data._bytes if isinstance(data, Data) else bytes(data)


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
    def MakeDefault() -> "Typeface":
        return _default_typeface()

    @staticmethod
    def MakeFromData(data: Any, index: int = 0) -> Optional["Typeface"]:
        handle = H.typeface(to_js(_raw(data)))
        return Typeface(handle) if handle else None

    @staticmethod
    def MakeFromFile(path: str, index: int = 0) -> Optional["Typeface"]:
        return Typeface.MakeFromData(Data.MakeFromFileName(path))


_TYPEFACE: Typeface | None = None


def _default_typeface() -> Typeface:
    global _TYPEFACE
    if _TYPEFACE is None:
        _TYPEFACE = Typeface(CK.Typeface.MakeTypefaceFromData(H.fontData))
    return _TYPEFACE


class FontMgr:
    @staticmethod
    def RefDefault() -> "FontMgr":
        return FontMgr()

    def matchFamilyStyle(self, family: Any, style: Any) -> Typeface:
        return _default_typeface()

    def countFamilies(self) -> int:
        return 0


class FontMetrics:
    __slots__ = ("fAscent", "fDescent", "fLeading")

    def __init__(self, ascent: float, descent: float, leading: float) -> None:
        self.fAscent, self.fDescent, self.fLeading = float(ascent), float(descent), float(leading)


class Font:
    def __init__(self, typeface: Typeface | None = None, size: float = 12.0) -> None:
        self._typeface = typeface if isinstance(typeface, Typeface) else _default_typeface()
        self._f = CK.Font.new(self._typeface._t, float(size))
        self._size = float(size)
        self._metrics: FontMetrics | None = None

    def getSize(self) -> float:
        return self._size

    def setSize(self, size: float) -> None:
        self._size = float(size)
        self._f.setSize(self._size)
        self._metrics = None

    def getMetrics(self) -> FontMetrics:
        if self._metrics is None:
            self._metrics = FontMetrics(*H.metrics(self._f).to_py())
        return self._metrics

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

    def __del__(self) -> None:
        H.release(self._f)


class TextBlob:
    def __init__(self, handle: Any, font: Font, text: str, xpos: Sequence[float] | None = None, y: float = 0.0) -> None:
        self._b = handle
        self._font, self._text, self._xpos, self._y = font, text, xpos, float(y)
        self._bounds: Rect | None = None

    @staticmethod
    def MakeFromString(text: str, font: Font) -> "TextBlob":
        return TextBlob(CK.TextBlob.MakeFromText(text, font._f), font, text)

    @staticmethod
    def MakeFromPosTextH(text: str, xpos: list[float], y: float, font: Font) -> "TextBlob":
        return TextBlob(H.posBlob(text, to_js(xpos), float(y), font._f), font, text, xpos, y)

    def bounds(self) -> Rect:
        """The ink bounds of the glyphs. CanvasKit does not report them, so the font measures them."""
        if self._bounds is None:
            widths, rects = self._font.getWidthsBounds(self._font.textToGlyphs(self._text))
            out = Rect()
            x = 0.0
            for index, (width, rect) in enumerate(zip(widths, rects)):
                if self._xpos is not None and index < len(self._xpos):
                    x = float(self._xpos[index])
                if not rect.isEmpty():
                    moved = Rect(rect.fLeft + x, rect.fTop + self._y, rect.fRight + x, rect.fBottom + self._y)
                    if out.isEmpty():
                        out = moved
                    else:
                        out = Rect(
                            min(out.fLeft, moved.fLeft),
                            min(out.fTop, moved.fTop),
                            max(out.fRight, moved.fRight),
                            max(out.fBottom, moved.fBottom),
                        )
                x += width
            self._bounds = out
        return self._bounds

    def __del__(self) -> None:
        H.release(self._b)


class Image:
    def __init__(self, handle: Any) -> None:
        self._i = handle
        self._w = int(handle.width())
        self._h = int(handle.height())

    @staticmethod
    def MakeFromEncoded(data: Any) -> Optional["Image"]:
        handle = H.decode(to_js(_raw(data)))
        return Image(handle) if handle else None

    def width(self) -> int:
        return self._w

    def height(self) -> int:
        return self._h

    def encodeToData(self, *args: Any) -> Optional[Data]:
        encoded = H.encode(self._i)
        return Data(encoded.to_py().tobytes()) if encoded else None

    def __del__(self) -> None:
        H.release(self._i)


class Matrix:
    """An affine matrix: ``x' = sx*x + kx*y + tx`` and ``y' = ky*x + sy*y + ty``."""

    __slots__ = ("sx", "kx", "tx", "ky", "sy", "ty")

    def __init__(
        self,
        sx: float = 1.0,
        kx: float = 0.0,
        tx: float = 0.0,
        ky: float = 0.0,
        sy: float = 1.0,
        ty: float = 0.0,
    ) -> None:
        self.sx, self.kx, self.tx = float(sx), float(kx), float(tx)
        self.ky, self.sy, self.ty = float(ky), float(sy), float(ty)

    def getScaleX(self) -> float:
        return self.sx

    def getScaleY(self) -> float:
        return self.sy

    def getSkewX(self) -> float:
        return self.kx

    def getSkewY(self) -> float:
        return self.ky

    def getTranslateX(self) -> float:
        return self.tx

    def getTranslateY(self) -> float:
        return self.ty


class Picture:
    def __init__(self, handle: Any) -> None:
        self._p = handle

    def __del__(self) -> None:
        H.release(self._p)


class Path:
    def __init__(self) -> None:
        self._b = CK.PathBuilder.new()

    def moveTo(self, x: float, y: float) -> None:
        self._b.moveTo(x, y)

    def lineTo(self, x: float, y: float) -> None:
        self._b.lineTo(x, y)

    def quadTo(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self._b.quadTo(x1, y1, x2, y2)

    def cubicTo(self, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> None:
        self._b.cubicTo(x1, y1, x2, y2, x3, y3)

    def arcTo(self, oval: Rect, start: float, sweep: float, forceMoveTo: bool) -> None:
        H.arcTo(self._b, oval.fLeft, oval.fTop, oval.fRight, oval.fBottom, start, sweep, bool(forceMoveTo))

    def close(self) -> None:
        self._b.close()

    def addRect(self, rect: Rect, *args: Any) -> None:
        H.addRect(self._b, rect.fLeft, rect.fTop, rect.fRight, rect.fBottom)

    def addRRect(self, rrect: RRect, *args: Any) -> None:
        H.addRRect(self._b, *rrect._flat())

    def addOval(self, oval: Rect, *args: Any) -> None:
        H.addOval(self._b, oval.fLeft, oval.fTop, oval.fRight, oval.fBottom)

    def reset(self) -> None:
        H.release(self._b)
        self._b = CK.PathBuilder.new()

    rewind = reset

    def __del__(self) -> None:
        H.release(self._b)


def _anti_alias(args: tuple[Any, ...], kwargs: dict[str, Any]) -> bool:
    """The ``doAntiAlias`` of a clip call, which skia-python takes last or by name."""
    if "doAntiAlias" in kwargs:
        return bool(kwargs["doAntiAlias"])
    for arg in reversed(args):
        if isinstance(arg, bool):
            return arg
    return False


def _snap(value: float) -> float:
    """Zero for a sine or cosine that is zero but for rounding, as Skia does, so a quarter turn stays exact."""
    return 0.0 if abs(value) < 1.0 / 65536.0 else value


def _find(args: tuple[Any, ...], kind: type) -> Any:
    for arg in args:
        if isinstance(arg, kind):
            return arg
    return None


class Canvas:
    """Forwards draws to CanvasKit and keeps the matrix and the clip bounds in Python."""

    def __init__(self, handle: Any, clip: _Bounds) -> None:
        self._c = handle
        self._sx = self._sy = 1.0
        self._kx = self._ky = self._tx = self._ty = 0.0
        self._clip = clip
        self._stack: list[tuple[float, float, float, float, float, float, _Bounds]] = []
        # Whether the host canvas shows the matrix above, and whether it shows
        # the identity. A save, a restore and a clip leave it at the identity.
        self._synced = True
        self._host_identity = True

    # -- matrix ------------------------------------------------------------

    def _is_identity(self) -> bool:
        return (
            self._sx == 1.0
            and self._sy == 1.0
            and self._kx == 0.0
            and self._ky == 0.0
            and self._tx == 0.0
            and self._ty == 0.0
        )

    def _sync(self) -> None:
        if self._synced:
            return
        identity = self._is_identity()
        if not (identity and self._host_identity):
            H.m(self._c, self._sx, self._kx, self._tx, self._ky, self._sy, self._ty)
            self._host_identity = identity
        self._synced = True

    def _host_popped(self) -> None:
        self._host_identity = True
        self._synced = self._is_identity()

    def translate(self, dx: float, dy: float) -> None:
        self._tx += self._sx * dx + self._kx * dy
        self._ty += self._ky * dx + self._sy * dy
        self._synced = False

    def scale(self, sx: float, sy: float) -> None:
        self._sx *= sx
        self._ky *= sx
        self._kx *= sy
        self._sy *= sy
        self._synced = False

    def rotate(self, degrees: float, px: float | None = None, py: float | None = None) -> None:
        if px is not None and py is not None:
            self.translate(px, py)
        cos, sin = _snap(math.cos(math.radians(degrees))), _snap(math.sin(math.radians(degrees)))
        self._sx, self._kx = self._sx * cos + self._kx * sin, self._kx * cos - self._sx * sin
        self._ky, self._sy = self._ky * cos + self._sy * sin, self._sy * cos - self._ky * sin
        if px is not None and py is not None:
            self.translate(-px, -py)
        self._synced = False

    def concat(self, matrix: Matrix) -> None:
        sx, kx, ky, sy = self._sx, self._kx, self._ky, self._sy
        self._tx += sx * matrix.tx + kx * matrix.ty
        self._ty += ky * matrix.tx + sy * matrix.ty
        self._sx, self._kx = sx * matrix.sx + kx * matrix.ky, sx * matrix.kx + kx * matrix.sy
        self._ky, self._sy = ky * matrix.sx + sy * matrix.ky, ky * matrix.kx + sy * matrix.sy
        self._synced = False

    def setMatrix(self, matrix: Matrix) -> None:
        self._sx, self._kx, self._tx = matrix.sx, matrix.kx, matrix.tx
        self._ky, self._sy, self._ty = matrix.ky, matrix.sy, matrix.ty
        self._synced = False

    def resetMatrix(self) -> None:
        self._sx = self._sy = 1.0
        self._kx = self._ky = self._tx = self._ty = 0.0
        self._synced = False

    def getTotalMatrix(self) -> Matrix:
        return Matrix(self._sx, self._kx, self._tx, self._ky, self._sy, self._ty)

    def _axis_aligned(self) -> bool:
        return self._kx == 0.0 and self._ky == 0.0

    def _device_bounds(self, left: float, top: float, right: float, bottom: float) -> _Bounds:
        xs = [self._sx * x + self._kx * y + self._tx for x in (left, right) for y in (top, bottom)]
        ys = [self._ky * x + self._sy * y + self._ty for x in (left, right) for y in (top, bottom)]
        return (min(xs), min(ys), max(xs), max(ys))

    # -- save stack and clip -------------------------------------------------

    def _push(self) -> int:
        self._stack.append((self._sx, self._kx, self._tx, self._ky, self._sy, self._ty, self._clip))
        self._host_popped()
        return len(self._stack)

    def save(self) -> int:
        H.save(self._c)
        return self._push()

    def saveLayer(self, bounds: Rect | None = None, paint: Paint | None = None, *args: Any) -> int:
        handle = paint.js() if paint is not None else None
        if bounds is None:
            H.saveLayer(self._c, handle, False, 0.0, 0.0, 0.0, 0.0)
        else:
            device = self._device_bounds(bounds.fLeft, bounds.fTop, bounds.fRight, bounds.fBottom)
            H.saveLayer(self._c, handle, True, *device)
        return self._push()

    def restore(self) -> None:
        if not self._stack:
            return
        self._sx, self._kx, self._tx, self._ky, self._sy, self._ty, self._clip = self._stack.pop()
        H.restore(self._c)
        self._host_popped()

    def getSaveCount(self) -> int:
        return len(self._stack) + 1

    def restoreToCount(self, count: int) -> None:
        while len(self._stack) + 1 > max(1, count):
            self.restore()

    def _clip_to(self, rect: Rect, radii: _Radii, anti_alias: bool) -> None:
        device = self._device_bounds(rect.fLeft, rect.fTop, rect.fRight, rect.fBottom)
        left, top, right, bottom = self._clip
        self._clip = (max(left, device[0]), max(top, device[1]), min(right, device[2]), min(bottom, device[3]))
        if not self._axis_aligned():
            H.clipTransformed(
                self._c,
                self._sx,
                self._kx,
                self._tx,
                self._ky,
                self._sy,
                self._ty,
                rect.fLeft,
                rect.fTop,
                rect.fRight,
                rect.fBottom,
                anti_alias,
                *radii,
            )
        elif radii == _NO_RADII:
            H.clipRect(self._c, *device, anti_alias)
        else:
            sx, sy = abs(self._sx), abs(self._sy)
            scaled = [radius * (sx if index % 2 == 0 else sy) for index, radius in enumerate(radii)]
            H.clipRRect(self._c, *device, anti_alias, *scaled)
        self._host_popped()

    def clipRect(self, rect: Rect, *args: Any, **kwargs: Any) -> None:
        self._clip_to(rect, _NO_RADII, _anti_alias(args, kwargs))

    def clipRRect(self, rrect: RRect, *args: Any, **kwargs: Any) -> None:
        self._clip_to(rrect.rc, rrect.radii, _anti_alias(args, kwargs))

    def getLocalClipBounds(self) -> Rect:
        det = self._sx * self._sy - self._kx * self._ky
        if det == 0.0:
            return Rect()
        left, top, right, bottom = self._clip
        xs: list[float] = []
        ys: list[float] = []
        for x in (left, right):
            for y in (top, bottom):
                dx, dy = x - self._tx, y - self._ty
                xs.append((self._sy * dx - self._kx * dy) / det)
                ys.append((self._sx * dy - self._ky * dx) / det)
        return Rect(min(xs), min(ys), max(xs), max(ys))

    # -- draws -------------------------------------------------------------

    def clear(self, color: Any) -> None:
        argb = _argb(color)
        H.clear(
            self._c,
            (argb >> 24 & 255) / 255,
            (argb >> 16 & 255) / 255,
            (argb >> 8 & 255) / 255,
            (argb & 255) / 255,
        )

    def drawRect(self, rect: Rect, paint: Paint) -> None:
        self._sync()
        self._c.drawRect4f(rect.fLeft, rect.fTop, rect.fRight, rect.fBottom, paint.js())

    def drawRoundRect(self, rect: Rect, rx: float, ry: float, paint: Paint) -> None:
        self._sync()
        H.rrect(self._c, rect.fLeft, rect.fTop, rect.fRight, rect.fBottom, rx, ry, paint.js())

    def drawRRect(self, rrect: RRect, paint: Paint) -> None:
        self._sync()
        rc, radii = rrect.rc, rrect.radii
        if radii.count(radii[0]) == 8:
            H.rrect(self._c, rc.fLeft, rc.fTop, rc.fRight, rc.fBottom, radii[0], radii[1], paint.js())
        else:
            H.rrect8(self._c, rc.fLeft, rc.fTop, rc.fRight, rc.fBottom, paint.js(), *radii)

    def drawDRRect(self, outer: RRect, inner: RRect, paint: Paint) -> None:
        self._sync()
        H.drrect(self._c, paint.js(), *outer._flat(), *inner._flat())

    def drawOval(self, rect: Rect, paint: Paint) -> None:
        self._sync()
        H.oval(self._c, rect.fLeft, rect.fTop, rect.fRight, rect.fBottom, paint.js())

    def drawCircle(self, *args: Any) -> None:
        if len(args) == 4:
            cx, cy, radius, paint = args
        else:
            center, radius, paint = args
            cx, cy = center.fX, center.fY
        self._sync()
        self._c.drawCircle(cx, cy, radius, paint.js())

    def drawArc(self, oval: Rect, start: float, sweep: float, useCenter: bool, paint: Paint) -> None:
        self._sync()
        H.arc(self._c, oval.fLeft, oval.fTop, oval.fRight, oval.fBottom, start, sweep, bool(useCenter), paint.js())

    def drawLine(self, *args: Any) -> None:
        if len(args) == 5:
            x0, y0, x1, y1, paint = args
        else:
            p0, p1, paint = args
            x0, y0, x1, y1 = p0.fX, p0.fY, p1.fX, p1.fY
        self._sync()
        self._c.drawLine(x0, y0, x1, y1, paint.js())

    def drawPath(self, path: Path, paint: Paint) -> None:
        self._sync()
        H.path(self._c, path._b, paint.js())

    def drawTextBlob(self, blob: TextBlob, x: float, y: float, paint: Paint) -> None:
        self._sync()
        self._c.drawTextBlob(blob._b, x, y, paint.js())

    def drawImage(self, image: Image, x: float, y: float, *args: Any) -> None:
        sampling, paint = _find(args, SamplingOptions), _find(args, Paint)
        self._sync()
        H.image(
            self._c,
            image._i,
            x,
            y,
            sampling is not None and sampling.linear,
            paint.js() if paint is not None else None,
        )

    def drawImageRect(self, image: Image, src: Rect, dst: Rect, *args: Any) -> None:
        sampling, paint = _find(args, SamplingOptions), _find(args, Paint)
        self._sync()
        H.imageRect(
            self._c,
            image._i,
            src.fLeft,
            src.fTop,
            src.fRight,
            src.fBottom,
            dst.fLeft,
            dst.fTop,
            dst.fRight,
            dst.fBottom,
            sampling is not None and sampling.linear,
            paint.js() if paint is not None else None,
        )

    def drawPicture(self, picture: Picture, *args: Any) -> None:
        self._sync()
        self._c.drawPicture(picture._p)


class Surface:
    """A raster surface, or the on-screen surface when the host hands one over."""

    def __init__(self, width: int, height: int, handle: Any = None) -> None:
        self._w, self._h = int(width), int(height)
        self._owned = handle is None
        self._s = handle if handle is not None else CK.MakeSurface(self._w, self._h)
        if not self._s:
            raise RuntimeError(f"CanvasKit could not make a {self._w}x{self._h} surface")
        self._canvas = Canvas(self._s.getCanvas(), (0.0, 0.0, float(self._w), float(self._h)))

    def getCanvas(self) -> Canvas:
        return self._canvas

    def width(self) -> int:
        return self._w

    def height(self) -> int:
        return self._h

    def makeImageSnapshot(self) -> Image:
        return Image(self._s.makeImageSnapshot())

    def flush(self) -> None:
        self._s.flush()

    def __del__(self) -> None:
        # The host owns the on-screen surface and deletes it on a resize.
        if getattr(self, "_owned", False) and self._s:
            H.release(self._s)


class PictureRecorder:
    def __init__(self) -> None:
        self._r = CK.PictureRecorder.new()

    def beginRecording(self, bounds: Rect) -> Canvas:
        handle = self._r.beginRecording(CK.LTRBRect(bounds.fLeft, bounds.fTop, bounds.fRight, bounds.fBottom))
        return Canvas(handle, (bounds.fLeft, bounds.fTop, bounds.fRight, bounds.fBottom))

    def finishRecordingAsPicture(self) -> Picture:
        return Picture(self._r.finishRecordingAsPicture())

    def __del__(self) -> None:
        H.release(self._r)
