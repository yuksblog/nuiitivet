"""Window-scoped adaptive layout: a responsive navigation rail.

The app installs a root ``Geometry`` provider at the window, so a top-level panel
reflows on the *window* width with no explicit wrapper. Here a ``NavigationRail``
stays compact (labels below icons) on a narrow window and expands (labels beside
icons) on a wide one — the classic responsive-navigation pattern. Resize the
window across 700px to see it switch.
"""

import nuiitivet.material as nv

_EXPAND_THRESHOLD = 700


class ResponsiveScaffold(nv.ComposableWidget):
    """Navigation rail (left) + content card (right); rail expands when wide."""

    def on_mount(self) -> None:
        # ``Geometry.of`` needs a mounted context (an ancestor chain), so the
        # bound values are derived here — not in ``__init__``, where this widget
        # has no ancestors yet. ``build()`` then just references them.
        size = nv.Geometry.of(self).size
        # ``NavigationRail.expanded`` is two-way (the menu button can toggle it),
        # so it needs a *mutable* Observable — a read-only ``.map`` won't do.
        # Mirror the size-derived flag into a plain Observable and keep it synced.
        self._expanded = nv.Observable(size.value.width >= _EXPAND_THRESHOLD)
        self._expanded_sub = size.subscribe(
            lambda s: setattr(self._expanded, "value", s.width >= _EXPAND_THRESHOLD)
        )
        # A plain read-only display value can bind straight from ``.map``.
        self._hint = size.map(
            lambda s: f"window width = {s.width}px — rail "
            + ("expanded (labels beside icons)" if s.width >= _EXPAND_THRESHOLD else "compact (labels below icons)")
        )
        super().on_mount()

    def on_unmount(self) -> None:
        self._expanded_sub.dispose()
        super().on_unmount()

    def build(self) -> nv.Widget:
        rail = nv.NavigationRail(
            children=[
                nv.RailItem(icon="home", label="Home"),
                nv.RailItem(icon="search", label="Search"),
                nv.RailItem(icon="library_books", label="Library"),
                nv.RailItem(icon="settings", label="Settings"),
            ],
            index=nv.Observable(0),
            # ``expanded`` is a mutable Observable written from two sources: the
            # window-size subscription (see on_mount) and the menu button. Both
            # work — resize re-syncs it, and between resizes the menu toggles it.
            expanded=self._expanded,
            width=220,
        )
        card = nv.Card(
            nv.Column(
                [
                    nv.Text("Responsive navigation"),
                    nv.Text(self._hint),
                ],
                gap=12,
                padding=24,
                cross_alignment="start",
            ),
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
        )
        return nv.Row([rail, card], gap=16, width=nv.Sizing.flex(1), height=nv.Sizing.flex(1))


def build_root() -> nv.Widget:
    """Factory root (uncalled), so `python -m nuiitivet.dev` can hot-reload it."""
    return nv.Container(ResponsiveScaffold(), padding=16, width=nv.Sizing.flex(1), height=nv.Sizing.flex(1))


def main(png: str = ""):
    app = nv.App(content=build_root, width=560, height=420, title="Window-scoped Adaptive Layout")
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
