import nuiitivet.material as nv

from dataclasses import dataclass


@dataclass
class HomeIntent:
    pass


@dataclass
class DetailsIntent:
    item_id: int


class DetailsScreen(nv.ComposableWidget):
    def __init__(self, item_id: int) -> None:
        super().__init__()
        self.item_id = item_id

    def build(self):
        def go_back() -> None:
            nv.Navigator.of(self).pop()

        return nv.Box(
            background_color="#F5F7FF",
            width="wt",
            height="wt",
            child=nv.Column(
                padding=16,
                gap=12,
                children=[
                    nv.Text(f"Details for item {self.item_id}"),
                    nv.Button("Back", on_click=go_back, style=nv.ButtonStyle.filled()),
                ],
            ),
        )


class ItemViewModel:
    def __init__(self, item_id: int) -> None:
        self.item_id = item_id

    # The navigator is passed in, so the ViewModel never touches a widget.
    def on_item_selected(self, navigator: nv.NavigatorProtocol) -> None:
        navigator.push(DetailsIntent(item_id=self.item_id))


class HomeScreen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.view_model = ItemViewModel(item_id=42)

    def build(self):
        def go_to_details() -> None:
            # Resolve the navigator here, not in __init__.
            self.view_model.on_item_selected(nv.Navigator.of(self))

        return nv.Column(
            padding=16,
            gap=12,
            children=[
                nv.Text("Home Screen"),
                nv.Button("View Details", on_click=go_to_details, style=nv.ButtonStyle.filled()),
            ],
        )


def main(png_path: str | None = None) -> None:
    app = nv.App(
        nv.Navigator.intents(
            initial_route=HomeIntent(),
            routes={
                HomeIntent: lambda _: HomeScreen(),
                DetailsIntent: lambda intent: DetailsScreen(item_id=intent.item_id),
            },
        ),
        title="Navigation Intent",
        width=400,
        height=300,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
