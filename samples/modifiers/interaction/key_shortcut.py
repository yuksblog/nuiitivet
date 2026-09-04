"""Keyboard shortcuts and their scopes.

Two scopes, side by side:

- The **canvas** binds ``Accel+Z`` with the default FOREGROUND scope. It fires
  while the canvas is displayed — no focus required, and it keeps working while
  you are typing in the text field.
- The **two editor panes** bind the same ``Accel+S`` with the FOCUS scope. Both
  are displayed at once, so only focus can decide which document is saved. Bound
  as FOREGROUND they would be ambiguous, and nothing would fire.
"""

import nuiitivet.material as nv


class PaintCanvas(nv.ComposableWidget):
    """Undo is a canvas concern, and it must work with nothing focused."""

    def __init__(self):
        super().__init__()
        self.strokes = nv.Observable(3)

    def undo(self) -> None:
        self.strokes.value = max(0, self.strokes.value - 1)
        print(f"[canvas] undo -> {self.strokes.value} strokes")

    def build(self):
        canvas = nv.Container(
            width=300,
            height=140,
            padding=16,
            child=nv.Column(
                children=[
                    nv.Text("Canvas (FOREGROUND)"),
                    nv.Text(self.strokes.map(lambda n: f"strokes: {n}")),
                    nv.Text("Accel+Z undoes, focus or not"),
                ],
                gap=8,
            ),
        )
        return canvas.modifier(
            nv.background("#E3F2FD")
            | nv.corner_radius(12)
            | nv.key_shortcut("Accel+Z", on_trigger=self.undo)
        )


class EditorPane(nv.ComposableWidget):
    """Save is a document concern, and which document is decided by focus."""

    def __init__(self, title: str, text: str = ""):
        super().__init__()
        self.title = title
        self.text = nv.Observable(text)
        self.saved_text = nv.Observable(text)
        # status is a function of the two texts, so derive it — nothing to keep in sync.
        self.status = nv.combine(self.text, self.saved_text).compute(
            lambda current, saved: "saved" if current == saved else "modified"
        )

    def save(self) -> None:
        self.saved_text.value = self.text.value
        print(f"[{self.title}] saved: {self.text.value!r}")

    def build(self):
        pane = nv.Container(
            width=300,
            padding=16,
            child=nv.Column(
                children=[
                    nv.Text(f"{self.title} (FOCUS)"),
                    nv.TextField(value=self.text, label="Document", width=268),
                    nv.Text(self.status.map(lambda s: f"status: {s}")),
                ],
                gap=8,
            ),
        )
        return pane.modifier(
            nv.background("#EEEEEE")
            | nv.corner_radius(12)
            | nv.key_shortcut("Accel+S", on_trigger=self.save, scope=nv.ShortcutScope.FOCUS)
        )


def main(png: str = ""):
    print("=" * 70)
    print("key_shortcut demo")
    print("  Accel = Cmd on macOS, Ctrl elsewhere.")
    print("  1. Press Accel+Z with nothing focused -> the canvas undoes.")
    print("  2. Click into an editor and type -> status becomes 'modified'.")
    print("  3. Accel+Z still undoes the canvas, even while the editor has focus.")
    print("  4. Accel+S saves only the editor that currently holds focus.")
    print("=" * 70)

    content = nv.Column(
        children=[
            PaintCanvas(),
            nv.Row(
                children=[EditorPane("notes.txt", "hello"), EditorPane("draft.md", "world")],
                gap=16,
            ),
        ],
        gap=16,
        padding=16,
    )

    app = nv.App(nv.Window(content=content, title="key_shortcut Modifier"))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
