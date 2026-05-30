import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.material import LargeBadge, SmallBadge, Text
from nuiitivet.modifiers import background, corner_radius, stick
from nuiitivet.widgeting.widget import Widget


def _icon_box() -> Widget:
    return nv.Container(
        width=56,
        height=56,
        child=Text("Icon"),
        alignment="center",
    ).modifier(background("#E0E0E0") | corner_radius(8))


def main(png: str = "") -> None:
    content = nv.Row(
        children=[
            # Default: small badge at top-right corner
            _icon_box().modifier(stick(SmallBadge())),
            # Large badge with count
            _icon_box().modifier(stick(LargeBadge("3"))),
            # Custom placement: bottom-right
            _icon_box().modifier(stick(LargeBadge("99+"), alignment="bottom-right", anchor="center")),
        ],
        gap=24,
        padding=24,
    )

    app = md.App(content=content, title="stick Modifier", width=500)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
