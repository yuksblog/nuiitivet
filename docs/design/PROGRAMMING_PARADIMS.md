# Programming Paradigms

## 1. Basic Philosophy

The primary objective of `nuiitivet` is to be **"Intuitive"** for developers.
In UI development, "intuition" refers to a state where the developer's mental model aligns perfectly with the code.

To achieve this, `nuiitivet` does not cling to a single paradigm but adopts a balanced multi-paradigm approach:

1. **Declarative UI**
    * Construction of Widget trees and Modifiers is described declaratively.
    * *Why*: The static structure of "what is displayed on the screen" is most intuitive and readable when described declaratively.

2. **Data Binding**
    * Synchronization between state and display is described declaratively through data binding with Observables.
    * *Why*: The causal relationship of "if data changes, the display changes" is most natural when left to a reactive mechanism, making it easier to maintain consistency.

3. **Event Handlers**
    * Processing for events (e.g., button clicks) is described imperatively within event handlers.
    * *Why*: The flow of time ("what happens next after a user action") is most intuitive and easier to debug when described procedurally.

## 2. UI Component Control

Some UI components sit on the boundary between declarative (structure) and imperative (flow). The following sections detail recommended approaches for these cases.

### 2.1 Dialogs

* **Challenge**: While part of the UI structure, dialogs have a chronological nature as a "conversation (flow)" with the user.
* **Solution**: **Declarative Definition + Imperative Display**
  * Define the content as a Widget declaratively.
  * Display with `await` imperatively and receive the result.

#### Dialog: Basic Usage (View only)

```python
# Use await within an event handler to wait for result
result = await Overlay.dialog(
    child=AlertDialog(
        title=Text("Confirm"),
        content=Text("Are you sure?"),
        actions=[
            TextButton("Yes", on_click=lambda: Overlay.pop(True)),
            TextButton("No", on_click=lambda: Overlay.pop(False)),
        ]
    )
)
if result:
    do_something()
```

#### Dialog: ViewModel Implementation

Since ViewModels should not know about specific Widgets, use Intents or Service interfaces.
The `Overlay` is defined as a layer independent of the root content and is passed during `App` initialization.

##### 1. Using Standard Dialogs

The framework provides standard dialog Widgets (e.g., `AlertDialog`) and makes standard Dialog Intents available by default.

A ViewModel does not create Widgets directly but issues Intents to an abstract interface like `IOverlay`.
The actual Widget creation is delegated to the View layer (via `dialogs` configuration), allowing for the reuse of dialogs with a standard look and feel.

```python
class MyViewModel:
    def __init__(self, overlay: IOverlay):
        self.overlay = overlay

    async def on_error(self, error_msg):
        await self.overlay.dialog(AlertDialogIntent(title="Error", message=error_msg))
```

##### 2. Using Custom Dialogs

To display a dialog with a unique layout, define a custom Intent and register it with the `Overlay`.

```python
# 1. Custom Intent (Data class)
@dataclass
class ConfirmIntent:
    title: str
    message: str

# 2. App Initialization (Overlay Setup)
if __name__ == "__main__":
    # Define Overlay layer
    overlay = Overlay(
        # Register Intent (standard intents available by default)
        dialogs={
            ConfirmIntent: lambda intent: DialogRoute(
                builder=lambda: AlertDialog(
                    title=Text(intent.title),
                    content=Text(intent.message),
                    actions=[
                        TextButton("OK", on_click=lambda: overlay.close(True)),
                        TextButton("Cancel", on_click=lambda: overlay.close(False))
                    ]
                ),
                barrier_dismissible=True,
                barrier_color=Colors.black54
            )
        }
    )
    # ... App startup logic ...

# 3. ViewModel Usage
class MyViewModel:
    # ...
    async def on_delete(self):
        # Use custom intent
        if await self.overlay.dialog(ConfirmIntent("Confirmation", "Are you sure you want to delete this?")):
            self.delete_item()
```

This pattern unifies the usage of `Navigator` and `Overlay`, ensuring consistent ViewModel implementations.

### 2.2 Snackbars (Snackbar/Toast)

* **Challenge**: Temporary feedback that is more of a "notification" than a UI structure.
* **Solution**: **Imperative Fire & Forget**
  * Treated as a simple method call since there is no need to wait for a result.

#### Snackbar: Basic Usage (Material)

```python
MaterialOverlay.root().snackbar("Saved successfully!")
```

#### Snackbar: ViewModel Implementation

When Material Design is assumed, the ViewModel can receive a `MaterialOverlay` (or its abstraction) and trigger a snackbar.

```python
# ViewModel
class MyViewModel:
    def __init__(self, overlay: MaterialOverlay):
        self.overlay = overlay

    def on_save_complete(self):
        self.overlay.snackbar("Saved successfully!")
```

### 2.3 Tooltips

* **Challenge**: Temporary displays strongly tied to specific UI elements as attributes.
* **Solution**: **Fully Declarative**
  * Described as a wrapper for a Widget.

#### Tooltip: Basic Usage (View only)

```python
Tooltip(
    message="Click to edit",
    child=IconButton(icon=Icons.edit, ...)
)
```

## 3. Navigation Patterns

Navigation often blurs the lines between "change of state (declarative)" and "user movement (imperative)." In `nuiitivet`, we recommend the following patterns based on requirements.

### 3.1 Single Page Wizard

* **Overview**: Switching content within a single screen based on state.
* **Implementation**: Conditional branching (`if/else`) or `map` instead of `Navigator`.
* **Use Case**: Closely coupled step transitions (like wizards) that should not appear in the back history.

```python
class WizardScreen(Widget):
    def build(self):
        # Switch Widget based on current_step (Observable)
        return self.vm.current_step.map(lambda step: 
            Step1() if step == 1 else
            Step2() if step == 2 else
            Step3() if step == 3 else
            Step4()
        )
```

