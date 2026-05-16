import types

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.widgets.box import Box


def test_box_theme_change_invalidates_cache():
    box = Box(background_color=ColorRole.PRIMARY)
    calls: list[str] = []
    original_cache = box.invalidate_paint_cache

    def fake_cache(self):
        calls.append("cache")
        original_cache()

    def fake_invalidate(self):
        calls.append("invalidate")

    box.invalidate_paint_cache = types.MethodType(fake_cache, box)
    box.invalidate = types.MethodType(fake_invalidate, box)
    box._handle_theme_change(None)
    assert calls == ["cache", "invalidate"]


def test_box_literal_colors_do_not_subscribe():
    box = Box(background_color="#FFFFFF", border_color="#000000")
    box.on_mount()
    try:
        assert getattr(box, "_box_theme_subscription", None) is None
    finally:
        box.on_unmount()


def test_box_subscription_updates_when_colors_change():
    """Without AppScope, no subscription is created regardless of color type.
    _uses_theme_colors() still tracks whether a subscription would be needed."""
    box = Box(background_color="#FFFFFF")
    box.on_mount()
    try:
        # No AppScope → no subscription
        assert getattr(box, "_box_theme_subscription", None) is None
        box.bgcolor = ColorRole.PRIMARY
        # Still None without AppScope, but _uses_theme_colors() is True
        assert getattr(box, "_box_theme_subscription", None) is None
        assert box._uses_theme_colors() is True
        box.bgcolor = "#FFFFFF"
        assert getattr(box, "_box_theme_subscription", None) is None
        assert box._uses_theme_colors() is False
    finally:
        box.on_unmount()
