"""ButtonGroup demo - StandardButtonGroup and ConnectedButtonGroup.

This demo shows:
- StandardButtonGroup: independent toggle segments with adjacent corner animation
- ConnectedButtonGroup single-select: radio-style option selector
- ConnectedButtonGroup multi-select: checkbox-style option selector
- Variant comparison: filled, tonal, outlined
"""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.widgets.box import Box
from nuiitivet.material import Text
from nuiitivet.material.app import MaterialApp
from nuiitivet.material.button_group import (
    GroupButton,
    ConnectedButtonGroup,
    StandardButtonGroup,
)
from nuiitivet.material.styles.button_group_style import (
    StandardButtonGroupStyle,
    ConnectedButtonGroupStyle,
)
from nuiitivet.observable import Observable


def _heading(text: str) -> Text:
    return Text(text, padding=(0, 16, 0, 6))


def _subheading(text: str) -> Text:
    return Text(text, padding=(0, 0, 0, 4))


# ---------------------------------------------------------------------------
# Demo state
# ---------------------------------------------------------------------------

selected_view = Observable("day")
log_lines: list[str] = []
log_obs: Observable[str] = Observable("(no events yet)")

_MAX_LOG = 6


def _log(msg: str) -> None:
    log_lines.append(msg)
    last = log_lines[-_MAX_LOG:]
    log_obs.value = "\n".join(last)


# ---------------------------------------------------------------------------
# StandardButtonGroup sections
# ---------------------------------------------------------------------------


def _make_standard_filled() -> StandardButtonGroup:
    def _cb(label: str):
        def _inner(_selected: bool) -> None:
            _log(f"standard/filled clicked: {label}")

        return _inner

    return StandardButtonGroup(
        [
            GroupButton("Day", on_change=_cb("Day")),
            GroupButton("Week", on_change=_cb("Week")),
            GroupButton("Month", on_change=_cb("Month")),
        ],
    )


def _make_standard_tonal_with_icons() -> StandardButtonGroup:
    def _cb(label: str):
        def _inner(_selected: bool) -> None:
            _log(f"standard/tonal clicked: {label}")

        return _inner

    return StandardButtonGroup(
        [
            GroupButton(icon="format_align_left", on_change=_cb("left")),
            GroupButton(icon="format_align_center", on_change=_cb("center")),
            GroupButton(icon="format_align_right", on_change=_cb("right")),
            GroupButton(icon="format_align_justify", on_change=_cb("justify")),
        ],
        style=StandardButtonGroupStyle.tonal(),
    )


def _make_standard_outlined() -> StandardButtonGroup:
    def _cb(label: str):
        def _inner(_selected: bool) -> None:
            _log(f"standard/outlined clicked: {label}")

        return _inner

    return StandardButtonGroup(
        [
            GroupButton("Bold", icon="format_bold", on_change=_cb("Bold")),
            GroupButton("Italic", icon="format_italic", on_change=_cb("Italic")),
            GroupButton("Underline", icon="format_underlined", on_change=_cb("Underline")),
        ],
        style=StandardButtonGroupStyle.outlined(),
    )


def _make_standard_with_disabled() -> StandardButtonGroup:
    def _cb(label: str):
        def _inner(_selected: bool) -> None:
            _log(f"standard/disabled-demo clicked: {label}")

        return _inner

    return StandardButtonGroup(
        [
            GroupButton("Edit", icon="edit", on_change=_cb("Edit")),
            GroupButton("Copy", icon="content_copy", on_change=_cb("Copy"), disabled=True),
            GroupButton("Share", icon="share", on_change=_cb("Share")),
        ],
    )


# ---------------------------------------------------------------------------
# ConnectedButtonGroup sections
# ---------------------------------------------------------------------------


def _make_connected_single() -> ConnectedButtonGroup:
    def _on_change(indices: list[int]) -> None:
        names = ["List", "Grid", "Map"]
        selected_names = [names[i] for i in indices if i < len(names)]
        _log(f"connected/single selected: {selected_names}")

    return ConnectedButtonGroup(
        [
            GroupButton("List", icon="list", selected=True),
            GroupButton("Grid", icon="grid_view"),
            GroupButton("Map", icon="map"),
        ],
        select_mode="single",
    )


def _make_connected_multi() -> ConnectedButtonGroup:
    def _on_change(indices: list[int]) -> None:
        names = ["Wi-Fi", "BT", "NFC"]
        selected_names = [names[i] for i in indices if i < len(names)]
        _log(f"connected/multi selected: {selected_names}")

    return ConnectedButtonGroup(
        [
            GroupButton("Wi-Fi", icon="wifi"),
            GroupButton("BT", icon="bluetooth", selected=True),
            GroupButton("NFC", icon="nfc"),
        ],
        select_mode="multi",
        style=ConnectedButtonGroupStyle.tonal(),
    )


def _make_connected_outlined_single() -> ConnectedButtonGroup:
    def _on_change(indices: list[int]) -> None:
        sizes = ["S", "M", "L", "XL", "2XL"]
        selected_names = [sizes[i] for i in indices if i < len(sizes)]
        _log(f"connected/outlined selected: {selected_names}")

    return ConnectedButtonGroup(
        [
            GroupButton("S"),
            GroupButton("M", selected=True),
            GroupButton("L"),
            GroupButton("XL"),
            GroupButton("2XL"),
        ],
        select_mode="single",
        style=ConnectedButtonGroupStyle.outlined(),
    )


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------


def main() -> None:
    event_log = Text(log_obs, padding=4)

    content = Column(
        children=[
            _heading("ButtonGroup Demo"),
            # ---- Standard ----
            _subheading("StandardButtonGroup — filled (text labels)"),
            _make_standard_filled(),
            _subheading("StandardButtonGroup — tonal (icon-only)"),
            _make_standard_tonal_with_icons(),
            _subheading("StandardButtonGroup — outlined (icon + label)"),
            _make_standard_outlined(),
            _subheading("StandardButtonGroup — with disabled item"),
            _make_standard_with_disabled(),
            # ---- Connected ----
            _heading("ConnectedButtonGroup"),
            _subheading("Single-select — filled (view switcher)"),
            _make_connected_single(),
            _subheading("Multi-select — tonal (toggles)"),
            _make_connected_multi(),
            _subheading("Single-select — outlined (5 items)"),
            _make_connected_outlined_single(),
            # ---- Event log ----
            _heading("Event Log"),
            Box(
                child=event_log,
                padding=8,
                background_color="#EEEEEE",
            ),
        ],
        gap=8,
        cross_alignment="start",
    )

    root = Box(child=content, padding=24)
    app = MaterialApp(content=root)
    app.run()


if __name__ == "__main__":
    main()
