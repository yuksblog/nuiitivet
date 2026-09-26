# Overlay System Design

## 1. Core Architectural Structure

### 1.1 Relationship Between Overlay and Navigator

`Overlay.show()` puts a layer on top of the window. `Navigator.push()` changes the screen beneath it. The two are siblings over the transition kernel in `nuiitivet.transition`, and the overlay imports nothing from `navigation`. [NAVIGATION.md](NAVIGATION.md) draws the pair.

The overlay keeps a private layer stack: a `StackRuntime` whose elements are overlay layers. Each layer wraps one `OverlayEntry` together with its transition.

The `Overlay` core provides only `show()`. Scenario-specific APIs (dialogs, snackbars, etc.) live on subclasses.

## 2. Overlay API Design

### 2.1 API Consistency with Navigator

- Each window owns one Overlay, reached through the same context lookup as its navigator.
  - `Overlay.of(context)`: the window's overlay. The ancestor search runs first, as the hook for a nested scope; the window is the only scope today.
  - `Overlay.of(context, root=True)`: skips the ancestor search.
  - The window composes its Overlay as a *sibling* of the Navigator, not as an ancestor of the content, so an ancestor walk alone would never reach it. The fallback resolves it through the window scope instead — per window, never a process-global.
- `Overlay` has no `child` and does not nest. The unit that blocks input is the window scope, as with Qt Quick's `Overlay.overlay` and the browser's top layer. Local layering is `Stack`.
- Protocols are provided to ensure ViewModels do not depend on implementation details.
  Core `OverlayProtocol` (`nuiitivet.overlay.protocols`) covers `close()` only, since the
  presentation helpers live on `MaterialOverlay`; `MaterialOverlayProtocol`
  (`nuiitivet.material.protocols`) extends it with `dialog` / `snackbar` / `loading` /
  `while_loading` / `side_sheet` / `bottom_sheet`, and is exported as `nv.OverlayProtocol`
  — the same aliasing as `nv.Overlay` for `MaterialOverlay`.

### 2.2 Overlay Core provides only `show()`

- `Overlay` provides only the generic `show()` and no scenario-specific APIs like `dialog`, `snackbar`, or `sheet`.
- It presents widgets only. The widget is the content; how it is presented, the transition included, is the keyword arguments.
- Intent resolution (`Intent -> Widget`) is not performed by `Overlay`.
- Intent resolution is provided by subclasses (e.g., `MaterialOverlay`) using an `IntentResolver`.

Presets are owned by **two** consumers, not one:

- `MaterialOverlay` — `dialog()` / `snackbar()` / `loading()` / `while_loading()` / `side_sheet()` / `bottom_sheet()`
- the modifier layer — `popup()` / `tooltip()` / `context_menu()`

"Modal", "modeless" and "light dismiss" are scenario vocabulary and deliberately
do **not** appear in the core. The core names mechanisms.

### 2.3 Core API: three orthogonal axes

`Overlay.show()` is the single core API for displaying content on the topmost
layer. It is parameterised by the axes that actually vary, rather than by a
scenario name.

```python
def show(
    self,
    content: Widget,
    *,
    passthrough: bool = False,
    dismiss_on_outside_tap: bool = False,
    backdrop: bool = False,
    timeout: float | None = None,
    position: OverlayPosition | None = None,
    transition_spec: TransitionSpec | None = None,
) -> OverlayHandle[Any]:
    ...
```

#### Parameters

- `passthrough` — **input**. `False` (default) installs a full-screen blocking
  layer and occludes everything below, for both pointer and keyboard.
- `dismiss_on_outside_tap` — **input**. Closes the entry when a tap lands
  outside the content. Requires `passthrough=False`.
- `backdrop` — **appearance**. Whether the layer composer paints a backdrop
  behind the content. Purely visual; blocking is `passthrough`'s job. The name
  is borrowed from the CSS `::backdrop` pseudo-element.
- `timeout: float | None` — seconds until auto-dismissal; `None` never closes.
- `position: OverlayPosition | None` — `None` is equivalent to "center".
- `transition_spec` — enter/exit animation for the entry.

The two input axes form a 2×2 whose fourth cell is not implementable today:

