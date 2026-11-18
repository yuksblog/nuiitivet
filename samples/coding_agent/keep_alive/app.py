"""Hot reload demo: an object made in main() lives across saves.

Run with hot reload::

    python -m nuiitivet.dev run samples/coding_agent/keep_alive/app.py

``main`` loads the catalog once, which takes a second. Edit this file and save:
the screen changes and the "loaded at" time stays. Edit the body of
``Catalog.search`` in ``catalog.py`` and save: the next search runs the new
code on the same catalog.

``main`` also accepts a ``png`` path so the sample harness can render it offscreen.
"""

import nuiitivet.material as nv
from catalog import Catalog


class CatalogScreen(nv.ComposableWidget):
    """A search box over the catalog it was given."""

    def __init__(self, catalog: Catalog) -> None:
        super().__init__()
        self.catalog = catalog
        self.word = nv.State("")

    def build(self) -> nv.Widget:
        return nv.Column(
            padding=24,
            gap=12,
            children=[
                nv.Text(f"Catalog loaded at {self.catalog.loaded_at}", key="loaded"),
                nv.TextField(self.word, label="Search", key="search"),
                nv.Text(self.word.map(lambda word: ", ".join(self.catalog.search(word))), key="found"),
            ],
        )


def main(png: str = "") -> None:
    catalog = Catalog()  # loaded once
    app = nv.App(
        nv.Window(
            content=lambda: CatalogScreen(catalog),
            title="Hot Reload: keep alive",
            width=420,
            height=260,
        )
    )
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
