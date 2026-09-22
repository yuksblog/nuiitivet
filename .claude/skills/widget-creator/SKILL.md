---
name: widget-creator
description: Create or update a widget: base class, location, value surface, MD3 spacing, parameter order, docstrings, the checklist.
---

# Create / Update Widget

Creating a new widget, or updating one, in `src/nuiitivet/`.

## Workflow

### 1. Plan the Widget

- **Purpose**: display data, handle input, or lay out children.
- **Rendering pipeline**: read `docs/design/RENDERING_PIPELINE.md` first.
  `paint()` is a pure consumer: no `layout()` call, no state mutation, no side
  effect. Side effects go in `on_mount`, `on_unmount`, input handlers and
  observable callbacks.
- **Base class**:
  - `Widget`: a fundamental component (`src/nuiitivet/widgeting/widget.py`)
  - `ComposableWidget`: built from other widgets in `build()` (`src/nuiitivet/widgeting/widget.py`)
  - `Box`: a container with padding, background, border (`src/nuiitivet/widgets/box.py`)
  - `InteractiveWidget`: every interactive MD3 component (`src/nuiitivet/material/interactive_widget.py`)
  - `Clickable`: an interactive box outside Material (`src/nuiitivet/widgets/clickable.py`)
- **Location**:
  - controls and base: `src/nuiitivet/widgets/<name>.py`
  - layouts: `src/nuiitivet/layout/<name>.py`
  - Material: `src/nuiitivet/material/<name>.py`
- **Material**: `/material-interaction` carries the rules, the design is
  `docs/design/MATERIAL_INTERACTION.md`.
- **Value surface**, when the widget holds something the user sets: read
  `docs/design/WIDGET_VALUE.md`. The value is a public `value` property; that
  is the name the dev tools read, and `describe_state` is no substitute. A
  composite value (several parts in one `value`) has no default shape: decide
  it by the two questions in that document (is the shape self-describing, does
  the widget already declare it) and put the decision in the API review. Never
  copy a sibling's shape because it fit there.
- **API review**: present the class name, the base class, the `__init__`
  parameters and the `value` shape to the user, and wait for approval.

### 2. Implementation

- The file in its directory, the chosen base class
- `__init__` takes content and config, calls `super().__init__()`
- `paint(self, canvas, x, y, width, height)` when needed, side-effect free
- `layout(self, constraints)` only for custom layout

### 3. Registration

- General widgets: `src/nuiitivet/widgets/__init__.py`
- Material widgets: `src/nuiitivet/material/__init__.py`

### 4. Testing

- `tests/material/test_<name>.py` or `tests/test_<name>.py`, with the
  `conftest.py` fixtures
- `uv run pytest tests/test_<name>.py`

## Matching MD3 Specs to Layout

An MD3 measurement is a component-box dimension; a widget carries internal
padding, so it does not map 1:1 to Nuiitivet sizing. Verify empirically, never
tune by feel.

- **Padding order is `(left, top, right, bottom)`**, not CSS clockwise
  (`normalize_padding` in `src/nuiitivet/layout/metrics.py`). The wrong order
  silently swaps top and bottom.
- **A widget box is larger than its glyph**:
  - `IconButton` (40dp) centres a 24dp icon, about 8dp of padding a side; the
    40dp box *is* the MD3 `menu-button.container`. Measure to the box.
  - `Button` (text) enforces a 48dp minimum touch target; an MD3 40dp button is
    `ButtonStyle.text().copy_with(container_height=40, min_height=40)`.
  - Text centred in an oversized cell adds phantom space; size the cell to the line.
  - A 40dp circle plus an 8dp gap is the 48dp MD3 pitch; a grid box is `6*40 + 5*8 = 280`.
- **Compose box to box**: set each section's padding so the box-to-box gaps
  equal the MD3 values and the blocks sum to the container height. With
  content shorter than the container, `main_alignment="space_between"`
  inflates every gap; use exact sums with `gap=0`.
- **Probe before claiming a match**: monkeypatch `Widget.set_last_rect` to
  record rects, `app.render_to_png(...)`, print glyph and box positions
  relative to the container. Probes live in `scripts/dev/` and are deleted
  when done.

## Parameter Ordering

```python
def __init__(
    self,
    text: str,                    # 1. Content/Essentials (positional)
    *,
    on_click: Callable,           # 2. Configuration (behavior/event handlers)
    disabled: bool = False,       # 2. Configuration (state flags)
    width: SizingLike = None,     # 3. Layout
    height: SizingLike = None,    # 3. Layout
    padding: ... = 0,             # 3. Layout
    color: Color = "blue",        # 4. Style/Appearance
):
```

## Docstrings

The class, `__init__`, and every public method and factory have one, Google
style. `__init__` and each method carry their own `Args:`; the class docstring
holds no parameter list and names the other constructors. The rules and the
test: `/refactor`, Docstrings.

```python
class MyWidget(Widget):
    """One-line summary.

    What the caller can observe about the widget as a whole.
    From a data collection: `builder`.
    """

    def __init__(self, text: str, *, width: SizingLike = None) -> None:
        """Initialize MyWidget.

        Args:
            text: The text to display.
            width: Width specification. Defaults to auto.
        """
```

## Checklist

- [ ] File in the right directory
- [ ] The right base class
- [ ] `__init__` handles its arguments and calls `super()`
- [ ] Interactive: state layer and focus indicator drawn
- [ ] A user-set value is published as `value`; a composite `value`'s shape was reviewed
- [ ] Exported in the right `__init__.py`
- [ ] Test file created and passing (`uv run pytest tests/...`)