| | `dismiss_on_outside_tap=False` | `dismiss_on_outside_tap=True` |
| --- | --- | --- |
| `passthrough=False` | blocking (dialog) | outside-tap dismissal (menu) |
| `passthrough=True` | pass-through (toast, tooltip) | `ValueError` |

Pointer dispatch resolves a **single** hit target and then walks parents only,
so a layer can pass a tap through (by not being the hit target) or observe it
(by being the hit target) — never both. `passthrough=True` with an explicit
`dismiss_on_outside_tap=True` raises `ValueError` rather than silently
ignoring the flag.

#### Responsibility split: the core owns input, the composer owns paint

| Responsibility | Owner | Where |
| --- | --- | --- |
| Paint (backdrop colour, opacity animation) | design system | `OverlayLayerComposer.compose` |
| Z-order / stacking | core | `Overlay.show` |
| Block pointer input | core | `Overlay.show` — a `HitParticipationBox` that descends and catches |
| Dismiss on outside tap | core | `Overlay.show` — an interaction region with `any_button=True` around that box |
| Keep the backdrop out of input | core | `Overlay.show` — a `HitParticipationBox` that neither descends nor catches |
| Block keyboard / focus | core | `occluding_content_widget()` |

A composer paints two things and stacks neither. `compose()` returns an
`OverlayLayerPaint(content, backdrop=None)` — the layers side by side rather
than pre-stacked — and the core assembles them:

```text
Stack(children=[
    HitParticipationBox(backdrop, descend=False, opaque=False),  # decoration; never catches
    blocker,             # HitParticipationBox(descend=True, opaque=True) [in an interaction region]
    content,             # tested first (children reversed)
])
```

Each layer is omitted when it does not apply (`backdrop=False`,
`passthrough=True`), and a single remaining layer is returned without the
`Stack`.

