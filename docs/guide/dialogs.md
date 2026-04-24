## Introduction

nuiitivet offers a robust dialog system built on top of the Overlay architecture. While `AlertDialog` is the most common use case, the system is flexible enough to display any widget as a modal dialog and supports advanced architectural patterns like MVVM.

![Overlay System](../assets/overlay_dialog_toast.png)

## Basic Usage

The most straightforward way to show a dialog is to create an `AlertDialog` widget and pass it to `Overlay.root().dialog()`.

The `dialog()` method is **awaitable**, meaning you can wait for the user to close the dialog and receive a result.

```python
from nuiitivet.material import ButtonStyle
# src/samples/dialogs/basic_usage.py (Excerpt)

class BasicDialogDemo(ComposableWidget):
    result_text: Observable[str] = Observable("Ready")

    async def _show_dialog(self):
        # Overlay.root() finds the globally unique Overlay
        overlay = Overlay.root()

        # Create the dialog widget
        dialog = AlertDialog(
            title="CONFIRMATION",
            message="Do you want to proceed with this action?",
            actions=[
                Button(
                    "CANCEL",
                    on_click=lambda: overlay.close("Canceled"),
                 style=ButtonStyle.text()),
                Button(
                    "OK",
                    on_click=lambda: overlay.close("Confirmed"),
                 style=ButtonStyle.text()),
            ],
        )

        # Show the dialog and await the result
        # The result is an OverlayResult[T] object
        result = await overlay.dialog(dialog)
        
        if result.value:
            self.result_text.value = f"Last Action: {result.value}"

    def build(self) -> Widget:
        # User Interface building code...
        return Container(
            alignment="center",
            child=Column(
                gap=20,
                children=[
                    Text(self.result_text),
                    Button(
                        "Show Alert Dialog",
                        on_click=self._show_dialog,
                     style=ButtonStyle.filled()),
                ],
            )
        )
```

![Basic Usage](../assets/dialogs_basic_usage.png)

### Key Points

- `Overlay.root()`: Retrieves the root overlay instance.
- `overlay.dialog(widget)`: Displays the widget as a modal dialog with a scrim.
- `overlay.close(value, target)`: Closes the dialog associated with `target`. The `value` is wrapped in an `OverlayResult` and returned to the caller of `await overlay.dialog()`.

## Custom Dialogs

You are not limited to `AlertDialog`. Any Widget can be shown in the overlay. This is useful for custom forms, interactive tools, or specialized prompts.

```python
from nuiitivet.material import ButtonStyle
# src/samples/dialogs/custom_dialog.py (Excerpt)

class CustomDialogContent(ComposableWidget):
    """A completely custom widget to be used as a dialog."""
    
    def __init__(self, overlay: Overlay):
        super().__init__()
        self.overlay = overlay
        self.counter = Observable(0)

    def _increment(self):
        self.counter.value += 1

    def build(self) -> Widget:
        return Card(
            child=Container(
                padding=24,
                child=Column(
                    gap=16,
                    children=[
                        Text("Custom Interactive Dialog"),
                        Row(
                            gap=10,
                            children=[Text("Count:"), Text(self.counter.map(str))],
                        ),
                        Button("Increment", on_click=self._increment, style=ButtonStyle.filled()),
                        Button(
                            "Close & Return Count", 
                            on_click=lambda: self.overlay.close(self.counter.value)
                        , style=ButtonStyle.outlined()),
                    ],
                ),
            ),
            width=300,
        )

# Usage in parent widget:
# await overlay.dialog(CustomDialogContent(overlay))
```

![Custom Dialog](../assets/dialogs_custom_dialog.png)

### Self-Closing Dialogs with `OverlayAware`

The example above requires the caller to pass an `Overlay` reference into
`CustomDialogContent` so the dialog can close itself. For fully self-contained
dialogs, inherit from `OverlayAware[T]`. The framework automatically injects
the created `OverlayHandle` into the widget before it is mounted, so the
dialog can close itself via `self.overlay_handle.close(value)` without any
external wiring.

The type parameter `T` describes the result type returned from
`handle.close(value)` / `await handle`.

```python
# src/samples/dialogs/custom_dialog_overlay_aware.py (Excerpt)

from nuiitivet.overlay import OverlayAware
from nuiitivet.material import ButtonStyle


class CounterDialog(ComposableWidget, OverlayAware[int]):
    """A self-contained dialog that closes itself via OverlayAware."""

    def __init__(self) -> None:
        super().__init__()
        self.counter = Observable(0)

    def _close(self) -> None:
        # No Overlay reference needed — the framework injected the handle.
        self.overlay_handle.close(self.counter.value)

    def build(self) -> Widget:
        return Card(
            child=Container(
                padding=24,
                child=Column(
                    gap=16,
                    children=[
                        Text("Self-Closing Dialog"),
                        Button("Increment", on_click=self._increment, style=ButtonStyle.filled()),
                        Button("Close & Return Count", on_click=self._close, style=ButtonStyle.outlined()),
                    ],
                ),
            ),
            width=300,
        )


# Caller code no longer needs to pass the overlay:
# result = await overlay.dialog(CounterDialog())
```

