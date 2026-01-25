"""Test padding support for Text and Icon widgets."""

from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.material.icon import Icon


def test_text_default_padding():
    """Text should have default padding of 0."""
    text = Text("Hello")
    assert text.padding == (0, 0, 0, 0)


def test_text_with_padding():
    """Text should accept padding parameter."""
    text1 = Text("Hello", padding=10)
    assert text1.padding == (10, 10, 10, 10)
    text2 = Text("World", padding=(8, 12))
    assert text2.padding == (8, 12, 8, 12)
    text3 = Text("Test", padding=(5, 10, 15, 20))
    assert text3.padding == (5, 10, 15, 20)


def test_text_preferred_size_includes_padding():
    """Text preferred_size should include padding."""
    text_no_pad = Text("Hello", padding=0)
    w0, h0 = text_no_pad.preferred_size()
    text_with_pad = Text("Hello", padding=10)
    w1, h1 = text_with_pad.preferred_size()
    assert w1 == w0 + 20
    assert h1 == h0 + 20


def test_text_content_rect():
    """Text should use content_rect for text placement."""
    text = Text("Test", padding=10)
    cx, cy, cw, ch = text.content_rect(0, 0, 100, 100)
    assert cx == 10
    assert cy == 10
    assert cw == 80
    assert ch == 80


def test_icon_default_padding():
    """Icon should have default padding of 0."""
    icon = Icon("home")
    assert icon.padding == (0, 0, 0, 0)


def test_icon_with_padding():
    """Icon should accept padding parameter."""
    icon1 = Icon("menu", padding=8)
    assert icon1.padding == (8, 8, 8, 8)
    icon2 = Icon("search", padding=(4, 6))
    assert icon2.padding == (4, 6, 4, 6)
    icon3 = Icon("settings", padding=(2, 4, 6, 8))
    assert icon3.padding == (2, 4, 6, 8)


def test_icon_preferred_size_includes_padding():
    """Icon preferred_size should include padding."""
    icon_no_pad = Icon("home", size=24, padding=0)
    w0, h0 = icon_no_pad.preferred_size()
    assert w0 == 24
    assert h0 == 24
    icon_with_pad = Icon("home", size=24, padding=8)
    w1, h1 = icon_with_pad.preferred_size()
    assert w1 == 40
    assert h1 == 40


def test_icon_content_rect():
    """Icon should use content_rect for icon placement."""
    icon = Icon("home", size=24, padding=10)
    cx, cy, cw, ch = icon.content_rect(0, 0, 100, 100)
    assert cx == 10
    assert cy == 10
    assert cw == 80
    assert ch == 80


def test_text_asymmetric_padding():
    """Text should handle asymmetric padding correctly."""
    text_no_pad = Text("Test", padding=0)
    w0, h0 = text_no_pad.preferred_size()
    text_asym = Text("Test", padding=(5, 10, 15, 20))
    w1, h1 = text_asym.preferred_size()
    assert w1 == w0 + 20
    assert h1 == h0 + 30


def test_icon_asymmetric_padding():
    """Icon should handle asymmetric padding correctly."""
    icon_no_pad = Icon("home", size=24, padding=0)
    w0, h0 = icon_no_pad.preferred_size()
    assert w0 == 24
    assert h0 == 24
    icon_asym = Icon("home", size=24, padding=(4, 8, 12, 16))
    w1, h1 = icon_asym.preferred_size()
    assert w1 == 40
    assert h1 == 48
