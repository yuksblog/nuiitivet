from nuiitivet.modifiers import background
from nuiitivet.runtime.app import App
from nuiitivet.material.text import Text
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import TextButton
import nuiitivet as nv
from nuiitivet.material.styles.button_style import ButtonStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.runtime.intents import ExitAppIntent


def main():
    # Create a custom title bar widget
    title_bar_content = Row(
        children=[
            Text("Custom Title Bar", style=TextStyle(color="#ffffff")),
            TextButton(
                icon="close",
                on_click=lambda: App.of(title_bar_content).dispatch(ExitAppIntent()),
                width=40,
                height=40,
                style=ButtonStyle(foreground="#ffffff"),
            ),
        ],
        main_alignment="space-between",
        cross_alignment="center",
        width="100%",
        height=40,
        padding=(10, 5),
    ).modifier(background("#37474f"))

    app = App(
        content=Container(
            child=Text("Content Area", style=TextStyle(font_size=20)),
            alignment="center",
        ),
        width=600,
        height=400,
        title_bar=nv.CustomTitleBar(content=title_bar_content),
        background="#ffffff",
    )
    app.run()


if __name__ == "__main__":
    main()
