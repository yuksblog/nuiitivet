"""Material Widgets - ButtonGroup showcase.

Showcases the Material 3 button-group family: standard variants
(filled / tonal / outlined), the per-size pressed-width interaction, and the
connected single-select group.
"""

from __future__ import annotations

from nuiitivet.material import (
    App,
    ConnectedButtonGroup,
    HorizontalDivider,
    GroupButton,
    StandardButtonGroup,
    Text,
)
from nuiitivet.material.styles.button_group_style import (
    ConnectedButtonGroupStyle,
    StandardButtonGroupStyle,
)
from nuiitivet.material.styles.button_size import ButtonSize
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row

# Icons reused for the tonal icon-only group.
_ALIGN_ICONS = ("format_align_left", "format_align_center", "format_align_right")

# Size scale content: each row varies icons and label presence (icon-only,
# label-only, icon + label).  Content-fit widths keep the pressed-width
# interaction working and avoid narrow vertical pills at large sizes.
_SIZES: tuple[ButtonSize, ...] = ("xs", "s", "m", "l", "xl")

_SIZE_CONTENT: dict[ButtonSize, list[tuple[str | None, str | None]]] = {
    "xs": [("format_align_left", None), ("format_align_center", None), ("format_align_right", None)],
    "s": [(None, "Day"), (None, "Week"), (None, "Month")],
    "m": [("calendar_today", "Day"), ("event", "Week"), ("schedule", "Month")],
    "l": [("call", "Call"), ("email", "Mail"), ("map", "Map")],
    "xl": [("favorite", "Like"), ("bolt", "Boost"), ("movie", "Watch")],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _section_title(text: str) -> Text:
    return Text(text, style=TextStyle(font_size=18, color=ColorRole.ON_SURFACE))


def _caption(text: str) -> Text:
    return Text(text, style=TextStyle(font_size=12, color=ColorRole.ON_SURFACE_VARIANT))


def _labeled(caption: str, widget) -> Column:
    """A small caption stacked above a button group."""
    return Column(gap=8, cross_alignment="start", children=[_caption(caption), widget])


def _section(title: str, *rows) -> Column:
    """A titled section grouping related examples.

    A plain ``Column`` (not ``Card``): ``Card`` is a scoped ``WidgetBuilder``
    that rebuilds — and unmounts — its subtree on every measure, which cancels
    an in-progress press when a child animates its width and triggers a
    relayout.  A plain layout container has no such rebuild.
    """
    return Column(
        gap=18,
        cross_alignment="start",
        children=[_section_title(title), HorizontalDivider(), *rows],
    )


def _days_group(style) -> StandardButtonGroup:
    return StandardButtonGroup(
        [GroupButton("Day"), GroupButton("Week"), GroupButton("Month")],
        style=style,
    )


def _icon_group(style) -> StandardButtonGroup:
    return StandardButtonGroup(
        [GroupButton(icon=icon) for icon in _ALIGN_ICONS],
        style=style,
    )


def _size_group(size: ButtonSize) -> StandardButtonGroup:
    return StandardButtonGroup(
        [GroupButton(icon=icon, label=label) for icon, label in _SIZE_CONTENT[size]],
        style=StandardButtonGroupStyle.filled(size),
    )


# ---------------------------------------------------------------------------
# Showcase
# ---------------------------------------------------------------------------


def main(png_path: str = "") -> None:
    standard = _section(
        "Standard",
        _labeled("Filled", _days_group(StandardButtonGroupStyle.filled())),
        _labeled("Tonal", _icon_group(StandardButtonGroupStyle.tonal())),
        _labeled("Outlined", _days_group(StandardButtonGroupStyle.outlined())),
    )

    connected = _section(
        "Connected",
        _labeled(
            "Single select",
            ConnectedButtonGroup(
                [GroupButton("Small"), GroupButton("Medium"), GroupButton("Large")],
                style=ConnectedButtonGroupStyle.outlined(),
            ),
        ),
    )

    sizes = _section(
        "Sizes",
        *[_labeled(size.upper(), _size_group(size)) for size in _SIZES],
    )

    page = Row(
        gap=24,
        cross_alignment="start",
        children=[
            Column(gap=24, cross_alignment="start", children=[standard, connected]),
            sizes,
        ],
    )

    content = Container(padding=32, child=page)
    app = App(
        content=content,
        title="ButtonGroup",
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
