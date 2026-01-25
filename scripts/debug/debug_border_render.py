import os
import sys


def main():
    # Add src to path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

    try:
        import skia  # noqa: F401
    except ImportError:
        print("skia-python not found")
        sys.exit(1)

    from nuiitivet.runtime.app import App
    from nuiitivet.layout.column import Column
    from nuiitivet.modifiers import border, corner_radius
    from nuiitivet.widgets.text import Text

    # Step 5: Use App.render_to_png
    box2 = Text("Chained Modifiers", padding=20)
    mod2 = corner_radius(8) | border("blue", width=3)
    widget2 = box2.modifier(mod2)

    root = Column(children=[Text("Title", padding=10), widget2], padding=20, gap=10)

    app = App(root=root, width=300, height=300, background="white")
    app.render_to_png("debug_border_render_step5.png")
    print("Saved debug_border_render_step5.png")


if __name__ == "__main__":
    main()
