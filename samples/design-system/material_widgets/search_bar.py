"""Material Widgets - SearchBar and DockedSearchBar.

``width`` names the *box* the bar is inset into, not the bar itself: the bar is
drawn 24dp inside it, animating to 12dp while focused. Click a bar to watch it
grow into its margins.

The docked bar shows the ordinary desktop loop: typing opens the container,
Enter closes it and the results land on the page, and typing again brings the
container back.
"""

from __future__ import annotations

import nuiitivet.material as nv

_FRUIT = ["apple", "apricot", "avocado", "banana", "blackberry", "blueberry"]


def build_root() -> nv.Widget:
    query: nv.Observable[str] = nv.Observable("")
    submitted: nv.Observable[str] = nv.Observable("")
    matches = query.map(lambda q: [f for f in _FRUIT if q in f] if q else _FRUIT)
    results = submitted.map(lambda q: f"Results for '{q}'" if q else "Nothing searched yet")

    return nv.Container(
        padding=24,
        child=nv.Column(
            gap=24,
            cross_alignment="start",
            children=[
                nv.Text("SearchBar"),
                nv.SearchBar(
                    placeholder="Search fruit",
                    on_submit=lambda value: print(f"Submitted: {value}"),
                    width=440,
                ),
                nv.Text("DockedSearchBar"),
                nv.DockedSearchBar(
                    query,
                    placeholder="Search fruit",
                    trailing_icon="close",
                    on_tap_trailing_icon=lambda: setattr(query, "value", ""),
                    # One slot: put whatever the query calls for in it. Here it
                    # is suggestions, driven by the app's own observable.
                    content=nv.Container(
                        padding=8,
                        child=nv.Column(
                            gap=4,
                            cross_alignment="start",
                            children=[
                                nv.ForEach(matches, lambda item, index: nv.Text(item)),
                            ],
                        ),
                    ),
                    # Enter closes the container (the default) and the page
                    # below renders the results.
                    on_submit=lambda value: setattr(submitted, "value", value),
                    width=440,
                ),
                nv.Text(results),
            ],
        ),
    )


def main(png_path: str = "") -> None:
    # A factory root, not an instance: that is what keeps hot reload working
    # under `python -m nuiitivet.dev`.
    app = nv.App(
        content=build_root,
        title="SearchBar",
        width=520,
        height=360,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
