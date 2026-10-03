import sys
import types
import nuiitivet.theme.theme as _theme_module
from nuiitivet.theme import Theme
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.text import Text
from nuiitivet.rendering.skia.font import _clear_typeface_caches_for_tests


def _make_dummy_skia():
    mod = types.ModuleType("skia")

    class Paint:
        kStroke_Style = 1
        kFill_Style = 0

        def __init__(self):
            pass

        def setAntiAlias(self, v):
            pass

        def setStyle(self, v):
            pass

        def setStrokeWidth(self, w):
            pass

        def setColor(self, c):
            mod._last_color = c

    class TextBlob:

        @staticmethod
        def MakeFromString(s, font):
            return TextBlob()

        def bounds(self):

            class B:

                def left(self):
                    return 0

                def top(self):
                    return 0

                def width(self):
                    return 10

                def height(self):
                    return 10

            return B()

    def ColorSetARGB(a, r, g, b):
        return (a, r, g, b)

    mod.Paint = Paint
    mod.TextBlob = TextBlob
    mod.ColorSetARGB = ColorSetARGB

    class Font:

        def __init__(self, tf, size):
            self.tf = tf
            self.size = size

    mod.Font = Font
    mod.Typeface = object
    mod.FontStyle = object
    return mod


def test_text_uses_theme_color(monkeypatch, request):
    dummy = _make_dummy_skia()
    monkeypatch.setitem(sys.modules, "skia", dummy)
    # Typefaces resolved against the dummy must not outlive it.
    _clear_typeface_caches_for_tests()
    request.addfinalizer(_clear_typeface_caches_for_tests)
    from nuiitivet.material.theme.theme_data import MaterialThemeData

    custom = Theme(name="t", mode="light", extensions=[MaterialThemeData(roles={ColorRole.ON_SURFACE: "#112233"})])
    monkeypatch.setattr(_theme_module.Theme, "of", staticmethod(lambda ctx: custom))
    t = Text("hello")

    class DummyCanvas:

        def drawTextBlob(self, blob, tx, ty, paint):
            DummyCanvas.called = True

    canvas = DummyCanvas()
    t.paint(canvas, 0, 0, 100, 20)
    assert hasattr(dummy, "_last_color"), "Paint.setColor was not called"
    assert dummy._last_color == (51, 255, 17, 34)
