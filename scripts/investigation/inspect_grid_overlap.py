import os
import sys


def collect_rects(root):
    res = []

    def walk(w, depth=0):
        try:
            cls = type(w).__name__
            rect = getattr(w, "_last_rect", None)
            info = (depth, cls, rect, getattr(getattr(w, "", None), "label", getattr(w, "label", None)))
            res.append(info)
        except Exception:
            pass
        try:
            for c in w.children_snapshot():
                walk(c, depth + 1)
        except Exception:
            pass

    walk(root)
    return res


def inspect_for_n(n):
    # Ensure project `src` directory is on sys.path so `nuiitivet` package imports work
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    SRC = os.path.join(ROOT, "src")
    if SRC not in sys.path:
        sys.path.insert(0, SRC)

    from samples.my_widget import MyWidgetModel, MyWidget
    from nuiitivet.runtime.app import App

    model = MyWidgetModel()
    # prefill grid items
    items = [f"GItem {i+1}" for i in range(n)]
    model.grid_items.set(items)
    widget = MyWidget(model)
    from nuiitivet.runtime.title_bar import DefaultTitleBar

    app = App(root=widget, width=480, height=600, title_bar=DefaultTitleBar(top_padding=16))

    # Normalize root as App.run would
    built = app.root.evaluate_build()
    if built is not None:
        app.root = built

        # Debug: print widget class tree (structure) before mount
        def print_tree(w, depth=0):
            print("  " * depth + type(w).__name__)
            try:
                for c in w.children_snapshot():
                    print_tree(c, depth + 1)
            except Exception:
                pass

        print("Widget tree:")
        print_tree(app.root)

    # Mount and paint (use None for canvas; paints often early-exit if skia missing,
    # but layout code sets _last_rect before requiring skia)
    try:
        app.root.mount(app)
    except Exception as e:
        print("mount failed:", e)

    # Prefer rendering into a real Skia canvas when available so paint() runs
    # fully and sets all _last_rect entries. Fall back to None and accept
    # partial layout information if skia isn't available.
    canvas = None
    try:
        import skia

        surface = skia.Surface(max(1, app.width), max(1, app.height))
        canvas = surface.getCanvas()
    except Exception:
        canvas = None

    try:
        app.root.paint(canvas, 0, 0, app.width, app.height)
    except Exception:
        # ignore painting errors; we only need _last_rects set by layout
        pass

    rects = collect_rects(app.root)

    # Print all nodes with a _last_rect for inspection
    print(f"--- N={n} — all nodes with _last_rect ---")
    for depth, cls, rect, lbl in rects:
        if rect is not None:
            print("  " * depth + f"{cls}: rect={rect} label={lbl}")
    # Also print last few GItems and the button labels (even if rect is None)
    gitems = [(d, cls, r, lbl) for (d, cls, r, lbl) in rects if lbl and str(lbl).startswith("GItem")]
    print("--- tail GItems ---")
    for gi in gitems[-6:]:
        print(gi)
    print("--- Buttons (labels) ---")
    for depth, cls, rect, lbl in rects:
        if lbl and (str(lbl) == "+" or str(lbl).startswith("Remove")):
            print((depth, cls, rect, lbl))

    try:
        app.root.unmount()
    except Exception:
        pass

    # As an extra check: find Flow instance and force-paint it into the Column
    try:

        def find_flow_layout(w):
            if type(w).__name__ == "Flow":
                return w
            for c in w.children_snapshot():
                found = find_flow_layout(c)
                if found:
                    return found
            return None

        tg = find_flow_layout(app.root)
        if tg is not None:
            print("Found Flow, forcing paint to populate child rects")
            try:
                print("Flow.children_snapshot() count:", len(tg.children_snapshot()))
                print("Flow.children types:", [type(c).__name__ for c in tg.children_snapshot()])
            except Exception:
                pass

            # Try to find ancestor Column rect to get an approximate area
            def find_parent_column_rect(w):
                if type(w).__name__ == "Column":
                    return getattr(w, "_last_rect", None)
                for c in w.children_snapshot():
                    r = find_parent_column_rect(c)
                    if r:
                        return r
                return None

            col_rect = find_parent_column_rect(app.root) or (0, 0, app.width, app.height)
            cx, cy, cw, ch = col_rect
            try:
                tg.paint(None, cx, cy, cw, ch)
            except Exception as e:
                print("Flow.paint exception:", repr(e))
            rects2 = collect_rects(tg)
            print("Flow children after forced paint:")
            for depth, cls, rect, lbl in rects2:
                print(depth, cls, rect, lbl)
    except Exception:
        pass


if __name__ == "__main__":
    inspect_for_n(22)
    inspect_for_n(23)