### 3.2 Parallel Navigation

* **Overview**: Switching between independent screens, common in tab bars or drawers.
* **Implementation**: Using `IndexedStack` or `BottomNavigationBar`.
* **Features**: Screen state (like scroll position) is preserved, but no back history is maintained.

```python
class MainScreen(Widget):
    def build(self):
        return Scaffold(
            body=IndexedStack(
                index=self.vm.current_tab_index,
                children=[HomeTab(), SearchTab(), ProfileTab()]
            ),
            bottom_navigation_bar=BottomNavigationBar(...)
        )
```

### 3.3 Standard Navigation

* **Overview**: Transitions with back history, common in "list to detail" or shopping cart flows.
* **Implementation**: Imperative transitions using `Navigator.push()`.
* **Features**: Data (e.g., cart contents) is managed reactively, while transition timing (next, back) is controlled imperatively via event handlers (Hybrid approach).

```python
# Example: List -> Cart -> Order Complete flow

# 1. Manage data with Observables (Global/Scoped Service)
class CartService:
    items = Observable([])

class ProductListScreen(Widget):
    def on_add_cart(self, product):
        # Reactive data manipulation (Update Service state)
        cart_service.items.value.append(product)
        
    def on_cart_click(self):
        # Imperative transition
        Navigator.push(CartScreen())

class CartScreen(Widget):
    def build(self):
        # Reactive display within the screen (Bind to Service state)
        return ForEach(cart_service.items, ...)

    def on_checkout_click(self):
        # 2. Execute order processing (Asynchronous)
        await self.vm.checkout()
        # 3. Transition to completion screen (Replace current cart screen)
        Navigator.push_replacement(OrderCompleteScreen())

class OrderCompleteScreen(Widget):
    def on_back_to_home_click(self):
        # 4. Return to the initial list
        Navigator.pop_until(ProductListScreen)
```

### 3.4 Intent-based Navigation

* **Overview**: Recommended pattern for standard navigation from a ViewModel.
* **Implementation**: The ViewModel issues only an "Intent" for the transition, delegating specific Widget creation to the View layer (via Navigator configuration).
* **Benefits**: Decouples ViewModel and View, provides type-safe routing, and improves testability.

```python
# 1. Define Intent
@dataclass
class ProductListIntent: pass

@dataclass
class CartIntent: pass

@dataclass
class OrderCompleteIntent: pass

# 2. ViewModel (No knowledge of specific Widgets)
class CartViewModel:
    def __init__(self, navigator: INavigator):
        self.navigator = navigator

    async def checkout(self):
        await self.service.submit_order()
        # Communicate intent: "Navigate to order completion"
        self.navigator.push_replacement(OrderCompleteIntent())

# 3. View (Bind Intent to Widget via Navigator configuration)
Navigator(
    initial_routes=[PageRoute(builder=lambda: ProductListScreen())],
    routes={
        ProductListIntent: lambda _: PageRoute(builder=lambda: ProductListScreen()),
        CartIntent: lambda _: PageRoute(builder=lambda: CartScreen()),
        OrderCompleteIntent: lambda _: PageRoute(builder=lambda: OrderCompleteScreen()),
    }
)
```

### 3.5 Nested Navigation

* **Overview**: Standard pattern combining Parallel and Standard navigation.
* **Implementation**: Host an independent `Navigator` (`Standard`) within each tab (`Parallel`).
* **Use Case**: Applications like Instagram or Twitter where each tab maintains its own navigation history.

```python
class MainScreen(Widget):
    def build(self):
        return Scaffold(
            # Parallel Navigation (Tab switching)
            body=IndexedStack(
                index=self.vm.current_tab_index,
                children=[
                    # Tab 1: Home (Standard Navigation)
                    # This Navigator manages transitions within this tab
                    Navigator(
                        key="home_nav",
                        initial_routes=[PageRoute(builder=lambda: ProductListScreen())],
                        routes={
                            ProductListIntent: lambda _: PageRoute(builder=lambda: ProductListScreen()),
                            CartIntent: lambda _: PageRoute(builder=lambda: CartScreen()),
                            # ...
                        }
                    ),
                    # Tab 2: Search (Standard Navigation)
                    Navigator(
                        key="search_nav",
                        initial_routes=[PageRoute(builder=lambda: SearchScreen())]
                    ),
                    # Tab 3: Profile
                    Navigator(
                        key="profile_nav",
                        initial_routes=[PageRoute(builder=lambda: ProfileScreen())]
                    ),
                ]
            ),
            bottom_navigation_bar=BottomNavigationBar(...)
        )

```

### 3.6 Declarative Routing - Future Work

* **Overview**: A pattern where the navigation state of the entire app is determined based on the URL or deep links.
* **Implementation**: A `Router` parses the URL and operates the `Navigator` according to declaratively defined mapping rules.
* **Use Cases**: Web support, external integration, complex state restoration.

```python
# Reconstruct Navigator stack based on URL on app startup or URL changes
Router(
    routes={
        "/": HomeIntent(),
        "/product/:id": lambda id: ProductDetailIntent(id),
        "/cart": CartIntent(),
    },
    # If URL "/product/123" is opened:
    # 1. HomeIntent -> HomeScreen
    # 2. ProductDetailIntent(123) -> DetailScreen
    # Automatically build this stack so that the back button returns to Home
    on_intent=lambda stack: Navigator.reset(stack)
)
```

## 4. Related Documents

* [Concurrency & Execution Model](../design/CONCURRENCY_MODEL.md)
* [Navigation](../design/NAVIGATION.md)
* [Overlay](../design/OVERLAY.md)
* [Asyncio Integration](../design/ASYNCIO_INTEGRATION.md)
