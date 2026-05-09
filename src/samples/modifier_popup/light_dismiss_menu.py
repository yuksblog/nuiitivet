import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.material import Menu, MenuItem, MenuDivider
from nuiitivet.modifiers import background, clickable, corner_radius, light_dismiss
from nuiitivet.observable import Observable

is_open: Observable[bool] = Observable(False)


def toggle() -> None:
    is_open.value = not is_open.value


def close() -> None:
    is_open.value = False


menu = Menu(
    items=[
        MenuItem("New", on_click=lambda: print("New")),
        MenuItem("Open...", on_click=lambda: print("Open")),
        MenuDivider(),
        MenuItem("Save", leading_icon="save", on_click=lambda: print("Save")),
        MenuItem("Close", on_click=close),
    ],
    on_dismiss=close,
)

anchor = (
    nv.Container(
        width=160,
        height=40,
        child=md.Text("Open (light-dismiss)"),
        alignment="center",
    )
    .modifier(background("#4CAF50") | corner_radius(8) | clickable(on_click=toggle))
    .modifier(
        light_dismiss(
            menu,
            is_open=is_open,
            alignment="bottom-left",
            anchor="top-left",
            offset=(0.0, 4.0),
        )
    )
)


def main(png: str = "") -> None:
    if png:
        # For screenshot: place menu directly in layout (overlay not captured by render_to_png)
        _anchor = nv.Container(
            width=160, height=40, child=md.Text("Open (light-dismiss)"), alignment="center"
        ).modifier(background("#4CAF50") | corner_radius(8))
        _menu = Menu(
            items=[
                MenuItem("New", on_click=lambda: print("New")),
                MenuItem("Open...", on_click=lambda: print("Open")),
                MenuDivider(),
                MenuItem("Save", leading_icon="save", on_click=lambda: print("Save")),
                MenuItem("Close", on_click=lambda: None),
            ],
        )
        app = md.App(
            content=nv.Column(children=[_anchor, _menu], gap=4, padding=16),
            title_bar=nv.DefaultTitleBar(title="light_dismiss Modifier"),
            width=400,
            height=400,
        )
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app = md.App(
        content=nv.Column(children=[anchor], gap=8, padding=16),
        title_bar=nv.DefaultTitleBar(title="light_dismiss Modifier"),
        width=400,
        height=400,
    )
    app.run()


if __name__ == "__main__":
    main()
