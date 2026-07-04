"""Material Widgets - Text layout: line breaks, wrapping and overflow.

Demonstrates the Text layout features that live on the widget itself
(not on TextStyle): hard line breaks (``\\n``), soft wrapping, ``max_lines``,
``overflow`` (visible/clip/ellipsis) and ellipsis ``truncation`` position.

Also shows the ``TypeScaleToken`` typography metrics that the Skia text path
applies: ``weight`` (font thickness) and ``tracking`` (letter spacing).
"""

from __future__ import annotations

from nuiitivet.material import App, Text
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.type_scale import TypeScaleToken
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import Widget

# A width narrow enough that the demo strings must wrap or truncate.
DEMO_WIDTH = 300

SENTENCE = (
    "The quick brown fox jumps over the lazy dog near the riverbank "
    "while the sun sets slowly behind the distant hills."
)
PATH = "/Users/alice/projects/nuiitivet/src/material/text.py"

_BODY = TypeScaleToken.from_size(15)
_CAPTION_SCALE = TypeScaleToken.from_size(11)
_CAPTION = TextStyle(color=ColorRole.ON_SURFACE_VARIANT)

# Typography demo strings/tokens. Same size (24px) so only weight/tracking vary.
TYPO_SAMPLE = "Weight & Tracking"
_HEADING = TypeScaleToken.from_size(24)


def _demo(caption: str, demo: Widget) -> Column:
    """A captioned block: a property label with the example indented beneath it."""
    return Column(
        gap=4,
        cross_alignment="start",
        children=[
            Text(caption, style=_CAPTION, type_scale=_CAPTION_SCALE),
            # Indent the example so the caption reads as its heading.
            Container(padding=(16, 0, 0, 0), child=demo),
        ],
    )


def main(png_path: str = "") -> None:
    content = Container(
        padding=24,
        child=Column(
            gap=16,
            cross_alignment="start",
            children=[
                # Hard line breaks: \n always breaks, regardless of width.
                _demo(
                    "Hard line breaks (\\n)",
                    Text("First line\nSecond line\nThird line", type_scale=_BODY),
                ),
                # Soft wrapping capped to 2 lines, then an ellipsis.
                _demo(
                    "soft_wrap + max_lines=2 + ellipsis",
                    Text(
                        SENTENCE,
                        type_scale=_BODY,
                        width=Sizing.fixed(DEMO_WIDTH),
                        max_lines=2,
                        overflow="ellipsis",
                    ),
                ),
                # Single line, cut at the edge.
                _demo(
                    "overflow=clip (max_lines=1)",
                    Text(
                        SENTENCE,
                        type_scale=_BODY,
                        width=Sizing.fixed(DEMO_WIDTH),
                        max_lines=1,
                        overflow="clip",
                    ),
                ),
                # Single line, ellipsis at the end (default truncation).
                _demo(
                    "overflow=ellipsis, truncation=tail",
                    Text(
                        SENTENCE,
                        type_scale=_BODY,
                        width=Sizing.fixed(DEMO_WIDTH),
                        max_lines=1,
                        overflow="ellipsis",
                        truncation="tail",
                    ),
                ),
                # Middle truncation keeps both ends — great for file paths.
                _demo(
                    "truncation=middle",
                    Text(
                        PATH,
                        type_scale=_BODY,
                        width=Sizing.fixed(DEMO_WIDTH),
                        max_lines=1,
                        overflow="ellipsis",
                        truncation="middle",
                    ),
                ),
                # Head truncation keeps the tail (e.g. the file name).
                _demo(
                    "truncation=head",
                    Text(
                        PATH,
                        type_scale=_BODY,
                        width=Sizing.fixed(DEMO_WIDTH),
                        max_lines=1,
                        overflow="ellipsis",
                        truncation="head",
                    ),
                ),
                # Weight: same 24px size, increasing font thickness.
                _demo(
                    "weight (300 / 400 / 700 / 900)",
                    Column(
                        gap=2,
                        cross_alignment="start",
                        children=[
                            Text(TYPO_SAMPLE, type_scale=_HEADING.copy_with(weight=w))
                            for w in (300, 400, 700, 900)
                        ],
                    ),
                ),
                # Tracking: same 24px size, widening letter spacing (incl. negative).
                _demo(
                    "tracking (-1.0 / 0.0 / 2.0 / 6.0 px)",
                    Column(
                        gap=2,
                        cross_alignment="start",
                        children=[
                            Text(TYPO_SAMPLE, type_scale=_HEADING.copy_with(tracking=t))
                            for t in (-1.0, 0.0, 2.0, 6.0)
                        ],
                    ),
                ),
            ],
        ),
    )
    app = App(
        content=content,
        title="Text",
        width=420,
        height=760,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
