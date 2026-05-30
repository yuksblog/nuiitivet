from nuiitivet.rendering.background_renderer import BackgroundRenderer


class DummyOwner:
    def __init__(self):
        self.bgcolor = "#ffffff"
        self.corner_radii = None
        self.corner_radius = None
        self.shadow_color = None
        self.shadow_offset = (0, 0)
        self.shadow_blur = 0.0
        self.border_width = 0
        self.border_color = None


def test_corner_radii_tuple_absolute_preserve():
    owner = DummyOwner()
    owner.corner_radii = (8, 8, 8, 8)
    br = BackgroundRenderer(owner)
    radii = br.corner_radii_pixels(200, 200)
    assert radii == (8.0, 8.0, 8.0, 8.0)


def test_corner_radii_tuple_proportion():
    owner = DummyOwner()
    owner.corner_radii = (0.25, 0.5, 0.0, 0.0)
    br = BackgroundRenderer(owner)
    # min(width,height)=80 -> half=40 -> 0.25*40=10, 0.5*40=20
    radii = br.corner_radii_pixels(100, 80)
    assert radii == (10.0, 20.0, 0.0, 0.0)


def test_corner_radii_tuple_cap():
    owner = DummyOwner()
    owner.corner_radii = (30, 30, 30, 30)
    br = BackgroundRenderer(owner)
    # width=20,height=20 -> half min dim = 10 -> cap to 10px
    radii = br.corner_radii_pixels(20, 20)
    assert radii == (10.0, 10.0, 10.0, 10.0)


def test_scalar_int_and_float_legacy():
    owner = DummyOwner()
    # int treated as absolute pixels
    owner.corner_radii = None
    owner.corner_radius = 12
    br = BackgroundRenderer(owner)
    assert br.corner_radii_pixels(100, 100) == (12.0, 12.0, 12.0, 12.0)

    # float < 1 treated as proportion
    owner.corner_radius = 0.5
    radii = br.corner_radii_pixels(100, 80)
    # min=80 -> half=40 -> 0.5*40 = 20
    assert radii == (20.0, 20.0, 20.0, 20.0)


def test_paint_background_calls_draw_methods(monkeypatch):
    owner = DummyOwner()
    br = BackgroundRenderer(owner)

    calls = []

    def fake_draw_background(canvas, x, y, width, height, paint, eff_rad):
        calls.append(("background", x, y, width, height, eff_rad))

    def fake_draw_shadow(canvas, x, y, width, height, sc, dx, dy, sb, eff_rad):
        calls.append(("shadow", x, y, width, height, sc, dx, dy, sb, eff_rad))

    # monkeypatch the instance methods
    monkeypatch.setattr(br, "_draw_background", fake_draw_background)
    monkeypatch.setattr(br, "_draw_shadow", fake_draw_shadow)

    # ensure resolve_color_to_rgba and make_paint don't raise/return None
    monkeypatch.setattr("nuiitivet.theme.resolver.resolve_color_to_rgba", lambda c, **_: (1, 1, 1, 1))
    monkeypatch.setattr("nuiitivet.rendering.background_renderer.make_paint", lambda **kw: object())

    # No shadow configured -> only background should be called
    owner.shadow_color = None
    br.paint_background(canvas=None, x=0, y=0, width=50, height=40)
    assert calls and calls[0][0] == "background"

    # Reset and configure shadow -> shadow should be called before background
    calls.clear()
    owner.shadow_color = ("#000000", 0.3)
    owner.shadow_offset = (2, 3)
    owner.shadow_blur = 0.0
    br.paint_background(canvas=None, x=1, y=2, width=60, height=50)
    assert calls and calls[0][0] == "shadow"


def test_paint_background_no_bg_early_return(monkeypatch):
    owner = DummyOwner()
    owner.bgcolor = None
    br = BackgroundRenderer(owner)

    called = {"bg": False}

    def fake_draw_background(canvas, x, y, width, height, paint, eff_rad):
        called["bg"] = True

    monkeypatch.setattr(br, "_draw_background", fake_draw_background)
    br.paint_background(canvas=None, x=0, y=0, width=10, height=10)
    assert not called["bg"]
