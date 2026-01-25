# Probe script: inspect Scroller viewport_rect and scrollbar config
from nuiitivet.layout.scroller import Scroller
from nuiitivet.widgets import text as text_mod
from nuiitivet.layout import scroll_viewport as sv_mod
from nuiitivet.widgets import scrollbar as sb_mod
from samples.my_widget import MyWidget, MyWidgetModel


def find_scrollers(widget):
    out = []
    try:
        children = getattr(widget, "children", [])
    except Exception:
        children = []
    for c in children:
        if isinstance(c, Scroller):
            out.append(c)
        out.extend(find_scrollers(c))
    return out


if __name__ == "__main__":
    model = MyWidgetModel()
    widget = MyWidget(model)
    # build to ensure children created
    root = widget.build()
    scrollers = find_scrollers(root)
    print("Found scrollers:", len(scrollers))
    for i, s in enumerate(scrollers):
        cfg = getattr(s, "_scrollbar_config", None)
        hdim = s.height_sizing.kind if hasattr(s, "height_sizing") else None
        print(f"Scroller[{i}] direction={s.direction} height={hdim}")
        print("  scrollbar_config.auto_hide=", getattr(cfg, "auto_hide", None))

    # pick the horizontal scroller (direction HORIZONTAL)
    horiz = next((s for s in scrollers if str(s.direction).endswith("HORIZONTAL")), None)
    if horiz is None:
        print("No horizontal scroller found")
    else:
        print("Probing horizontal scroller...")
        # Patch get_skia to None in modules that use it so paint uses non-skia path
        orig_sv_get_skia = sv_mod.get_skia
        orig_sb_get_skia = sb_mod.get_skia
        sv_mod.get_skia = lambda raise_if_missing=False: None
        sb_mod.get_skia = lambda raise_if_missing=False: None
        orig_text_paint = text_mod.Text.paint
        text_mod.Text.paint = lambda self, canvas, x, y, w, h: None
        try:
            horiz.paint(canvas=None, x=0, y=0, width=400, height=50)
            vp = horiz._viewport.viewport_rect
            print("  viewport_rect=", vp)
            print("  recorded scrollbar_rect=", getattr(horiz, "_scrollbar_rect", None))
        finally:
            sv_mod.get_skia = orig_sv_get_skia
            sb_mod.get_skia = orig_sb_get_skia
            text_mod.Text.paint = orig_text_paint
