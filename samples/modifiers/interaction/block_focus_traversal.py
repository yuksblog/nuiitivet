"""block_focus_traversal(): take a subtree out of the Tab sequence.

The panel below stays visible, laid out and clickable while it is blocked —
only keyboard traversal changes. Tab walks straight from the button above it
to the button below it, and focus held inside the panel is released the moment
the panel becomes blocked.
"""

import nuiitivet.material as nv


class TabStop(nv.ComposableWidget):
    """A focusable box that reports whether it currently holds focus."""

    def __init__(self, label: str):
        super().__init__()
        self.label = label
        self.is_focused = nv.Observable(False)

    def _set_focused(self, focused: bool, source) -> None:
        del source
        self.is_focused.value = focused

    def build(self):
        border_color = self.is_focused.map(lambda f: "#2196F3" if f else "#00000000")
        return nv.Container(
            width=260,
            height=48,
            child=nv.Text(self.label),
            alignment="center",
        ).modifier(
            nv.background("#E0E0E0")
            | nv.corner_radius(8)
            | nv.border(color=border_color, width=2)
            | nv.focusable(on_focus_change=self._set_focused)
        )


class BlockFocusTraversalDemo(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.blocked = nv.Observable(True)

    def _toggle(self) -> None:
        self.blocked.value = not self.blocked.value

    def build(self):
        status = self.blocked.map(
            lambda b: "Panel is BLOCKED - Tab skips it" if b else "Panel is reachable - Tab enters it"
        )

        panel = nv.Column(
            children=[
                nv.Text("Panel"),
                TabStop("panel field 1"),
                TabStop("panel field 2"),
            ],
            gap=8,
            padding=12,
        ).modifier(
            nv.background("#F5F5F5")
            | nv.corner_radius(12)
            # Keyboard traversal only: the panel stays visible and clickable.
            | nv.block_focus_traversal(self.blocked)
        )

        return nv.Column(
            children=[
                nv.Row(
                    children=[
                        nv.Button("Toggle panel", on_click=self._toggle),
                        nv.Text(status),
                    ],
                    gap=12,
                    cross_alignment="center",
                ),
                TabStop("before the panel"),
                panel,
                TabStop("after the panel"),
            ],
            gap=16,
            padding=16,
        )


def main(png: str = ""):
    print("=" * 68)
    print("block_focus_traversal() demo")
    print("  1. Press Tab repeatedly -> focus goes 'before' -> 'after',")
    print("     skipping both fields inside the blocked panel.")
    print("  2. Press 'Toggle panel' -> the panel joins the Tab sequence.")
    print("  3. Focus a panel field, then press 'Toggle panel' again ->")
    print("     the focus ring disappears: focus is released, not stranded.")
    print("=" * 68)

    app = nv.App(nv.Window(content=BlockFocusTraversalDemo(), title="block_focus_traversal Modifier"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
