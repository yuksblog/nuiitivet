import sys
import types
from nuiitivet.material.buttons import FilledButton


class _FakeRect:
    def left(self):
        return 0.0

    def top(self):
        return 0.0

    def height(self):
        return 10.0


class _FakeTextBlob:
    @staticmethod
    def MakeFromString(_text, _font):
        return _FakeTextBlob()

    def bounds(self):
        return _FakeRect()


class _FakeFont:
    def __init__(self, _typeface, _size):
        self.typeface = _typeface
        self.size = _size


class _FakeTypeface:
    @staticmethod
    def MakeFromName(_family, _style):
        return _FakeTypeface()

    @staticmethod
    def MakeFromFile(_path):
        return _FakeTypeface()

    @staticmethod
    def MakeFromData(_data):
        return _FakeTypeface()


class _FakeFontMgr:
    @staticmethod
    def RefDefault():
        return _FakeFontMgr()

    def matchFamilyStyle(self, _family, _style):
        return _FakeTypeface()

    def getFamilyCount(self):
        return 0

    def getFamilyName(self, _index):
        return "Fake"

    def countFamilies(self):
        return 0


class _FakeFontStyle:
    pass


class _FakeData:
    @staticmethod
    def MakeFromFileName(_path):
        return b""


class _FakePaint:
    def setAntiAlias(self, *_args, **_kwargs):
        pass

    def setStyle(self, *_args, **_kwargs):
        pass

    def setStrokeWidth(self, *_args, **_kwargs):
        pass

    def setColor(self, *_args, **_kwargs):
        pass


def _install_fake_skia():
    fake_skia = types.SimpleNamespace(
        Font=_FakeFont,
        TextBlob=_FakeTextBlob,
        Typeface=_FakeTypeface,
        FontMgr=_FakeFontMgr,
        FontStyle=_FakeFontStyle,
        Paint=_FakePaint,
        Data=_FakeData,
        ColorSetARGB=lambda a, r, g, b: (a, r, g, b),
    )
    sys.modules["skia"] = fake_skia
    from nuiitivet.rendering.skia import skia_module

    skia_module._reset_skia_import_state_for_tests()
    skia_module.get_skia(raise_if_missing=True)
    return fake_skia


def _remove_fake_skia():
    from nuiitivet.rendering.skia import skia_module

    skia_module._reset_skia_import_state_for_tests()
    if "skia" in sys.modules:
        del sys.modules["skia"]


def test_child_painted_without_skiamodule():
    if "skia" in sys.modules:
        del sys.modules["skia"]
    _remove_fake_skia()
    b = FilledButton("ok")
    b.paint(None, 10, 20, 100, 40)
    child = b.children[0]
    child_rect = child.last_rect
    assert child_rect is not None
    cx, cy, cw, ch = child_rect
    assert 10 <= cx <= 10 + 100
    assert 20 <= cy <= 20 + 40


def test_child_painted_with_fake_skia():
    _install_fake_skia()
    try:
        b = FilledButton("ok")
        b.paint(None, 5, 6, 120, 30)
        child = b.children[0]
        assert child.last_rect is not None
    finally:
        _remove_fake_skia()
