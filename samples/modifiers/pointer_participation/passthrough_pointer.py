"""passthrough_pointer(): the whole subtree becomes click-through.

Posture — own: none · child: none · behind: reachable.

Shares the common demo layout (see defer_pointer.py): a clickable "behind"
canvas, a full-size translucent "self" layer carrying the modifier, and a
"child" button panel inside it. The toggle flips the modifier between ON and the
``auto`` default; observe through "behind" and "child".

While ON both the self surface and its children are turned off for hit-testing,
so every click falls through to the canvas behind.

What each click checks:
    - Self area / child, ON  -> "behind" (own + child off; the canvas is reached)
    - Child button,     OFF  -> "child"  (auto descends; the button works)
    - Self area,        OFF  -> nothing: the painted self (auto) catches and swallows.
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


class PassthroughPointerDemo(nv.ComposableWidget):
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
                "passthrough_pointer ON — whole subtree passes to 'behind'"
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

        # self layer: a translucent painted "ghost". No own `clickable` — under
        # passthrough it would never fire anyway (the subtree is off), so the
        # ON behaviour is observed via "behind" being reached.
        self_layer = nv.Stack(
            width="100%",
            height="100%",
            children=[
                nv.Container(width="100%", height="100%", alignment="bottom-center", padding=18, child=child_panel),
                _label("self", "top-left", nv.ColorRole.ON_SURFACE),
            ],
        ).modifier(nv.background("#2196F344") | nv.passthrough_pointer(self.active))

        stack = nv.Stack(
            width=360,
            height=320,
            children=[behind, self_layer],
        ).modifier(nv.corner_radius(16) | nv.clip())

        return nv.Column(
            children=[
                nv.Button("Toggle (passthrough ↔ auto)", on_click=self._toggle),
                nv.Text(status),
                stack,
                nv.Text(self.log),
            ],
            gap=12,
            padding=16,
        )


def main(png: str = ""):
    app = nv.App(content=PassthroughPointerDemo(), title="passthrough_pointer Modifier", width=500)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
