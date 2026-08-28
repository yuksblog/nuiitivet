"""defer_pointer(): a decorated overlay yields its own surface to what's behind.

Posture — own: yields · child: reachable · behind: reachable.

All four pointer-participation demos share one layout so their behaviours line
up for comparison:

    - "behind" — a clickable canvas, label at the centre
    - "self"   — a full-size translucent layer carrying the modifier (top-left
                 label). It paints a tint, so under ``auto`` it would catch.
    - "child"  — a small panel with a button inside the self layer (top-left label)

The toggle flips the modifier between ON and the ``auto`` default. Observe only
through "behind" and "child": there is deliberately no handler on the self
surface — for defer that would be self-contradictory (asking one surface both to
catch and to yield), so the own-yield is proven by the behind layer being
reached.

What each click checks:
    - Centre / self area, ON  -> "behind"  (self yields, so the canvas is reached)
    - Child button            -> "child"   (child stays reachable)
    - Centre / self area, OFF -> nothing: the painted overlay (auto) catches and
      swallows the click before it reaches the canvas.
"""

from __future__ import annotations

import nuiitivet.material as nv


def _label(text: str, align: str, color) -> nv.Container:
    """A full-size, hit-transparent overlay that pins a small label at *align*."""
    return nv.Container(
        width="wt",
        height="wt",
        alignment=align,
        padding=8,
        child=nv.Text(text, type_scale=nv.TypeScale.LABEL_SMALL, style=nv.TextStyle(color=color)),
    )


class DeferPointerDemo(nv.ComposableWidget):
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
                "defer_pointer ON — self yields; the self area reaches 'behind'"
                if a
                else "auto (default) — the painted self catches and swallows the click"
            )
        )

        behind = nv.Container(
            width="wt",
            height="wt",
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

        # self layer: a translucent painted overlay. No `clickable` here — asking
        # a deferring surface to also catch is contradictory (see module docstring).
        self_layer = nv.Stack(
            width="wt",
            height="wt",
            children=[
                nv.Container(width="wt", height="wt", alignment="bottom-center", padding=18, child=child_panel),
                _label("self", "top-left", nv.ColorRole.ON_SURFACE),
            ],
        ).modifier(nv.background("#2196F344") | nv.defer_pointer(self.active))

        stack = nv.Stack(
            width=360,
            height=320,
            children=[behind, self_layer],
        ).modifier(nv.corner_radius(16) | nv.clip())

        return nv.Column(
            children=[
                nv.Button("Toggle (defer ↔ auto)", on_click=self._toggle),
                nv.Text(status),
                stack,
                nv.Text(self.log),
            ],
            gap=12,
            padding=16,
        )


def main(png: str = ""):
    app = nv.App(nv.Window(content=DeferPointerDemo(), title="defer_pointer Modifier", width=500))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
