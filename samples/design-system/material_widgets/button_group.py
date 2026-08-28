"""Material Widgets - ButtonGroup showcase.

Showcases the Material 3 button-group family: standard variants
(filled / tonal / outlined), the per-size pressed-width interaction, and the
connected single-select group.
"""

from __future__ import annotations

import nuiitivet.material as nv

# Icons reused for the tonal icon-only group.
_ALIGN_ICONS = ("format_align_left", "format_align_center", "format_align_right")

# Size scale content: each row varies icons and label presence (icon-only,
# label-only, icon + label).  Content-fit widths keep the pressed-width
# interaction working and avoid narrow vertical pills at large sizes.
_SIZES: tuple[nv.ButtonSize, ...] = ("xs", "s", "m", "l", "xl")

_SIZE_CONTENT: dict[nv.ButtonSize, list[tuple[str | None, str | None]]] = {
    "xs": [("format_align_left", None), ("format_align_center", None), ("format_align_right", None)],
    "s": [(None, "Day"), (None, "Week"), (None, "Month")],
    "m": [("calendar_today", "Day"), ("event", "Week"), ("schedule", "Month")],
    "l": [("call", "Call"), ("email", "Mail"), ("map", "Map")],
    "xl": [("favorite", "Like"), ("bolt", "Boost"), ("movie", "Watch")],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _section_title(text: str) -> nv.Text:
    return nv.Text(text, style=nv.TextStyle(color=nv.ColorRole.ON_SURFACE), type_scale=nv.TypeScaleToken.from_size(18))


def _caption(text: str) -> nv.Text:
    return nv.Text(
        text,
        style=nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT),
        type_scale=nv.TypeScaleToken.from_size(12),
    )


def _labeled(caption: str, widget) -> nv.Column:
    """A small caption stacked above a button group."""
    return nv.Column(gap=8, cross_alignment="start", children=[_caption(caption), widget])


def _section(title: str, *rows) -> nv.Column:
    """A titled section grouping related examples.

    A plain ``Column`` (not ``Card``): ``Card`` is a scoped ``WidgetBuilder``
    that rebuilds — and unmounts — its subtree on every measure, which cancels
    an in-progress press when a child animates its width and triggers a
    relayout.  A plain layout container has no such rebuild.
    """
    return nv.Column(
        gap=18,
        cross_alignment="start",
        children=[_section_title(title), nv.HorizontalDivider(), *rows],
    )


def _days_group(style) -> nv.StandardButtonGroup:
    return nv.StandardButtonGroup(
        [nv.GroupButton("Day"), nv.GroupButton("Week"), nv.GroupButton("Month")],
        style=style,
    )


def _icon_group(style) -> nv.StandardButtonGroup:
    return nv.StandardButtonGroup(
        [nv.GroupButton(icon=icon) for icon in _ALIGN_ICONS],
        style=style,
    )


def _size_group(size: nv.ButtonSize) -> nv.StandardButtonGroup:
    return nv.StandardButtonGroup(
        [nv.GroupButton(icon=icon, label=label) for icon, label in _SIZE_CONTENT[size]],
        style=nv.StandardButtonGroupStyle.filled(size),
    )


# ---------------------------------------------------------------------------
# Showcase
# ---------------------------------------------------------------------------


def main(png_path: str = "") -> None:
    standard = _section(
        "Standard",
        _labeled("Filled", _days_group(nv.StandardButtonGroupStyle.filled())),
        _labeled("Tonal", _icon_group(nv.StandardButtonGroupStyle.tonal())),
        _labeled("Outlined", _days_group(nv.StandardButtonGroupStyle.outlined())),
    )

    connected = _section(
        "Connected",
        _labeled(
            "Single select",
            nv.ConnectedButtonGroup(
                [nv.GroupButton("Small"), nv.GroupButton("Medium"), nv.GroupButton("Large")],
                style=nv.ConnectedButtonGroupStyle.outlined(),
            ),
        ),
    )

    sizes = _section(
        "Sizes",
        *[_labeled(size.upper(), _size_group(size)) for size in _SIZES],
    )

    page = nv.Row(
        gap=24,
        cross_alignment="start",
        children=[
            nv.Column(gap=24, cross_alignment="start", children=[standard, connected]),
            sizes,
        ],
    )

    content = nv.Container(padding=32, child=page)
    app = nv.App(nv.Window(content=content, title="ButtonGroup"))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
