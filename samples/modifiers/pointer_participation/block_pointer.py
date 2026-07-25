"""block_pointer(): catch the whole surface — even transparent areas.

Posture — own: catches everywhere (incl. transparent) · child: reachable · behind: blocked.

Shares the common demo layout (see defer_pointer.py): a clickable "behind"
canvas, a full-size "self" layer carrying the modifier, and a "child" button
panel inside it. The toggle flips the modifier between ON and the ``auto``
default; observe through "behind" and "child".

Necessary deviation from the other three demos: **the self layer is transparent
(no background)**. block_pointer's whole point is catching *unpainted* pixels; a
painted self would already be caught by ``auto``, so ON and OFF would look
identical. With a transparent self the toggle is meaningful:

    - Self area (transparent), ON  -> nothing: block catches it, "behind" blocked
    - Child button                 -> "child"  (block still descends into children)
    - Self area (transparent), OFF -> "behind": auto lets the unpainted area pass
      through, so the canvas is reached.
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


class BlockPointerDemo(nv.ComposableWidget):
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
                "block_pointer ON — self catches everywhere; 'behind' is blocked"
                if a
                else "auto (default) — the transparent self lets clicks reach 'behind'"
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

        # self layer: TRANSPARENT (no background) — the necessary deviation, so
        # that block's "catch even unpainted areas" differs from `auto`. No own
        # `clickable`: block catches at the box level, so ON is a silent swallow,
        # observed via behind (blocked) vs child (still reachable).
        self_layer = nv.Stack(
            width="100%",
            height="100%",
            children=[
                nv.Container(width="100%", height="100%", alignment="bottom-center", padding=18, child=child_panel),
                _label("self", "top-left", nv.ColorRole.ON_SURFACE),
            ],
        ).modifier(nv.block_pointer(self.active))

        stack = nv.Stack(
            width=360,
            height=320,
            children=[behind, self_layer],
        ).modifier(nv.corner_radius(16) | nv.clip())

        return nv.Column(
            children=[
                nv.Button("Toggle (block ↔ auto)", on_click=self._toggle),
                nv.Text(status),
                stack,
                nv.Text(self.log),
            ],
            gap=12,
            padding=16,
        )


def main(png: str = ""):
    app = nv.App(content=BlockPointerDemo(), title="block_pointer Modifier", width=500)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
