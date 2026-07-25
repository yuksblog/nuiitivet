"""absorb_pointer(): a composite behaves as one solid, non-interactive slab.

Posture — own: catches · child: blocked · behind: blocked.

Shares the common demo layout (see defer_pointer.py): a clickable "behind"
canvas, a full-size translucent "self" layer carrying the modifier, and a
"child" button panel inside it. The toggle flips the modifier between ON and the
``auto`` default; observe through "behind" and "child".

While ON the self surface catches and does not descend, so the whole subtree is
one dead slab.

The toggle resets the log, so each ON/OFF state starts from a clean "…" line —
that makes the "nothing happens" case (a click absorbed with no log) observable
every time you flip the toggle, not just once.

What each click checks:
    - Anywhere on the card, ON  -> nothing: own catches, child + behind blocked;
      the click is absorbed (the log stays on its reset "…" line).
    - Child button, OFF -> "child"  (auto descends; the button works again)
    - Self area,    OFF -> nothing: the painted self (auto) catches and swallows.

behind stays blocked in both states — the self layer covers it — so "behind"
never fires here; the label just marks the layer being sealed off.
"""

from __future__ import annotations

import nuiitivet.material as nv


def _label(text: str, align: str, color) -> nv.Container:
    """A full-size, hit-transparent overlay that pins a small label at *align*."""
    return nv.Container(
        width="100%",
        height="100%",
        alignment=align,
        padding=8,
        child=nv.Text(text, type_scale=nv.TypeScale.LABEL_SMALL, style=nv.TextStyle(color=color)),
    )


class AbsorbPointerDemo(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.active = nv.Observable(True)
        self.log = nv.Observable("Click the stack…")

    def _hit(self, who: str) -> None:
        self.log.value = who

    def _toggle(self) -> None:
        self.active.value = not self.active.value
        self.log.value = "Click the stack…"  # reset so a no-op is visible each flip

    def build(self):
        status = self.active.map(
            lambda a: (
                "absorb_pointer ON — self catches, children blocked (dead slab)"
                if a
                else "auto (default) — the painted self catches, but children work"
            )
        )

        behind = nv.Container(
            width="100%",
            height="100%",
            alignment="center",
            child=nv.Text("behind", style=nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT)),
        ).modifier(
            nv.background(nv.ColorRole.SURFACE_CONTAINER_HIGH) | nv.clickable(on_click=lambda: self._hit("behind"))
        )

        child_panel = nv.Container(
            width=200,
            padding=12,
            child=nv.Column(
                children=[
                    nv.Text(
                        "child",
                        type_scale=nv.TypeScale.LABEL_SMALL,
                        style=nv.TextStyle(color=nv.ColorRole.ON_PRIMARY_CONTAINER),
                    ),
                    nv.Button("child action", on_click=lambda: self._hit("child")),
                ],
                gap=14,
            ),
        ).modifier(nv.background(nv.ColorRole.PRIMARY_CONTAINER) | nv.corner_radius(12))

        # self layer: a translucent painted card. No own `clickable` — absorb
        # would catch it at the box level anyway (the click never descends), so
        # its ON behaviour is a silent swallow, observed via child + behind.
        self_layer = nv.Stack(
            width="100%",
            height="100%",
            children=[
                nv.Container(width="100%", height="100%", alignment="bottom-center", padding=18, child=child_panel),
                _label("self", "top-left", nv.ColorRole.ON_SURFACE),
            ],
        ).modifier(nv.background("#2196F344") | nv.absorb_pointer(self.active))

        stack = nv.Stack(
            width=360,
            height=320,
            children=[behind, self_layer],
        ).modifier(nv.corner_radius(16) | nv.clip())

        return nv.Column(
            children=[
                nv.Button("Toggle (absorb ↔ auto)", on_click=self._toggle),
                nv.Text(status),
                stack,
                nv.Text(self.log),
            ],
            gap=12,
            padding=16,
        )


def main(png: str = ""):
    app = nv.App(content=AbsorbPointerDemo(), title="absorb_pointer Modifier", width=500)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
