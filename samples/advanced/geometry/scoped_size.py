"""Pull/scope adaptive layout: one measured box, many readers.

``on_size_changed`` reports a widget's size back to *that* widget. When the
measurer and the readers are different widgets, the size has to travel down the
tree instead — that is what ``Geometry`` is for.

Here a single ``Geometry`` wraps the content pane, and three widgets at three
different depths read it with ``Geometry.of(self).size``. None of the widgets
between them pass anything down: a card does not know its badge cares about the
pane's width, and dropping the same badge somewhere else makes it read whatever
pane it lands in.
"""

import nuiitivet.material as nv

_WIDE = 600


class SizeClassBadge(nv.ComposableWidget):
    """A leaf, nested arbitrarily deep, that reads the pane it lives in."""

    def on_mount(self) -> None:
        # ``Geometry.of`` resolves through the ancestor chain, so it needs a
        # mounted context — ``__init__`` is too early, the widget has no
        # ancestors yet.
        size = nv.Geometry.of(self).size
        self._label = size.map(lambda s: f"{'expanded' if s.width >= _WIDE else 'compact'} · {s.width}px")
        super().on_mount()

    def build(self) -> nv.Widget:
        # A fixed width so the label does not reflow as the text changes length.
        return nv.Text(self._label, width=150)


class _Section(nv.ComposableWidget):
    """An intermediate widget: it holds a badge but knows nothing about size."""

    def __init__(self, title: str) -> None:
        super().__init__(width="wt")
        self._title = title

    def build(self) -> nv.Widget:
        return nv.Card(
            nv.Row(
                [nv.Text(self._title), nv.Spacer(width="wt"), SizeClassBadge()],
                gap=12,
                padding=16,
                width="wt",
                cross_alignment="center",
            ),
            width="wt",
        )


class ContentPane(nv.ComposableWidget):
    """The pane whose box every badge below it reads."""

    def build(self) -> nv.Widget:
        return nv.Column(
            [
                _Section("Library"),
                _Section("Downloads"),
                _Section("Settings"),
            ],
            gap=16,
            width="wt",
            height="wt",
        )


def build_root() -> nv.Widget:
    """Factory root (uncalled), so `python -m nuiitivet.dev` can hot-reload it."""
    # One filling Geometry defines the scope; every ``Geometry.of`` below it
    # resolves here, because the nearest ancestor provider wins.
    return nv.Container(
        nv.Geometry(ContentPane(), width="wt", height="wt"),
        padding=24,
        width="wt",
        height="wt",
    )


def main(png: str = ""):
    app = nv.App(nv.Window(content=build_root, width=720, height=420, title="Geometry: one box, many readers"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
