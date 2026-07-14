import nuiitivet.material as nv


class RebuildCaveat(nv.ComposableWidget):
    """Shows that a mount callback follows the *widget instance*, not the component."""

    def __init__(self) -> None:
        super().__init__()
        self.override_count = 0
        self.modifier_count = 0
        self.summary = nv.Observable("")

    def on_mount(self) -> None:
        # Runs once for the lifetime of this RebuildCaveat instance.
        super().on_mount()
        self.override_count += 1
        self._update_summary()

    def _child_mounted(self) -> None:
        # build() returns a new Column on every rebuild, so this runs every time.
        self.modifier_count += 1
        self._update_summary()

    def _update_summary(self) -> None:
        self.summary.value = (
            f"on_mount() override on the ComposableWidget: {self.override_count}\n"
            f"on_mount() modifier on the built Column:     {self.modifier_count}"
        )

    def build(self) -> nv.Widget:
        return nv.Column(
            children=[
                nv.Text("Press Rebuild and watch the two counters diverge."),
                nv.Button("Rebuild", on_click=self.rebuild, style=nv.ButtonStyle.filled()),
                nv.Text(self.summary),
            ],
            gap=14,
            cross_alignment="start",
            padding=24,
        ).modifier(nv.on_mount(self._child_mounted))


def main(png: str = "") -> None:
    app = nv.App(content=RebuildCaveat(), title="Mount is not once per component", width=460, height=260)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
