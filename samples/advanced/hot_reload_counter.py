"""Hot reload demo: a counter whose state survives a save.

Run with hot reload::

    python -m nuiitivet.dev samples/advanced/hot_reload_counter.py

Then edit ``build()`` below — tweak the padding, the label, the button style —
and save. The UI updates in place and ``count`` keeps its value because it is an
``Observable`` snapshotted and restored across the reload. See
``docs/guide/advanced/hot_reload.md``.

The increment button carries a stable ``key`` so the dev action bridge can drive
it without pixel coordinates (#375)::

    python -m nuiitivet.dev click --key increment-btn   # or: --label increment
    python -m nuiitivet.dev describe-tree                # Count went up

``main`` also accepts a ``png`` path so the sample harness can render it offscreen.
"""

import nuiitivet.material as nv


class Counter(nv.ComposableWidget):
    """A button that increments an observable count."""

    def __init__(self) -> None:
        super().__init__()
        self.count = nv.Observable(0)

    def _increment(self) -> None:
        self.count.value += 1

    def build(self) -> nv.Widget:
        return nv.Column(
            padding=24,
            gap=12,
            children=[
                nv.Text(self.count.map(lambda n: f"Count: {n}")),
                nv.Button(
                    "increment",
                    on_click=lambda: self._increment(),
                    style=nv.ButtonStyle.filled(),
                ).modifier(nv.keyed("increment-btn")),
            ],
        )


def build_root() -> nv.Widget:
    # A root *factory*: the dev runner re-invokes this to rebuild the tree on
    # every save. Pass the function itself to App(content=...), not its result.
    return nv.Container(alignment="center", child=Counter())


def main(png: str = ""):
    app = nv.App(content=build_root, title="Hot Reload: counter", width=360, height=240)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
