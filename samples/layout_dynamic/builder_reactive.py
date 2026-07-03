"""Dynamic list generation: reactive builder() with an observable.

Passing an observable as ``items`` makes the layout regenerate its children
automatically whenever the collection changes. Only the affected regions are
invalidated, not the whole layout.

Click "Add tag" to append an item and watch the Flow regenerate.
"""

import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class TagListApp(ComposableWidget):
    """A Flow whose cards are driven by an observable list of tags."""

    def __init__(self) -> None:
        super().__init__()
        self.tags = nv.Observable(["Python", "UI"])
        self._counter = 0

    def add(self) -> None:
        # Reassigning .value pushes the change; the Flow regenerates its cards.
        self._counter += 1
        self.tags.value = [*self.tags.value, f"Tag {self._counter}"]

    def build(self) -> Widget:
        return nv.Column(
            padding=16,
            gap=12,
            children=[
                nv.Flow.builder(
                    self.tags,
                    lambda tag, index: md.Card(md.Text(tag, padding=8), style=md.CardStyle.outlined()),
                    main_gap=8,
                    cross_gap=8,
                    width=300,
                ),
                md.Button("Add tag", on_click=lambda: self.add(), style=md.ButtonStyle.filled()),
            ],
        )


def main(png: str = ""):
    widget = TagListApp()
    root = nv.Container(alignment="center", child=widget)

    app = md.App(content=root, title="Dynamic List: reactive builder()")
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
