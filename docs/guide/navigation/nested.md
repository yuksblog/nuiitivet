# Nested Navigation with Navigator

While `Navigator.root()` is useful for full-screen transitions, you might sometimes need to navigate within a specific part of your screen, such as inside a tab or a split pane. This is known as nested navigation.

## Using Navigator

You can create a nested navigation area by placing a `Navigator` widget anywhere in your widget tree. You can initialize it with a single initial screen.

![Nested Navigation](../../assets/navigation_sub.png)

```python
import nuiitivet.material as nv


class NestedHome(nv.ComposableWidget):
    def build(self):
        return nv.Column(
            padding=16,
            gap=12,
            children=[
                nv.Text("Nested Home"),
                nv.Button("Go Deeper (Nested)", on_click=lambda: nv.Navigator.of(self).push(NestedDetails()), style=nv.ButtonStyle.filled()),
            ],
        )

class NestedDetails(nv.ComposableWidget):
    def build(self):
        return nv.Container(
            width="wt",
            height="wt",
            child=nv.Column(
                padding=16,
                gap=12,
                children=[
                    nv.Text("Nested Details"),
                    nv.Button("Back (Nested)", on_click=lambda: nv.Navigator.of(self).pop(), style=nv.ButtonStyle.filled()),
                ],
            ),
        ).modifier(nv.background("#F5F7FF"))

class FullScreenDetails(nv.ComposableWidget):
    def build(self):
        return nv.Container(
            width="wt",
            height="wt",
            child=nv.Column(
                padding=20,
                gap=12,
                children=[
                    nv.Text("Full Screen Details"),
                    nv.Button("Back (Full Screen)", on_click=lambda: nv.Navigator.root().pop(), style=nv.ButtonStyle.filled()),
                ],
            ),
        ).modifier(nv.background("#EEF7F0"))

class MainScreen(nv.ComposableWidget):
    def build(self):
        return nv.Row(
            width="wt",
            height="wt",
            gap=12,
            padding=12,
            children=[
                # Left side: Static menu
                nv.Container(
                    width=200,
                    height="wt",
                    child=nv.Column(
                        padding=12,
                        gap=10,
                        children=[
                            nv.Text("Sidebar Menu"),
                            nv.Button("Open Full Screen", on_click=lambda: nv.Navigator.root().push(FullScreenDetails()), style=nv.ButtonStyle.filled()),
                        ],
                    ),
                ),
                # Right side: Nested Navigator
                nv.Container(
                    width="wt",
                    height="wt",
                    child=nv.Navigator(
                        routes=[nv.Route(builder=lambda: NestedHome())]
                    ),
                ),
            ],
        )
```

## Navigating within a Nested Navigator

To navigate within a nested navigator, you use `Navigator.of(context)` instead of `Navigator.root()`. This method searches up the widget tree from the given context to find the nearest `Navigator`.

In the example above:

- The "Open Full Screen" button uses `Navigator.root().push()` to replace the entire `MainScreen`.
- The "Go Deeper (Nested)" button uses `Navigator.of(self).push()` to change only the right side of the screen, leaving the sidebar intact.

By using `Navigator` and `Navigator.of()`, you can create complex, multi-layered navigation structures within your application, allowing for independent navigation flows in different sections of the UI.