#### Notes

- `overlay_handle` is available from the moment the dialog is mounted. Accessing
  it before the widget has been shown raises `RuntimeError`.
- `OverlayAware` works with **all** overlay show APIs, including
  `dialog`, `show_modal`, `show_modeless`, `show_light_dismiss`, `side_sheet`,
  `bottom_sheet`, and `loading`. It also works when the widget is wrapped in a
  `Route` (e.g. `DialogRoute(builder=lambda: CounterDialog())`).
- Attempting to display the same `OverlayAware` widget instance while its
  previous handle is still active raises `RuntimeError`. Re-displaying after
  the previous handle has completed is allowed.

## Architecting Dialogs in MVVM

When building larger applications with patterns like MVVM (Model-View-ViewModel), handling dialogs requires care regarding boundaries and testing. To illustrate the differences, we will use the same "Operation Complete" dialog in both coupled and decoupled patterns.

### Coupled ViewModels

One approach is to have the ViewModel create Widgets directly. While simple to implement, this couples your business logic to the UI framework.

**Direct Widget Creation Example:**

```python
from nuiitivet.material import ButtonStyle
# src/samples/dialogs/view_model_direct.py (Excerpt)

class CoupledViewModel:
    """
    This ViewModel knows about types like AlertDialog.
    It imports widgets which ties it to the UI layer.
    """
    
    def __init__(self):
        self.status = Observable("Ready")

    async def process_action(self, overlay: Overlay):
        self.status.value = "Processing..."
        
        # Logic creates UI components directly
        dialog = AlertDialog(
            title="Operation Complete",
            message="Process finished successfully.",
            icon="check_circle",
            actions=[Button("OK", on_click=lambda: overlay.close(True), style=ButtonStyle.text())]
        )
        
        await overlay.dialog(dialog)
        self.status.value = "Finished"

class DirectViewModelDemo(ComposableWidget):
    async def _on_run_click(self):
        overlay = Overlay.root()
        await self.vm.process_action(overlay)
```

![Coupled ViewModel](../assets/dialogs_view_model_direct.png)

### Decoupling with Intents

For those who prefer a stricter separation of concerns, nuiitivet supports **Intents**. An Intent is a plain data class that describes *what* needs to happen, not *how* it looks. The ViewModel emits an Intent, and the View (or Overlay system) decides how to render it.

By using `AlertDialogIntent`, the ViewModel remains pure logic.

```python
# src/samples/dialogs/view_model_intent.py (Excerpt)

from nuiitivet.material.intents import AlertDialogIntent

class DecoupledViewModel:
    """
    Pure logic. No Widget imports.
    Easier to test: we just assert that proper Intent was emitted.
    """
    
    def __init__(self):
        self.status = Observable("Ready")

    async def process_action(self, overlay: Overlay):
        self.status.value = "Processing..."
        
        # We just create a data description of what we want
        intent = AlertDialogIntent(
            title="Operation Complete",
            message="Process finished successfully.",
            icon="check_circle"
        )
        
        # Dispatch the intent. The system handles the UI.
        await overlay.dialog(intent)
        self.status.value = "Finished"
```

![Decoupled Intent](../assets/dialogs_view_model_intent.png)

## Custom Intents

The same principle applies to custom UI. You can define your own Intent classes and register them to render specific Widgets, keeping your ViewModels free of UI dependencies.

Below, we show how to implement the same "Counter Card" logic using Intents.

1. **Define the Intent**: A simple data class.

   ```python
   # src/samples/dialogs/custom_intent.py (Excerpt)

   @dataclass(frozen=True)
   class CounterIntent:
       initial_value: int = 0
   ```

2. **Map Intent to Dialog**: Register the connection between the Intent data and its Widget in `App`.

   ```python
   def create_counter_dialog(intent: CounterIntent) -> Widget:
       # This function knows about Widgets, but ViewModel doesn't
       return CustomDialogContent(
           Overlay.root(),
           initial=intent.initial_value
       )

   class IntentDemoApp(ComposableWidget):
       def build(self) -> Widget:
           return App(
               content=HomeView(),
               overlay_routes={
                   CounterIntent: create_counter_dialog
               }
           )
   ```

3. **Use in ViewModel**:

   ```python
   class MyViewModel:
       async def open_counter(self, overlay: Overlay):
           # Pure logic, using our custom intent
           result = await overlay.dialog(CounterIntent(initial_value=5))
           
           if result.value is not None:
              self.message.value = f"Final Count: {result.value}"
   ```

![Custom Intent](../assets/dialogs_custom_intent.png)
