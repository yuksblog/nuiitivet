"""What a screen reader reads, and the labels an app adds where there are no words.

A standard control is read as it is: a button by its text, a text field by
its label, a slider by its value. A control with no words of its own, an
icon button or a bare checkbox, is read by the label ``nv.semantics`` gives it.

Interactions (macOS: turn VoiceOver on with Cmd+F5, then VO+Right through the
window. Windows: turn Narrator on with Win+Ctrl+Enter, then Caps Lock+Right
through the window. Linux: turn Orca on with Super+Alt+S, then Tab through
the window):
    - "Save" is read as "Save, button" with nothing added.
    - The close icon is read as "Close, button" from its ``nv.semantics`` label.
    - The warning icon is read as "Warning, image".
    - The checkbox is read as "Agree, checkbox" from its label; "I agree"
      beside it is read as text of its own.
    - The cart row is read once, as "Cart, 3 items", not as two texts.
    - The range slider is read as two sliders, "Lowest price" and
      "Highest price". VO+Shift+Down on one starts interacting with it; Up
      and Down then move its handle, and VO+Shift+Up stops. With Narrator or
      Orca, Tab to a handle and press Left or Right.
    - VO+Space (Narrator: Caps Lock+Enter, Orca: Enter) on "Save" runs its
      click like a press.
"""

from __future__ import annotations

import nuiitivet.material as nv

_MUTED = nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT)


class Screen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.saved = nv.Observable(0)
        self.agree = nv.Observable(False)

    def _save(self) -> None:
        self.saved.value += 1

    def build(self):
        return nv.Column(
            children=[
                nv.Text("Screen reader", type_scale=nv.TypeScale.TITLE_MEDIUM),
                nv.Text(
                    "Turn the screen reader on (VoiceOver: Cmd+F5, Narrator: Win+Ctrl+Enter, Orca: Super+Alt+S) "
                    "and step through it.",
                    style=_MUTED,
                ),
                nv.Row(
                    children=[
                        nv.Button("Save", on_click=self._save),  # read as "Save, button": nothing to add
                        nv.IconButton("close", on_click=lambda: None).modifier(
                            nv.semantics(label="Close")  # an icon has no words
                        ),
                        nv.Icon("warning").modifier(
                            nv.semantics(label="Warning", role=nv.SemanticsRole.IMAGE)  # read as an image
                        ),
                    ],
                    gap=8,
                ),
                nv.Row(
                    children=[
                        nv.Checkbox(checked=self.agree).modifier(nv.semantics(label="Agree")),
                        nv.Text("I agree"),
                    ],
                    gap=8,
                    cross_alignment="center",
                ),
                nv.Row(
                    children=[nv.Icon("shopping_cart"), nv.Text("3 items")],
                    gap=8,
                    cross_alignment="center",
                ).modifier(nv.semantics(label="Cart, 3 items")),  # the row is read once, in these words
                nv.HorizontalRangeSlider(value_start=20, value_end=80, min_value=0, max_value=100).modifier(
                    nv.semantics(label=["Lowest price", "Highest price"])  # one label per handle
                ),
                nv.Text(self.saved.map(lambda n: f"saved: {n}"), style=_MUTED),
            ],
            gap=12,
            padding=24,
        )


def main(png: str = ""):
    app = nv.App(nv.Window(content=Screen, title="screen_reader", width=520, height=360))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
