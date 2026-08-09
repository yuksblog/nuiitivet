# Dialogs

## Introduction

nuiitivet offers a robust dialog system built on top of the Overlay architecture. While `BasicDialog` is the most common use case, the system is flexible enough to display any widget as a modal dialog and supports advanced architectural patterns like MVVM.

## Basic Usage

The most straightforward way to show a dialog is to create an `BasicDialog` widget and pass it to `Overlay.of(self).dialog()`.

The `dialog()` method is **awaitable**, meaning you can wait for the user to close the dialog and receive a result.

```python
import nuiitivet.material as nv
# samples/overlay/dialogs/basic_usage.py (Excerpt)

class BasicDialogDemo(nv.ComposableWidget):
    result_text: nv.Observable[str] = nv.Observable("Ready")

    async def _show_dialog(self):
        # No Overlay is nested above this screen, so this resolves to the App's.
        overlay = nv.Overlay.of(self)

        # Create the dialog widget
        dialog = nv.BasicDialog(
            title="CONFIRMATION",
            message="Do you want to proceed with this action?",
            actions=[
                nv.Button(
                    "CANCEL",
                    on_click=lambda: overlay.close("Canceled"),
                 style=nv.ButtonStyle.text()),
                nv.Button(
                    "OK",
                    on_click=lambda: overlay.close("Confirmed"),
                 style=nv.ButtonStyle.text()),
            ],
        )

        # Show the dialog and await the result
        # The result is an OverlayResult[T] object
        result = await overlay.dialog(dialog)
        
        if result.value:
            self.result_text.value = f"Last Action: {result.value}"

    def build(self) -> nv.Widget:
        # User Interface building code...
        return nv.Container(
            alignment="center",
            child=nv.Column(
                gap=20,
                children=[
                    nv.Text(self.result_text),
                    nv.Button(
                        "Show Alert Dialog",
                        on_click=self._show_dialog,
                     style=nv.ButtonStyle.filled()),
                ],
            )
        )
```

![Basic Usage](../../assets/dialogs_basic_usage.png)

### Key Points

- `Overlay.of(self)`: Resolves the overlay to show in — the nearest nested one, otherwise the App's.
- `overlay.dialog(widget)`: Displays the widget as a modal dialog with a scrim.
- `overlay.close(value, target)`: Closes the dialog associated with `target`. The `value` is wrapped in an `OverlayResult` and returned to the caller of `await overlay.dialog()`.

## Custom Dialogs

You are not limited to `BasicDialog`. Any Widget can be shown in the overlay. This is useful for custom forms, interactive tools, or specialized prompts.

```python
import nuiitivet.material as nv
# samples/overlay/dialogs/custom_dialog.py (Excerpt)

class CustomDialogContent(nv.ComposableWidget):
    """A completely custom widget to be used as a dialog."""
    
    def __init__(self, overlay: nv.Overlay):
        super().__init__()
        self.overlay = overlay
        self.counter = nv.Observable(0)

    def _increment(self):
        self.counter.value += 1

    def build(self) -> nv.Widget:
        return nv.Card(
            child=nv.Container(
                padding=24,
                child=nv.Column(
                    gap=16,
                    children=[
                        nv.Text("Custom Interactive Dialog"),
                        nv.Row(
                            gap=10,
                            children=[nv.Text("Count:"), nv.Text(self.counter.map(str))],
                        ),
                        nv.Button("Increment", on_click=self._increment, style=nv.ButtonStyle.filled()),
                        nv.Button(
                            "Close & Return Count", 
                            on_click=lambda: self.overlay.close(self.counter.value)
                        , style=nv.ButtonStyle.outlined()),
                    ],
                ),
            ),
            width=300,
        )

# Usage in parent widget:
# await overlay.dialog(CustomDialogContent(overlay))
```

![Custom Dialog](../../assets/dialogs_custom_dialog.png)

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
# samples/overlay/dialogs/custom_dialog_overlay_aware.py (Excerpt)

import nuiitivet.material as nv


