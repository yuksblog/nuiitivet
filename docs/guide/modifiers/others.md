# Other Modifiers

Other modifiers provide additional functionalities to Widgets, such as handling back navigation.

## On Size Changed

`on_size_changed` reports the widget's own measured size — an `nv.Size` with `.width` / `.height` — after every layout that changed it. It is how a component adapts to the space its parent gave it, which `build()` cannot see.

```python
class Panel(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__(width="wt", height="wt")
        self._wide = nv.Observable(False)

    def _on_size(self, size: nv.Size) -> None:
        self._wide.value = size.width >= 600

    def build(self) -> nv.Widget:
        return nv.Column([...]).modifier(nv.on_size_changed(self._on_size))
```

Like the lifecycle modifiers it registers on the widget itself and adds no node to the tree. It fires once with the first measurement, then only when the size actually changed — a widget that is merely moved, or re-laid-out at the same size, is silent.

The callback is dispatched **between frames**, never inside the layout pass, so it may safely write Observables, push routes, or replace children; the effect lands on the next frame. Two consequences: do not resize the measured widget from its own callback, or the report can feed back; and the first call arrives after the first paint, so give the Observable the value the initial size implies to avoid a one-frame transition on startup.

See [Adaptive Layout](../layout/adaptive.md) for the full pattern, and [Geometry](../advanced/geometry.md) for the case where a *subtree* needs an ancestor's size.

## Will Pop

You can handle back navigation (e.g., pressing the Esc key) using the `will_pop` modifier. It takes an `on_will_pop` callback that returns a boolean indicating whether pop should be allowed.
In this example, an editor screen is pushed on a `Navigator`. Pop is blocked while there are unsaved changes, and allowed after Save or Discard.

```python
import nuiitivet.material as nv

class HomeScreen(nv.ComposableWidget):
    def build(self):
        def _open_editor() -> None:
            nv.Navigator.root().push(EditScreen())

        return nv.Container(
            padding=24,
            child=nv.Column(
                children=[
                    nv.Text("Open editor, edit text, then try Esc or Back."),
                    nv.Button("Open editor", on_click=_open_editor, style=nv.ButtonStyle.filled()),
                ],
                gap=14,
                cross_alignment="start",
            ),
        )

class EditScreen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.text = nv.Observable("Hello")
        self._initial_text = str(self.text.value)

    def _is_dirty(self) -> bool:
        return str(self.text.value) != self._initial_text

    def _save(self) -> None:
        self._initial_text = str(self.text.value)

    async def _on_will_pop(self) -> bool:
        if not self._is_dirty():
            return True

        result = await nv.Overlay.root().dialog(
            nv.BasicDialog(
                title="Discard changes?",
                message="You have unsaved changes.",
                actions=[
                    nv.Button("Cancel", on_click=lambda: nv.Overlay.root().close(False), style=nv.ButtonStyle.text()),
                    nv.Button("Discard", on_click=lambda: nv.Overlay.root().close(True), style=nv.ButtonStyle.filled()),
                ],
            ),
            dismiss_on_outside_tap=False,
        )
        return bool(result.value)

    def build(self):
        return nv.Container(
            padding=24,
            child=nv.Column(
                children=[
                    nv.Text("Edit text. Back/Esc asks confirmation when unsaved."),
                    nv.TextField.two_way(
                        self.text,
                        width=420,
                        height=52,
                        padding=10,
                    ),
                    nv.Row(
                        children=[
                            nv.Button("Back", on_click=lambda: nv.Navigator.root().pop(), style=nv.ButtonStyle.text()),
                            nv.Button("Save", on_click=self._save, style=nv.ButtonStyle.filled()),
                        ],
                        gap=10,
                    ),
                ],
                gap=14,
                cross_alignment="start",
            ),
        ).modifier(nv.will_pop(on_will_pop=self._on_will_pop))

def main() -> None:
    nv.App(
        HomeScreen(),
    ).run()
```

![Will Pop](../../assets/modifier_others_will_pop.png)

## Stick

The `stick` modifier overlays any widget on top of a target widget at a specified anchor point. Unlike popup modifiers, the overlaid widget is always visible — it is not transient. Because it is a static overlay rather than a dynamic one, it is suited to custom decorations rather than transient indicators like notifications or status updates.

The following example composes a custom symbol by layering a smaller icon over a larger base icon. Because the result is a fixed, decorative composition — not a value that changes at runtime — it is a good fit for `stick`. (Avoid using it for dynamic indicators such as badges or status dots; those represent changing state and belong in transient UI instead.) Any widget can be passed as the overlay.

```python
import nuiitivet.material as nv

def _base_icon(name: str) -> nv.Widget:
    return nv.Icon(name, size=64, style=nv.IconStyle(color="#5F6368"))

def _overlay_icon(name: str, color: str) -> nv.Widget:
    return nv.Icon(name, size=30, style=nv.IconStyle(color=color))

# cloud + upward arrow = "upload to cloud"
upload = _base_icon("cloud").modifier(
    nv.stick(_overlay_icon("arrow_upward", "#1A73E8"), target_anchor="center", content_anchor="center")
)

# folder + star = "favorite folder"
favorite_folder = _base_icon("folder").modifier(
    nv.stick(_overlay_icon("star", "#F9AB00"), target_anchor="center", content_anchor="center")
)

# photo + pencil = "edit photo"
edit_photo = _base_icon("photo").modifier(
    nv.stick(_overlay_icon("edit", "#188038"), target_anchor="center", content_anchor="center")
)
```

