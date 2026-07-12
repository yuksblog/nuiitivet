"""Raw pointer handling with ``pointer_input()``: an event inspector.

Higher-level modifiers (``clickable``, ``hoverable``) hand you an interpreted
gesture. ``pointer_input`` hands you the raw stream instead — press, move,
release, enter, leave and scroll — with widget-local coordinates, the buttons
currently held and the active modifier keys. This sample shows what arrives, so
the stream is visible.

Interactions:
    - Move, press and drag over the panel with any mouse button.
    - Hold Shift / Ctrl / Alt while interacting to see the modifier mask.
    - Scroll over the panel.
    - ``capture=True`` keeps a drag reporting even after the pointer leaves the
      panel, so the release lands here too.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, List, Tuple

import nuiitivet.material as nv

_PANEL_W = 320
_PANEL_H = 220
_LOG_LINES = 6

_LABEL = nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT)
_MUTED = nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT)

_BUTTONS = [(nv.BUTTON_LEFT, "left"), (nv.BUTTON_MIDDLE, "middle"), (nv.BUTTON_RIGHT, "right")]
_MODIFIERS = [(nv.MOD_SHIFT, "shift"), (nv.MOD_CTRL, "ctrl"), (nv.MOD_ALT, "alt"), (nv.MOD_META, "meta")]


def _names(mask: int, table: List[Tuple[int, str]]) -> str:
    """Render a bit mask as a readable list of names."""
    hits = [name for bit, name in table if mask & bit]
    return " + ".join(hits) if hits else "—"


class PointerInspector(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self._log: Deque[str] = deque(maxlen=_LOG_LINES)
        self.event = nv.Observable("—")
        self.local = nv.Observable("—")
        self.screen = nv.Observable("—")
        self.buttons = nv.Observable("—")
        self.modifiers = nv.Observable("—")
        self.log = nv.Observable("Waiting for the pointer…")

    def _record(self, kind: str, e: nv.PointerEvent, detail: str = "") -> None:
        self.event.value = f"{kind}{f'  ({detail})' if detail else ''}"
        self.local.value = f"{e.local_x:.0f}, {e.local_y:.0f}"
        self.screen.value = f"{e.x:.0f}, {e.y:.0f}"
        self.buttons.value = _names(e.buttons, _BUTTONS)
        self.modifiers.value = _names(e.modifier_keys, _MODIFIERS)

        self._log.appendleft(f"{kind}  ·  {e.local_x:.0f}, {e.local_y:.0f}{f'  ·  {detail}' if detail else ''}")
        self.log.value = "\n".join(self._log)

    def _on_enter(self, e: nv.PointerEvent) -> None:
        self._record("enter", e)

    def _on_leave(self, e: nv.PointerEvent) -> None:
        self._record("leave", e)

    def _on_press(self, e: nv.PointerEvent) -> None:
        self._record("press", e, _names(e.button or 0, _BUTTONS))

    def _on_move(self, e: nv.PointerEvent) -> None:
        # Fires while hovering and while dragging; `buttons` tells the two apart.
        self._record("drag" if e.buttons else "move", e)

    def _on_release(self, e: nv.PointerEvent) -> None:
        self._record("release", e, _names(e.button or 0, _BUTTONS))

    def _on_scroll(self, e: nv.PointerEvent) -> None:
        self._record("scroll", e, f"{e.scroll_x:+.0f}, {e.scroll_y:+.0f}")

    def _field(self, label: str, value: nv.Observable) -> nv.Row:
        return nv.Row(
            children=[
                nv.Text(label, style=_LABEL, type_scale=nv.TypeScale.LABEL_MEDIUM, width=76),
                nv.Text(value, type_scale=nv.TypeScale.BODY_MEDIUM),
            ],
            gap=8,
            cross_alignment="center",
        )

    def _panel(self) -> nv.Container:
        return nv.Container(
            width=_PANEL_W,
            height=_PANEL_H,
            alignment="center",
            child=nv.Text("Move, drag or scroll here", style=_MUTED),
        ).modifier(
            nv.background(nv.ColorRole.SURFACE_CONTAINER_HIGH)
            | nv.corner_radius(12)
            | nv.pointer_input(
                on_press=self._on_press,
                on_move=self._on_move,
                on_release=self._on_release,
                on_enter=self._on_enter,
                on_leave=self._on_leave,
                on_scroll=self._on_scroll,
                capture=True,
            )
        )

    def build(self):
        readout = nv.Column(
            children=[
                self._field("Event", self.event),
                self._field("Local", self.local),
                self._field("Screen", self.screen),
                self._field("Buttons", self.buttons),
                self._field("Modifiers", self.modifiers),
            ],
            gap=6,
        )

        history = nv.Column(
            children=[
                nv.Text("Recent", style=_LABEL, type_scale=nv.TypeScale.LABEL_MEDIUM),
                nv.Text(self.log, style=_MUTED, type_scale=nv.TypeScale.BODY_SMALL, max_lines=_LOG_LINES),
            ],
            gap=6,
        )

        return nv.Row(
            children=[self._panel(), nv.Column(children=[readout, history], gap=20)],
            gap=24,
            padding=20,
        )


def main(png: str = ""):
    app = nv.App(content=PointerInspector(), title="pointer_input — event inspector", width=550)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