class CounterDialog(nv.ComposableWidget, nv.OverlayAware[int]):
    """A self-contained dialog that closes itself via OverlayAware."""

    def __init__(self) -> None:
        super().__init__()
        self.counter = nv.Observable(0)

    def _close(self) -> None:
        # No Overlay reference needed — the framework injected the handle.
        self.overlay_handle.close(self.counter.value)

    def build(self) -> nv.Widget:
        return nv.Card(
            child=nv.Container(
                padding=24,
                child=nv.Column(
                    gap=16,
                    children=[
                        nv.Text("Self-Closing Dialog"),
                        nv.Button("Increment", on_click=self._increment, style=nv.ButtonStyle.filled()),
                        nv.Button("Close & Return Count", on_click=self._close, style=nv.ButtonStyle.outlined()),
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
  `show`, `dialog`, `side_sheet`, `bottom_sheet`, and `loading`, regardless of
  which axes were passed. It also works when the widget is wrapped in a
  `Route` (e.g. `OverlayRoute(builder=lambda: CounterDialog())`).
- Attempting to display the same `OverlayAware` widget instance while its
  previous handle is still active raises `RuntimeError`. Re-displaying after
  the previous handle has completed is allowed.

## Architecting Dialogs in MVVM

When building larger applications with patterns like MVVM (Model-View-ViewModel), handling dialogs requires care regarding boundaries and testing. To illustrate the differences, we will use the same "Operation Complete" dialog in both coupled and decoupled patterns.

### Coupled ViewModels

One approach is to have the ViewModel create Widgets directly. While simple to implement, this couples your business logic to the UI framework.

**Direct Widget Creation Example:**

```python
import nuiitivet.material as nv
# samples/overlay/dialogs/view_model_direct.py (Excerpt)

class CoupledViewModel:
    """
    This ViewModel knows about types like BasicDialog.
    It imports widgets which ties it to the UI layer.
    """
    
    def __init__(self):
        self.status = nv.Observable("Ready")

    async def process_action(self, overlay: nv.Overlay):
        self.status.value = "Processing..."
        
        # Logic creates UI components directly
        dialog = nv.BasicDialog(
            title="Operation Complete",
            message="Process finished successfully.",
            icon="check_circle",
            actions=[nv.Button("OK", on_click=lambda: overlay.close(True), style=nv.ButtonStyle.text())]
        )
        
        await overlay.dialog(dialog)
        self.status.value = "Finished"

class DirectViewModelDemo(nv.ComposableWidget):
    async def _on_run_click(self):
        overlay = nv.Overlay.of(self)
        await self.vm.process_action(overlay)
```

![Coupled ViewModel](../../assets/dialogs_view_model_direct.png)

### Decoupling with Intents

For those who prefer a stricter separation of concerns, nuiitivet supports **Intents**. An Intent is a plain data class that describes *what* needs to happen, not *how* it looks. The ViewModel emits an Intent, and the View (or Overlay system) decides how to render it.

By using `BasicDialogIntent`, the ViewModel remains pure logic.

```python
# samples/overlay/dialogs/view_model_intent.py (Excerpt)

import nuiitivet.material as nv

class DecoupledViewModel:
    """
    Pure logic. No Widget imports.
    Easier to test: we just assert that proper Intent was emitted.
    """
    
    def __init__(self):
        self.status = nv.Observable("Ready")

    async def process_action(self, overlay: nv.OverlayProtocol):
        self.status.value = "Processing..."
        
        # We just create a data description of what we want
        intent = nv.BasicDialogIntent(
            title="Operation Complete",
            message="Process finished successfully.",
            icon="check_circle"
        )
        
        # Dispatch the intent. The system handles the UI.
        await overlay.dialog(intent)
        self.status.value = "Finished"
```

![Decoupled Intent](../../assets/dialogs_view_model_intent.png)

## Typing the Overlay: `nv.OverlayProtocol`

Annotate the overlay a ViewModel receives as `nv.OverlayProtocol`, not the concrete
`nv.Overlay`, as in the example above. A test can then pass a fake with no widget tree and
no `App`.

Pass it **per call**, resolved in the event handler: `nv.Overlay.of(self)` does not
work from a widget's `__init__`, because a widget has no ancestors until it is mounted.

## Custom Intents

The same principle applies to custom UI. You can define your own Intent classes and register them to render specific Widgets, keeping your ViewModels free of UI dependencies.

Below, we show how to implement the same "Counter Card" logic using Intents.

1. **Define the Intent**: A simple data class.

   ```python
   # samples/overlay/dialogs/custom_intent.py (Excerpt)

   @dataclass(frozen=True)
   class CounterIntent:
       initial_value: int = 0
   ```

2. **Map Intent to Dialog**: Register the connection between the Intent data and its Widget in `App`.

   ```python
   def create_counter_dialog(intent: CounterIntent) -> nv.Widget:
       # This function knows about Widgets, but ViewModel doesn't. It has no
       # context to resolve an overlay from -- and needs none: the widget it
       # returns is mounted inside the overlay showing it, so the dialog itself
       # calls nv.Overlay.of(self) when it wants to close.
       return CustomDialogContent(initial=intent.initial_value)

   class IntentDemoApp(nv.ComposableWidget):
       def build(self) -> nv.Widget:
           return nv.App(
               content=HomeView(),
               overlay_routes={
                   CounterIntent: create_counter_dialog
               }
           )
   ```

3. **Use in ViewModel**:

   ```python
   class MyViewModel:
       async def open_counter(self, overlay: nv.OverlayProtocol):
           # Pure logic, using our custom intent
           result = await overlay.dialog(CounterIntent(initial_value=5))
           
           if result.value is not None:
              self.message.value = f"Final Count: {result.value}"
   ```

![Custom Intent](../../assets/dialogs_custom_intent.png)
