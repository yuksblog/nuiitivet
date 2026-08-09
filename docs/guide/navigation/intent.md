# Intent-Based Navigation

In larger applications, hardcoding widget creation inside your navigation logic can lead to tight coupling between different parts of your app. Nuiitivet provides an Intent-based navigation system to solve this problem.

## What is an Intent?

An Intent is simply a data class that represents a request to navigate to a specific screen. It can carry any data needed by that screen.

```python
from dataclasses import dataclass

@dataclass
class DetailsIntent:
    item_id: int
```

## Configuring Navigator.intents()

To use Intents, you create a Navigator with the `Navigator.intents(...)` factory and pass it to `App(...)`. You provide a mapping of Intent types to route builder functions.

![Navigation Intent](../../assets/navigation_intent.png)

```python
import nuiitivet.material as nv

from dataclasses import dataclass



@dataclass
class HomeIntent:
    pass


@dataclass
class DetailsIntent:
    item_id: int

class HomeScreen(nv.ComposableWidget):
    def build(self):
        return nv.Column(
            padding=16,
            gap=12,
            children=[
                nv.Text("Home Screen"),
                nv.Button("View Details", on_click=lambda: nv.Navigator.of(self).push(DetailsIntent(item_id=42)), style=nv.ButtonStyle.filled()),
            ],
        )

class DetailsScreen(nv.ComposableWidget):
    def __init__(self, intent: DetailsIntent):
        super().__init__()
        self.intent = intent

    def build(self):
        return nv.Container(
            width="wt",
            height="wt",
            child=nv.Column(
                padding=16,
                gap=12,
                children=[
                    nv.Text(f"Details for item {self.intent.item_id}"),
                    nv.Button("Back", on_click=lambda: nv.Navigator.of(self).pop(), style=nv.ButtonStyle.filled()),
                ],
            ),
        ).modifier(nv.background("#F5F7FF"))

app = nv.App(
    nv.Navigator.intents(
        initial_route=HomeIntent(),
        routes={
            HomeIntent: lambda _: HomeScreen(),
            DetailsIntent: lambda intent: DetailsScreen(intent),
        },
    ),
    title="Navigation Intent",
    width=400,
    height=300,
)
```

## Navigating with Intents

Once configured, you can navigate by pushing an Intent object to the `Navigator`. The `Navigator` will automatically resolve the Intent to the correct route using the mapping you provided.

```python
import nuiitivet.material as nv

def go_to_details():
    # Push an Intent instead of a Widget or Route
    nv.Navigator.of(self).push(DetailsIntent(item_id=42))

nv.Button(
    "View Details",
    on_click=go_to_details,
 style=nv.ButtonStyle.filled())
```

## Why Use Intents?

Intent-based navigation is highly recommended, especially when navigating from a ViewModel or controller. It allows your business logic to request a screen transition without needing to know how that screen is built or what widgets it uses. This separation of concerns makes your code more modular, testable, and easier to maintain.

Here is an example of how a ViewModel can trigger navigation using `Navigator` and Intents:

```python
import nuiitivet.material as nv

class ItemViewModel:
    def __init__(self, item_id: int):
        self.item_id = item_id

    # The navigator is passed in, so the ViewModel never touches a widget.
    def on_item_selected(self, navigator: nv.NavigatorProtocol):
        navigator.push(DetailsIntent(item_id=self.item_id))


class HomeScreen(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.vm = ItemViewModel(item_id=42)

    def build(self):
        def go_to_details():
            self.vm.on_item_selected(nv.Navigator.of(self))

        return nv.Button("View Details", on_click=go_to_details, style=nv.ButtonStyle.filled())
```

!!! warning "Not in `__init__`"
    Neither `nv.Navigator.of(self)` nor `nv.Navigator.of(self)` works there. Resolve one in
    the event handler, every time.

Because the ViewModel only depends on `NavigatorProtocol` and `DetailsIntent`, you can test the navigation decision logic in isolation.

## Testing a ViewModel

A fake needs only `push()`, `pop()`, and `can_pop()` — no widget tree, no `App`.

```python
class FakeNavigator:
    def __init__(self):
        self.pushed = []

    def push(self, route_or_widget_or_intent):
        self.pushed.append(route_or_widget_or_intent)

    def pop(self):
        if self.pushed:
            self.pushed.pop()

    def can_pop(self):
        return bool(self.pushed)


def test_selecting_an_item_navigates_to_details():
    navigator = FakeNavigator()

    ItemViewModel(item_id=42).on_item_selected(navigator)

    assert navigator.pushed == [DetailsIntent(item_id=42)]
```

For the overlay side of the same boundary, see
[Dialogs](../overlay/dialogs.md#typing-the-overlay-nvoverlayprotocol).
