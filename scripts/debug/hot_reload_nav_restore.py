"""Hot reload demo: a declarative navigation stack that survives a save (#378).

Run with hot reload::

    python -m nuiitivet.dev run scripts/debug/hot_reload_nav_restore.py

Navigate a few screens deep (click "Open next"), then edit ``build()`` below —
tweak a label, a color, the padding — and save. The UI updates in place and you
**stay on the deep screen**: the intent stack is snapshotted and replayed onto
the rebuilt navigator across the reload, instead of collapsing back to Home. The
per-screen ``Observable`` counter is restored too, so the whole screen state
survives.

Everything is driven by *intents* against a route table, which is the restorable
navigation style. An imperative ``Navigator.root().push(SomeScreen())`` would be
opaque and reset on reload — see the "Non-goals" in the issue.

Bridge-drive it without pixel coordinates (keys are stable identifiers)::

    python -m nuiitivet.dev click --key open-next     # go one screen deeper
    python -m nuiitivet.dev click --key bump          # increment this screen's counter
    python -m nuiitivet.dev describe-tree             # inspect depth + state

``main`` also accepts a ``png`` path so the sample harness can render it offscreen.
"""

from __future__ import annotations

from dataclasses import dataclass

import nuiitivet.material as nv


@dataclass(frozen=True)
class ScreenIntent:
    """Restorable route descriptor: which screen, at what depth."""

    depth: int


class Screen(nv.ComposableWidget):
    """One navigation screen with a local, observable counter."""

    def __init__(self, depth: int) -> None:
        super().__init__()
        self.depth = depth
        self.count = nv.Observable(0)

    def _open_next(self) -> None:
        nv.Navigator.root().push(ScreenIntent(depth=self.depth + 1))

    def _go_back(self) -> None:
        nv.Navigator.root().pop()

    def _bump(self) -> None:
        self.count.value += 1

    def build(self) -> nv.Widget:
        actions: list[nv.Widget] = [
            nv.Button(
                "Open next",
                on_click=lambda: self._open_next(),
                style=nv.ButtonStyle.filled(),
            ).modifier(nv.keyed("open-next")),
            nv.Button(
                "Bump counter",
                on_click=lambda: self._bump(),
                style=nv.ButtonStyle.tonal(),
            ).modifier(nv.keyed("bump")),
        ]
        if self.depth > 0:
            actions.append(
                nv.Button(
                    "Back",
                    on_click=lambda: self._go_back(),
                    style=nv.ButtonStyle.outlined(),
                ).modifier(nv.keyed("back"))
            )

        return nv.Box(
            background_color="#F5F7FF",
            width=nv.Sizing.weight(1),
            height=nv.Sizing.weight(1),
            child=nv.Column(
                padding=24,
                gap=12,
                children=[
                    nv.Text(f"Screen depth {self.depth}").modifier(nv.keyed("screen-title")),
                    nv.Text(self.count.map(lambda n: f"Counter: {n}")),
                    *actions,
                ],
            ),
        )


def build_root() -> nv.Widget:
    # A root *factory*: the dev runner re-invokes this on every save. The intent
    # route table reconstructs each Screen from its ScreenIntent, which is what
    # makes the pushed stack replayable after a reload.
    return nv.Navigator.intents(
        initial_route=ScreenIntent(depth=0),
        routes={ScreenIntent: lambda intent: Screen(depth=intent.depth)},
    )


def main(png: str = "") -> None:
    app = nv.App(
        content=build_root,
        title="Hot Reload: navigation restore",
        width=420,
        height=320,
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
