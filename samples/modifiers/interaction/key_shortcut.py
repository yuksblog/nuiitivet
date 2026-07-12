"""Two editor panes, each saving its own document with Accel+S (#327).

The point of the sample: ``Accel+S`` is bound per pane, not once for the app.
The binding is focus-scoped, so the pane that currently contains focus is the
one that saves — click into either editor and press Cmd+S (macOS) / Ctrl+S
(Linux, Windows).
"""

import nuiitivet.material as nv


class EditorPane(nv.ComposableWidget):
    """One document: a text field plus the save state of *its* text."""

    def __init__(self, title: str, text: str = ""):
        super().__init__()
        self.title = title
        self.text = nv.Observable(text)
        self.saved_text = nv.Observable(text)
        self.status = nv.Observable("saved")
        self.text.subscribe(lambda value: self._refresh_status())

    def _refresh_status(self) -> None:
        self.status.value = "saved" if self.text.value == self.saved_text.value else "modified"

    def save(self) -> None:
        self.saved_text.value = self.text.value
        self.status.value = "saved"
        print(f"[{self.title}] saved: {self.text.value!r}")

    def build(self):
        pane = nv.Container(
            width=320,
            padding=16,
            child=nv.Column(
                children=[
                    nv.Text(self.title),
                    nv.TextField(value=self.text, label="Document", width=288),
                    nv.Text(self.status.map(lambda s: f"status: {s}")),
                ],
                gap=8,
            ),
        )

        # Owned by the pane, because *which* document Accel+S saves is decided by
        # which pane holds focus. An app-level registry (one gesture, one
        # callback) could not express this: both panes want the same gesture.
        return pane.modifier(
            nv.background("#EEEEEE")
            | nv.corner_radius(12)
            | nv.key_shortcut("Accel+S", on_trigger=self.save)
        )


def main(png: str = ""):
    print("=" * 68)
    print("key_shortcut demo (#327)")
    print("  1. Click into (or Tab to) either editor.")
    print("  2. Type something -> status becomes 'modified'.")
    print("  3. Press Cmd+S (macOS) / Ctrl+S (elsewhere).")
    print("     Only the pane containing focus saves — the other is untouched.")
    print("=" * 68)

    content = nv.Row(
        children=[
            EditorPane("notes.txt", "hello"),
            EditorPane("draft.md", "world"),
        ],
        gap=16,
        padding=16,
    )

    app = nv.App(content=content, title="key_shortcut Modifier")
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