`OverlayLayerCompositionContext` carries **visual facts only**: `content`,
`transition_state`, `position_content` and `backdrop`. There is no
`barrier_color`, `barrier_dismissible`, `on_barrier_click` or `passthrough` on
it — a composer needs none of them in order to paint. The Material scrim colour
lives in `MaterialOverlayLayerComposer` (from the theme's `ColorRole.SCRIM`),
and `_DefaultOverlayLayerComposer`'s neutral fallback is a private constant; no
design-system colour appears in a core default.

Two consequences are worth stating explicitly:

- **`passthrough` has consumers on both sides of the boundary.** Its pointer
  half is the blocking layer built in `show()`; its keyboard half is read
  straight off the layer by `occluding_content_widget()`, which drives the modal
  focus trap and `FOREGROUND` shortcut scoping. Removing it from the
  *composition context* does not remove it from the *layer*.
- **A painted backdrop would otherwise steal the outside tap.** A painted
  surface is a hit target in this framework ("painted = clickable",
  `Box._hit_self_opaque`), so a backdrop left alone would win the hit test over
  the blocking layer beneath it. Returning it as a separate layer is what lets
  the core make it click-through itself. Enforcement therefore does not
  depend on a composer remembering anything: a third-party composer cannot break
  blocking or dismissal by omission.

#### Definition of "Outside-tap"

- "Outside" is defined based on the hit-testing rules in [BOX_MODEL.md](BOX_MODEL.md).
- Outside-tap dismissal fires when the core's blocking layer receives a pointer
  event, for **any** button — primary, secondary or middle.
- If the content covers the entire viewport, outside-tap dismissal will not function.

### 2.4 Positioning: `OverlayPosition`

`OverlayPosition` is the single type describing placement. Instances are built
through named constructors; every kind exposes the same
`make_position_content(content) -> Widget` hook, so the show APIs take one
position argument and never branch on which kind they were given.

- `OverlayPosition.aligned(alignment: str = "center", *, offset=(0, 0))` — relative to the overlay root
- `OverlayPosition.anchored(rect_provider, target_anchor, content_anchor, offset, *, clamp=True)` — relative to a widget's screen rect
- `OverlayPosition.at_point(x, y, *, content_anchor, offset, clamp=True)` — relative to a screen point
- `OverlayPosition.at_pointer(event, *, content_anchor, offset, clamp=True)` — relative to a `PointerEvent`'s screen point

`alignment` follows the vocabulary for single-child alignment defined in [LAYOUT.md](LAYOUT.md).

- `"top-left"`, `"top-center"`, `"top-right"`
- `"center-left"`, `"center"`, `"center-right"`
- `"bottom-left"`, `"bottom-center"`, `"bottom-right"`

`offset` is applied after placement.

A point has no extent, so `at_point` / `at_pointer` take no `target_anchor`:
`content_anchor` alone decides which corner of the content lands on the point.
Internally they are `anchored()` over a zero-size rect.

Anchored and point positions clamp their content to the viewport by default, so
content placed near an edge is pulled back into view rather than clipped. The
aligned kind needs no clamping: it is inside by construction.

- Unit: px.
- Coordinate system is the overlay root's layout space.
  - $+x$ is right.
  - $+y$ is down.

### 2.5 `OverlayHandle` / `OverlayResult`

`Overlay.show()` returns an `OverlayHandle[T]`.

- `handle.close(value)` closes the specific entry associated with the handle.
- `await handle` returns a structured result.

```python
class OverlayResult[T]:
    value: T | None
    reason: OverlayDismissReason


class OverlayDismissReason(Enum):
    CLOSED = ...
    OUTSIDE_TAP = ...
    TIMEOUT = ...
    DISPOSED = ...
```

#### Result Semantics

- `handle.close(value)` -> `OverlayResult(value=value, reason=CLOSED)`
- Outside-tap -> `OverlayResult(value=None, reason=OUTSIDE_TAP)`
- Timeout -> `OverlayResult(value=None, reason=TIMEOUT)`
- Entry discarded without explicit close -> `OverlayResult(value=None, reason=DISPOSED)`

`await handle` is guaranteed not to wait indefinitely (even completed on disposal).

### 2.6 Subclass APIs (MaterialOverlay, etc.)

Scenario-specific APIs are moved to subclasses.

#### Responsibilities of MaterialOverlay

`MaterialOverlay` is implemented as a subclass of `Overlay` and provides Material-specific resolution and shortcut APIs.

- Inheritance: `MaterialOverlay(Overlay)`
- Retrieval:
  - `MaterialOverlay.of(context)`: the nearest ancestor `MaterialOverlay`, falling back to the App's. The lookup is parameterised on the calling class, so the subclass type is preserved; it fails if the resolved overlay is not a `MaterialOverlay`.

#### Intent Resolution

- `MaterialOverlay.dialog(...)` accepts `Widget | Any`.
  - A `Widget` is displayed as-is.
  - Everything else is resolved to a `Widget` via `IntentResolver.resolve(intent)`.
  - Either way, `dialog()` supplies the MD3 dialog transition. An intent factory returns content only, so a registered intent cannot change how its dialog enters.
- `MaterialOverlay` allows for `IntentResolver` injection.
  - Alternatively, pass `intents: Mapping[type[Any], Callable[[Any], Widget]]` (internally builds a mapping resolver).
- Register standard intents by default:
  - `BasicDialogIntent`
  - `LoadingIntent`

#### Provided APIs (v1)

- `MaterialOverlay.dialog(...)`
  - Blocks background input by default (modal).
  - `dismiss_on_outside_tap` is optional.
    - Default is `False` for `LoadingDialogIntent`.
    - Default is `True` for others.
- `MaterialOverlay.snackbar(message, *, duration=3.0)`
  - `message` accepts `str` or `Snackbar`, displayed with the default snackbar transition.
  - Background input remains interactive (`passthrough=True`).
  - Automatically dismisses after `timeout=duration`.
  - Default position: `OverlayPosition.aligned("bottom-center", offset=(0, -24))`.
- `MaterialOverlay.loading(indicator=None)` → `OverlayHandle[Any]`
  - Displays the loading indicator and returns a handle for manual dismissal.
  - `handle.close(None)` dismisses the overlay.
- `MaterialOverlay.while_loading(indicator=None)` → context manager
  - Displays `LoadingIntent` and ensures it closes upon exiting the block (sync or async).

### 2.7 Supplying the Window's Overlay

`Window` takes its overlay the way it takes its content: an `Overlay` instance or a zero-argument factory. A hot reload re-invokes the factory, because an intents table references user classes that a reload replaces. An instance keeps the window hot-reload inert.

Omitted, the overlay is the window class's default: `Overlay` for `Window`, `MaterialOverlay` for `MaterialWindow`. The navigator default is a separate hook, so replacing the overlay alone keeps `MaterialNavigator`.

A custom intents table is an argument of the overlay, not of the window. A window-level intents keyword was rejected: it was a second path to the same overlay, exclusive with the factory.

### 2.8 Note: Scope of core APIs

- `Overlay.show()` is not responsible for intent registration or providing standard dialog/widgets.
- Standard UI components (e.g., `BasicDialog`, `LoadingDialog`) and intents are provided by `MaterialOverlay`.

## 3. Asynchronous Processing and Lifecycle

- For the big picture (threads × asyncio × UI thread), see [CONCURRENCY_MODEL.md](CONCURRENCY_MODEL.md).
- Details on the execution foundation (async runtime) and event loop integration are centralized in [ASYNCIO_INTEGRATION.md](ASYNCIO_INTEGRATION.md).
- The Overlay's responsibility is to ensure that `await handle` never hangs.
  - If an entry is removed without being explicitly closed, it completes with `OverlayDismissReason.DISPOSED`.
  - The caller can branch based on `OverlayResult.reason`.

## 4. Layer Stack

### 4.1 Rendering Order

Rendering order is controlled by insertion order (later entries are rendered on top), eliminating the need for explicit Z-index management.

#### Design Intent (Rendering Order)

- Managing numerical Z-index values adds complexity that is unnecessary for initial requirements (YAGNI).
- Matching the intuition that "later openings are on top" aligns with user expectations and consistency with other frameworks like Flutter.

### 4.2 Layer Lifetime

The modal navigator owns one `Stack` for the life of the overlay. Showing an
entry appends its layer to that `Stack`; closing one removes that layer once
its exit animation has finished. The other layers are not touched: an entry's
widget mounts once, when it is shown, and unmounts once, when its entry
closes.

An unmount is not a dismissal signal. The widget also leaves the tree when the
overlay's own host does, with the entry still open. A widget that must know it
was closed reads the handle's settled result (`handle.done()`, `await handle`).

Rebuilding the whole `Stack` on every show or close was rejected: it unmounts
and remounts every live entry, and a `Menu` drops the keyboard focus it holds
on unmount, so opening a submenu left its parent menu deaf to the arrow keys.

## 5. Integration with Back / Navigator

Details on Back button priority and `will_pop` are centralized in [docs/design/NAVIGATION.md](NAVIGATION.md).

- The Overlay focus is solely on closing the topmost overlay entry.
- `Overlay.close(...)` is provided as a shortcut to close the topmost entry.

## Pending Matters / Future Considerations

The following items are not finalized in this specification (or require implementation/verification).

### Async / Runtime

- Current behavior is defined in [docs/design/ASYNCIO_INTEGRATION.md](ASYNCIO_INTEGRATION.md).
- Handling strategy for `asyncio.CancelledError`.
- Implementation of Future cancellation notification.
- Policy for error logging (what users should see).
- How to launch coroutines from UI events (integration with the execution foundation).

### ViewModel / Dispose

- Providing helpers like `CompositeDisposable`.
- Organizing ViewModel lifecycle management patterns.
- Mechanism for automatic ViewModel disposal.
- Best practices for the relationship between ViewModels and Widgets.
- Guarding operations on already disposed Widgets.
- Managing state flags after disposal.
- Preventing double calling of `dispose`.

### Rendering / Overlay

- Nested scope: a region that owns its own navigator and overlay, for a modality narrower than the window.
- Design for introducing Z-index in the future.
- Maintaining compatibility (existing code continues to work).
- Rendering optimizations for large numbers of Overlays.
- Skipping rendering for non-visible Overlays.
Details on Back Button / Events are centralized in [docs/design/NAVIGATION.md](NAVIGATION.md).

### Documentation / Prototype

- Finalize the core design of the Intent System.
- Evaluate implementation strategies for Context Lookup.
- Evaluate implementation strategies for asynchronous processing.
- Evaluate implementation strategies for Z-index management.
- Create class and sequence diagrams.
- Draft API references.
- Prioritize implementation tasks and create issues.
- Develop a minimal prototype and identify potential issues.
- Refine the design based on feedback.
