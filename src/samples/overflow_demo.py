"""
Phase 2 overflow demonstration.

Shows the difference between overflow="visible" and overflow="clip":
- Top demo: overflow="visible" (children extend beyond bounds)
- Bottom demo: overflow="clip" (children clipped to bounds)

Visual comparison demonstrates the clipping behavior.
"""

from nuiitivet.material.app import MaterialApp
from nuiitivet.rendering import Sizing
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.material.card import FilledCard
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.material import Text
from nuiitivet.material.theme.color_role import ColorRole
from typing import Literal


def build_demo_container(overflow_mode: Literal["visible", "clip", "scroll"]):
    """Build a demo container with specified overflow mode."""
    large_content = Column(
        children=[
            Text(
                (
                    "This is a very long text that should extend beyond the container bounds when "
                    "overflow='visible' but will be clipped when overflow='clip'. The quick brown fox "
                    "jumps over the lazy dog. Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
                ),
                width=Sizing.fixed(400),
                height=Sizing.auto(),
            )
        ],
        width=Sizing.auto(),
        height=Sizing.auto(),
    )

    demo_container = FilledCard(
        child=large_content,
        width=Sizing.fixed(300),
        height=Sizing.fixed(150),
        style=CardStyle.filled().copy_with(
            background=(ColorRole.SURFACE_VARIANT, 1.0),
            border_width=2,
            border_color=(ColorRole.OUTLINE, 1.0),
            border_radius=12,
        ),
    )

    if overflow_mode == "clip":
        demo_container.clip_content = True

    return demo_container


def build_ui():
    """Build the UI with both overflow modes side by side."""
    title = Text("Phase 2 Overflow Demo", width=Sizing.fixed(600), height=Sizing.auto())
    visible_label = Text(
        "overflow='visible' (default):\nContent extends beyond bounds",
        width=Sizing.fixed(600),
        height=Sizing.auto(),
    )
    visible_demo = build_demo_container("visible")
    spacer1 = Container(height=Sizing.fixed(20))
    clip_label = Text(
        "overflow='clip':\nContent clipped to container bounds (blue border)",
        width=Sizing.fixed(600),
        height=Sizing.auto(),
    )
    clip_demo = build_demo_container("clip")
    root = Column(
        children=[
            title,
            Container(height=Sizing.fixed(20)),
            visible_label,
            Container(height=Sizing.fixed(10)),
            visible_demo,
            spacer1,
            clip_label,
            Container(height=Sizing.fixed(10)),
            clip_demo,
        ],
        width=Sizing.auto(),
        height=Sizing.auto(),
        gap=10,
        padding=(20, 20, 20, 20),
    )
    return root


if __name__ == "__main__":
    app = MaterialApp(content=build_ui(), background=(ColorRole.SURFACE, 1.0))
    app.run()
