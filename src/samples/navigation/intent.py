import nuiitivet as nv

from dataclasses import dataclass

from nuiitivet.material import FilledButton, MaterialApp, Text
from nuiitivet.layout.column import Column
from nuiitivet.navigation import Navigator
from nuiitivet.widgeting.widget import ComposableWidget
from nuiitivet.widgets.box import Box


@dataclass
class HomeIntent:
    pass


@dataclass
class DetailsIntent:
    item_id: int


class DetailsScreen(ComposableWidget):
    def __init__(self, item_id: int) -> None:
        super().__init__()
        self.item_id = item_id

    def build(self):
        def go_back() -> None:
            Navigator.root().pop()

        return Box(
            background_color="#F5F7FF",
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
            child=Column(
                padding=16,
                gap=12,
                children=[
                    Text(f"Details for item {self.item_id}"),
                    FilledButton("Back", on_click=go_back),
                ],
            ),
        )


class ItemViewModel:
    def __init__(self, item_id: int, navigator: Navigator) -> None:
        self.item_id = item_id
        self.navigator = navigator

    def on_item_selected(self) -> None:
        self.navigator.push(DetailsIntent(item_id=self.item_id))


class HomeScreen(ComposableWidget):
    def build(self):
        view_model = ItemViewModel(item_id=42, navigator=Navigator.root())

        def go_to_details() -> None:
            view_model.on_item_selected()

        return Column(
            padding=16,
            gap=12,
            children=[
                Text("Home Screen"),
                FilledButton("View Details", on_click=go_to_details),
            ],
        )


def main(png_path: str | None = None) -> None:
    app = MaterialApp.navigation(
        routes={
            HomeIntent: lambda _: HomeScreen(),
            DetailsIntent: lambda intent: DetailsScreen(item_id=intent.item_id),
        },
        initial_route=HomeIntent(),
        title_bar=nv.DefaultTitleBar(title="Navigation Intent"),
        width=400,
        height=300,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
