from nuiitivet.material.app import MaterialApp
from nuiitivet.material import Text
from nuiitivet.layout.column import Column
from nuiitivet.widgets.box import Box
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.modifiers import background, border, clip, corner_radius, scrollable, shadow


def main():
    # 1. Basic Modifier: Background & Border
    box1 = Text("Red Box with Radius", padding=20, style=TextStyle(color="white"))
    # Apply background red, radius 16, then border black width 2
    mod1 = corner_radius(16) | background("red") | border("black", width=2)
    widget1 = box1.modifier(mod1)

    # 2. Chained Modifiers with Shadow
    # Shadow -> Border -> Background
    box2 = Text("Chained Modifiers", padding=20)
    mod2 = corner_radius(8) | background("#E0E0E0") | border("blue", width=3) | shadow("black", blur=10, offset=(5, 5))
    widget2 = box2.modifier(mod2)

    # 3. Rounded clip via corner radius
    # A box with content that needs clipping.
    inner = Box(width=Sizing.fixed(100), height=Sizing.fixed(100), background_color="orange")
    # Apply radius 50 (circle)
    mod3 = corner_radius(50)
    widget3 = inner.modifier(mod3)

    # 4. Explicit Clip
    # A small box containing a large box, clipped.
    large_child = Box(width=Sizing.fixed(100), height=Sizing.fixed(100), background_color="purple")
    # Parent is smaller (60x60) and clips content
    box5 = Box(child=large_child, width=Sizing.fixed(60), height=Sizing.fixed(60), background_color="#ddd")
    mod5 = clip()
    widget5 = box5.modifier(mod5)

    # 5. Scrollable
    # A fixed height container with many items
    items = [Text(f"Scroll Item {i}", padding=4) for i in range(20)]
    col_content = Column(children=items, width=Sizing.fixed(200), gap=4)

    # Apply scrollable modifier. This wraps Column in a Scroller.
    mod6 = scrollable(axis="y")
    scroller = col_content.modifier(mod6)

    # Constrain the scrollable area with a Box
    widget6 = Box(
        child=scroller, width=Sizing.fixed(200), height=Sizing.fixed(150), border_color="gray", border_width=1
    )

    # Layout
    content = Column(
        children=[
            Text("Modifier System Demo", padding=20),
            Text("1. Background & Border", padding=(0, 10, 0, 5)),
            widget1,
            Text("2. Shadow > Border > Background", padding=(0, 20, 0, 5)),
            widget2,
            Text("3. Corner Radius (Circle)", padding=(0, 20, 0, 5)),
            widget3,
            Text("4. Explicit Clip", padding=(0, 20, 0, 5)),
            widget5,
            Text("5. Scrollable", padding=(0, 20, 0, 5)),
            widget6,
        ],
        padding=40,
        gap=20,
        cross_alignment="center",
    )

    app = MaterialApp(content=content)
    app.run()


if __name__ == "__main__":
    main()
