import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.material import Card, CardStyle, Text
from nuiitivet.material.divider import Divider
from nuiitivet.modifiers import background, clickable, corner_radius, modeless
from nuiitivet.observable import Observable

is_open: Observable[bool] = Observable(False)


def toggle() -> None:
    is_open.value = not is_open.value


info_panel = Card(
    child=nv.Column(
        children=[
            Text("Keyboard Shortcuts"),
            Divider(padding=(4, 0)),
            Text("Ctrl+N  New file"),
            Text("Ctrl+O  Open file"),
            Text("Ctrl+S  Save"),
            Text("Ctrl+Z  Undo"),
        ],
        gap=6,
        cross_alignment="start",
    ),
    padding=16,
    width=200,
    style=CardStyle.elevated(),
)

anchor = (
    nv.Container(
        width=160,
        height=40,
        child=md.Text("Show shortcuts"),
        alignment="center",
    )
    .modifier(background("#2196F3") | corner_radius(8) | clickable(on_click=toggle))
    .modifier(
        modeless(
            info_panel,
            is_open=is_open,
            alignment="bottom-left",
            anchor="top-left",
            offset=(0.0, 4.0),
        )
    )
)


def main(png: str = "") -> None:
    if png:
        # For screenshot: place popup content directly in layout (overlay not captured by render_to_png)
        _anchor = nv.Container(width=160, height=40, child=md.Text("Show shortcuts"), alignment="center").modifier(
            background("#2196F3") | corner_radius(8)
        )
        _panel = Card(
            child=nv.Column(
                children=[
                    Text("Keyboard Shortcuts"),
                    Divider(padding=(4, 0)),
                    Text("Ctrl+N  New file"),
                    Text("Ctrl+O  Open file"),
                    Text("Ctrl+S  Save"),
                    Text("Ctrl+Z  Undo"),
                ],
                gap=6,
                cross_alignment="start",
            ),
            padding=16,
            width=200,
            style=CardStyle.elevated(),
        )
        app = md.App(
            content=nv.Column(children=[_anchor, _panel], gap=4, padding=16),
            title_bar=nv.DefaultTitleBar(title="modeless Modifier"),
            width=300,
            height=350,
        )
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app = md.App(
        content=nv.Column(children=[anchor], gap=8, padding=16),
        title_bar=nv.DefaultTitleBar(title="modeless Modifier"),
        width=300,
        height=250,
    )
    app.run()


if __name__ == "__main__":
    main()