![Stick Modifier](../../assets/modifier_others_stick.png)

The `target_anchor` parameter sets the reference point on the **target widget**, and `content_anchor` sets the reference point on the **overlaid widget** that lines up with it. An optional `offset` tuple provides additional pixel adjustment.

## Visible

The `visible()` modifier conditionally shows or hides a widget.
It is a thin composition of `opacity()`, `block_focus_traversal()` and `passthrough_pointer()`:
while hidden the widget is rendered fully transparent, ignores all pointer input and is
skipped by Tab traversal, but it **retains its normal layout space** — the surrounding
layout is not affected.

### Basic usage

Pass a `bool` or an `Observable[bool]` as the condition:

```python
import nuiitivet.material as nv


def _panel(label: str) -> nv.Widget:
    return nv.Card(
        child=nv.Text(label, style=nv.TextStyle(font_size=14)),
        padding=16,
        width=180,
        style=nv.CardStyle.filled(),
    )


content = nv.Column(
    children=[
        nv.Text("visible(True) — always shown", style=nv.TextStyle(font_size=12)),
        _panel("Always shown").modifier(nv.visible(True)),
        nv.Text("visible(False) — hidden, but layout space preserved", style=nv.TextStyle(font_size=12)),
        _panel("Never shown").modifier(nv.visible(False)),
        nv.Text("Sibling below: layout space of hidden widget is reserved", style=nv.TextStyle(font_size=12)),
    ],
    gap=12,
    cross_alignment="start",
    padding=24,
)
```

![Visible Static](../../assets/modifier_others_visible_static.png)

To make visibility reactive, pass an `Observable[bool]`:

```python
import nuiitivet.material as nv

is_visible: nv.Observable[bool] = nv.Observable(True)

widget.modifier(nv.visible(is_visible))
```

Whenever `is_visible.value` changes, the widget instantly appears or disappears (no animation).

### Animated usage

Pass a `TransitionDefinition` to animate the transition between hidden and shown states.
The example below combines a fade and a scale animation:

```python
import nuiitivet.material as nv

_FADE_SCALE = nv.TransitionDefinition(
    motion=nv.LinearMotion(0.25),
    pattern=nv.FadePattern(start_alpha=0.0, end_alpha=1.0)
    | nv.ScalePattern(start_scale_x=0.9, start_scale_y=0.9, end_scale_x=1.0, end_scale_y=1.0),
)


class MyWidget(nv.ComposableWidget):
    is_visible: nv.Observable[bool] = nv.Observable(True)

    def build(self) -> nv.Widget:

        def toggle() -> None:
            self.is_visible.value = not self.is_visible.value

        panel = nv.Card(
            child=nv.Text("Animated widget", style=nv.TextStyle(font_size=14)),
            padding=16,
            width=220,
            style=nv.CardStyle.filled(),
        )

        return nv.Column(
            children=[
                nv.Button("Toggle visibility", on_click=toggle, style=nv.ButtonStyle.filled()),
                panel.modifier(nv.visible(self.is_visible, transition=_FADE_SCALE)),
                nv.Text("↑ Layout space is always reserved", style=nv.TextStyle(font_size=12)),
            ],
            gap=12,
            cross_alignment="start",
        )
```

![Visible Animated](../../assets/modifier_others_visible_animated.png)

> **Note:** `visible()` never collapses the widget's layout size.
> If you need the widget to also shrink or grow in the layout during the animation,
> use a layout-aware widget instead.

## Keyed

The `keyed()` modifier attaches a stable `key` — a layout-independent identifier — to a widget. A key is central to the AI pair-programming loop and serves two roles:

- **Action targeting** — the dev bridge drives a widget by its `key` instead of brittle pixel coordinates (e.g. `click(key="increment-btn")`), so targeting survives layout changes.
- **Hot-reload state restoration** — a `key` anchors a widget's `Observable` state across a structural edit (a reorder or a sibling insertion), where a position-based match would otherwise break.

`keyed()` is applied on demand: add it when a widget needs to be targeted or state-stabilized, and remove it once that need is gone.

### Usage

Apply `keyed()` to any already-built widget:

```python
import nuiitivet.material as nv

nv.Button("increment").modifier(nv.keyed("increment-btn"))
nv.TextField(label="Email").modifier(nv.keyed("email"))
```

Choose a key that is unique enough to disambiguate the widget among its realistic targets (think "testID").

### Ordering rule

When you combine `keyed()` with modifiers that **wrap** the widget (such as `background`, `visible`, or `stick`), apply `keyed()` **last** so the key lands on the outermost node:

```python
widget.modifier(nv.clickable(on_click=...) | nv.keyed("row"))
```

This ordering is required for hot-reload state restoration to survive a reorder. Used alone, `keyed()` has nothing to wrap, so the order does not matter.

### Relationship to `ComposableWidget(key=...)`

A `ComposableWidget` that owns state takes its key through the constructor:

```python
MyItem(key="item-1")
```

Use `keyed()` when you instead need to key an already-built widget inline.
