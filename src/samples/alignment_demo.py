from nuiitivet.material.app import MaterialApp
from nuiitivet.widgeting.widget import Widget
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.layout.container import Container
from nuiitivet.material import Text
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.modifiers import background, border, scrollable


def ColoredBox(label: str, w: int = 60, h: int = 40, color="#E0E0E0"):
    t = Text(label)
    c = Container(
        width=w,
        height=h,
        child=t,
        alignment="center",
    )
    return c.modifier(background(color) | border("black", 1))


def Section(title: str, child: Widget):
    # Wrap child in Container to add padding, then apply border
    # This ensures padding is inside the border
    content = Container(child=child, padding=8, width=Sizing.flex())
    bordered_content = content.modifier(border("#ccc", 1))

    return Column(
        gap=8,
        width=Sizing.flex(),
        children=[Text(title), bordered_content],
    )


def main():
    # Row Main Alignment Demo
    row_alignments = ["start", "center", "end", "space-between", "space-around", "space-evenly"]

    row_demos = []
    for align in row_alignments:
        row = Row(
            width=Sizing.flex(),  # Fill width to show alignment
            gap=10,
            main_alignment=align,
            children=[
                ColoredBox("1", 40, 40, "#FFCDD2"),
                ColoredBox("2", 40, 40, "#C8E6C9"),
                ColoredBox("3", 40, 40, "#BBDEFB"),
            ],
        )
        row_demos.append(Section(f"Row main_alignment='{align}'", row))

    # Column Main Alignment Demo (Vertical)
    # We need fixed height container to show vertical alignment
    col_alignments = ["start", "center", "end", "space-between"]
    col_demos = []
    for align in col_alignments:
        col = Column(
            height=200,
            width=Sizing.flex(),
            gap=10,
            main_alignment=align,
            cross_alignment="center",  # Center horizontally
            children=[
                ColoredBox("A", 40, 40, "#FFCDD2"),
                ColoredBox("B", 40, 40, "#C8E6C9"),
                ColoredBox("C", 40, 40, "#BBDEFB"),
            ],
        )
        col_demos.append(Section(f"Column main_alignment='{align}' (h=200)", col))

    # Cross Alignment Demo
    # Row with different heights
    cross_alignments = ["start", "center", "end"]
    cross_demos = []
    for align in cross_alignments:
        row = Row(
            gap=10,
            cross_alignment=align,
            children=[
                ColoredBox("H=40", 60, 40, "#FFCDD2"),
                ColoredBox("H=80", 60, 80, "#C8E6C9"),
                ColoredBox("H=60", 60, 60, "#BBDEFB"),
            ],
        )
        cross_demos.append(Section(f"Row cross_alignment='{align}'", row))

    root = Row(
        padding=20,
        gap=20,
        children=[
            Column(row_demos),
            Column(cross_demos),
            Column(col_demos),
        ],
    )

    # Wrap in Scroller because it will be long
    scrollable_root = root.modifier(scrollable())

    app = MaterialApp(content=scrollable_root)
    app.run()


if __name__ == "__main__":
    main()
