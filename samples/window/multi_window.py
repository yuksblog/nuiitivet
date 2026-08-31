"""Multiple windows with ``nv.Window``.

A ``Window`` is constructed as a model and shown with ``open()``; ``close()``
destroys it — one object is one window lifetime. State that must survive a
window lives in app-layer Observables passed into each window's content.
``parent=`` makes a child window that closes with its opener; ``modal=True``
additionally blocks input to the parent chain while the child is open.

Interactions:
    - "Open palette" opens a tool palette window; picking a swatch updates
      the readout in the main window. Close the palette and reopen it — the
      picked color survives, because it lives in the app layer.
    - "Open settings…" opens a window modal to the main one: main-window
      clicks are ignored until it is closed.
"""

from __future__ import annotations

import nuiitivet.material as nv

_MUTED = nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT)
_SWATCHES = ("#6750A4", "#B3261E", "#2E7D32", "#1D6FA3")


class AppState:
    """App-layer state, shared by every window's content."""

    def __init__(self) -> None:
        self.color = nv.Observable(_SWATCHES[0])
        self.log = nv.Observable("Pick a color from the palette.")


class Palette(nv.ComposableWidget):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state

    def _pick(self, color: str) -> None:
        self.state.color.value = color
        self.state.log.value = f"Picked {color}."

    def build(self):
        return nv.Column(
            children=[
                nv.Text("Palette", type_scale=nv.TypeScale.TITLE_SMALL),
                nv.Row(
                    children=[
                        nv.Button(color, on_click=lambda color=color: self._pick(color))
                        for color in _SWATCHES[:2]
                    ],
                    gap=8,
                ),
                nv.Row(
                    children=[
                        nv.Button(color, on_click=lambda color=color: self._pick(color))
                        for color in _SWATCHES[2:]
                    ],
                    gap=8,
                ),
            ],
            gap=12,
            padding=16,
        )


class Settings(nv.ComposableWidget):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state

    def _done(self) -> None:
        self.state.log.value = "Settings closed."
        nv.Window.of(self).close()

    def build(self):
        return nv.Column(
            children=[
                nv.Text("Settings", type_scale=nv.TypeScale.TITLE_SMALL),
                nv.Text("Modal: the main window ignores input while this is open.", style=_MUTED),
                nv.Button("Done", on_click=self._done, key="settings-done"),
            ],
            gap=12,
            padding=16,
        )


class Main(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.state = AppState()

    def _open_palette(self) -> None:
        # A closed Window is finished; each click constructs a fresh one. The
        # picked color survives anyway — it lives in self.state, not in the
        # palette window.
        nv.Window(
            content=lambda: Palette(self.state),
            title="Palette",
            width=280,
            height=170,
        ).open()

    def _open_settings(self) -> None:
        nv.Window(
            content=lambda: Settings(self.state),
            title="Settings",
            width=340,
            height=180,
            parent=nv.Window.of(self),
            modal=True,
        ).open()

    def build(self):
        return nv.Column(
            children=[
                nv.Text("Multiple windows", type_scale=nv.TypeScale.TITLE_MEDIUM),
                nv.Text(self.state.color.map(lambda c: f"color: {c}"), style=_MUTED),
                nv.Text(self.state.log, style=_MUTED),
                nv.Row(
                    children=[
                        nv.Button("Open palette", on_click=self._open_palette, key="open-palette"),
                        nv.Button("Open settings…", on_click=self._open_settings, key="open-settings"),
                    ],
                    gap=8,
                ),
            ],
            gap=12,
            padding=24,
        )


def main(png: str = ""):
    app = nv.App(nv.Window(content=Main, title="multi_window", width=520, height=240))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
