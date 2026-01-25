import types

from nuiitivet.theme import manager
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
    box.on_mount()
    try:
        callback = getattr(box, "_box_theme_subscription", None)
        assert callback is not None
        callback(manager.current)
    finally:
        box.on_unmount()
    assert calls == ["cache", "invalidate"]


def test_box_literal_colors_do_not_subscribe():
    box = Box(background_color="#FFFFFF", border_color="#000000")
    box.on_mount()
    try:
        assert getattr(box, "_box_theme_subscription", None) is None
    finally:
        box.on_unmount()


def test_box_subscription_updates_when_colors_change():
    box = Box(background_color="#FFFFFF")
    box.on_mount()
    try:
        assert getattr(box, "_box_theme_subscription", None) is None
        box.bgcolor = ColorRole.PRIMARY
        assert getattr(box, "_box_theme_subscription", None) is not None
        box.bgcolor = "#FFFFFF"
        assert getattr(box, "_box_theme_subscription", None) is None
    finally:
        box.on_unmount()
