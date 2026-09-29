# Overlay System Design

`Overlay.show()` puts a layer on top of the window; `Navigator.push()`
changes the screen beneath it. The two are siblings over the transition
kernel in `nuiitivet.transition`, drawn in [NAVIGATION.md](NAVIGATION.md),
and the overlay imports nothing from `navigation`. The overlay keeps a
private layer stack, a `StackRuntime` whose elements are overlay layers,
each wrapping one `OverlayEntry` with its transition.

## One Overlay per Window

`Overlay.of(context)` resolves the window's overlay. The ancestor search
runs first, as the hook for a nested scope, but the window composes its
overlay as a sibling of the navigator, not an ancestor of the content, so an
ancestor walk alone never reaches it; the fallback resolves it through the
window scope, per window and never process-global. `Overlay.of(context,
root=True)` skips the search.

`Overlay` has no `child` and does not nest. The unit that blocks input is
the window scope, as with Qt Quick's `Overlay.overlay` and the browser's
top layer; local layering is `Stack`. A region that needs a modality
narrower than the window would nest the scope itself, which no in-tree case
asks for.

The core `OverlayProtocol` (`overlay/protocols.py`) covers `close()` only,
since the presentation helpers live on `MaterialOverlay`;
`MaterialOverlayProtocol` (`material/protocols.py`) adds `dialog`,
`snackbar`, `loading`, `while_loading`, `side_sheet` and `bottom_sheet`, and
is exported as `nv.OverlayProtocol`, the same aliasing as `nv.Overlay` for
`MaterialOverlay`.

## The Core Names Mechanisms

`Overlay` provides `show()` and nothing scenario-specific. It presents a
widget; how the widget is presented, the transition included, is keyword
arguments. Intent resolution is not the core's: a subclass such as
`MaterialOverlay` resolves an intent to a widget through an
`IntentResolver`. Presets are owned by two consumers, `MaterialOverlay` for
`dialog()` / `snackbar()` / `loading()` / `while_loading()` / `side_sheet()`
/ `bottom_sheet()`, and the modifier layer for `popup()` / `tooltip()` /
`context_menu()`. "Modal", "modeless" and "light dismiss" are scenario
vocabulary and do not appear in the core.

`show()` is parameterised by the axes that vary, not by a scenario name.
`passthrough` is input: `False` installs a full-screen blocking layer that
occludes everything below, pointer and keyboard. `dismiss_on_outside_tap` is
input: a tap outside the content closes the entry, and it requires
`passthrough=False`. `backdrop` is appearance only: whether the composer
paints a backdrop, named after the CSS `::backdrop` pseudo-element; blocking
is `passthrough`'s job. `timeout`, `position` and `transition` complete the
set. The two input axes form a 2×2 whose fourth cell cannot be implemented:

| | outside tap does nothing | outside tap dismisses |
| --- | --- | --- |
| `passthrough=False` | blocking (dialog) | outside-tap dismissal (menu) |
| `passthrough=True` | pass-through (toast, tooltip) | `ValueError` |

Pointer dispatch resolves a single hit target and then walks parents only,
so a layer can pass a tap through, by not being the hit target, or observe
it, by being the hit target, never both. The combination raises rather than
silently ignoring a flag.

### The Core Owns Input, the Composer Owns Paint

| Responsibility | Owner | Where |
| --- | --- | --- |
| Paint: backdrop colour, opacity animation | design system | `OverlayLayerComposer.compose` |
| Z-order | core | `Overlay.show` |
| Block pointer input | core | a `HitParticipationBox` that descends and catches |
| Dismiss on outside tap | core | an interaction region with `any_button=True` around that box |
| Keep the backdrop out of input | core | a `HitParticipationBox` that neither descends nor catches |
| Block keyboard and focus | core | `occluding_content_widget()` |

A composer paints two things and stacks neither. `compose()` returns an
`OverlayLayerPaint(content, backdrop=None)`, the layers side by side, and
the core assembles them: the backdrop in a box that never catches, the
blocker in an interaction region, the content on top and hit-tested first.
A layer that does not apply is omitted, and a single remaining layer is
returned without the `Stack`. `OverlayLayerCompositionContext` carries
visual facts only, `content`, `transition_state`, `position_content` and
`backdrop`; there is no barrier colour, dismissibility flag or `passthrough`
on it, because a composer needs none of them to paint. The Material scrim
colour lives in `MaterialOverlayLayerComposer` from the theme's
`ColorRole.SCRIM`, and the default composer's neutral fallback is a private
constant, so no design-system colour appears in a core default.

Two consequences. `passthrough` has consumers on both sides of the boundary:
its pointer half is the blocking layer built in `show()`, its keyboard half
is read off the layer by `occluding_content_widget()`, which drives the modal
focus trap and `FOREGROUND` shortcut scoping. And a painted backdrop would
otherwise steal the outside tap, since a painted surface is a hit target
("painted = clickable", [HIT_TESTING.md](HIT_TESTING.md)); returning it as a
separate layer is what lets the core make it click-through, so a third-party
composer cannot break blocking or dismissal by omission. Outside-tap
dismissal fires when the blocking layer receives a pointer event with any
button, and cannot fire when the content covers the whole viewport.

### Position

`OverlayPosition` is the single placement type, built through named
constructors: `aligned` relative to the overlay root, `anchored` relative to
a widget's screen rect, `at_point` and `at_pointer` relative to a screen
point. Every kind exposes the same `make_position_content(content)` hook,
so a show API takes one position argument and never branches on the kind. A
point has no extent, so the point kinds take no `target_anchor`, only
`content_anchor`, and are `anchored()` over a zero-size rect. Anchored and
point positions clamp to the viewport by default, so content near an edge
is pulled back into view rather than clipped; the aligned kind is inside by
construction. `alignment` is the nine-point vocabulary of
[LAYOUT.md](LAYOUT.md).

### Handle and Result

`show()` returns an `OverlayHandle[T]`: `handle.close(value)` closes that
entry, and `await handle` yields an `OverlayResult(value, reason)` with a
`reason` of `CLOSED`, `OUTSIDE_TAP`, `TIMEOUT` or `DISPOSED`. The await never
hangs: an entry removed without an explicit close, by a closed window, an
unmount or a navigation, completes with `DISPOSED`, and the caller branches
on `reason`. Unmounting the overlay removes every open entry at once without
exit transitions, with one exception: on a hot reload an entry shown from an
intent hands its handle to the rebuilt overlay and completes there
([HOT_RELOAD.md](HOT_RELOAD.md)). The async runtime beneath the await is in
[ASYNCIO_INTEGRATION.md](ASYNCIO_INTEGRATION.md).

## MaterialOverlay

`MaterialOverlay` subclasses `Overlay`. `MaterialOverlay.of(context)` is
parameterised on the calling class, so the subclass type is preserved and
the lookup fails if the resolved overlay is not a `MaterialOverlay`. Its
`dialog()`, `side_sheet()`, `bottom_sheet()` and `loading()` accept a widget,
shown as is, or anything else, resolved through the `IntentResolver`; either
way the method supplies the MD3 transition and position, so a registered
intent cannot change how its entry enters. Sheet placement (`side`,
`dismiss_on_outside_tap`) stays on the method; carrying it on the intent was
rejected because it is how the sheet is presented, not what it shows. A
resolver is injected, or an `intents` mapping builds one; `BasicDialogIntent`
and `LoadingIntent` are registered by default.

`Window` takes its overlay as it takes its content, an instance or a
zero-argument factory. A hot reload re-invokes the factory, because an
intents table references user classes that a reload replaces; an instance
keeps the window hot-reload inert. Omitted, the overlay is the window
class's default, `Overlay` for `Window` and `MaterialOverlay` for
`MaterialWindow`, and the navigator default is a separate hook, so replacing
the overlay alone keeps `MaterialNavigator`. A window-level `intents` keyword
was rejected as a second path to the same overlay, exclusive with the
factory.

## The Layer Stack

Rendering order is insertion order: a later entry paints on top. Numeric
z-indexes were rejected as complexity nothing needs, and "later openings are
on top" matches what users and Flutter expect.

The modal navigator owns one `Stack` for the life of the overlay. Showing an
entry appends its layer; closing one removes that layer once its exit
animation has finished; the other layers are untouched, so an entry's widget
mounts once, when shown, and unmounts once, when its entry closes.
Rebuilding the whole `Stack` on every show or close was rejected: it
remounts every live entry, and a `Menu` drops the keyboard focus it holds on
unmount, so opening a submenu left its parent menu deaf to the arrow keys.
An unmount is therefore not a dismissal signal either, since the widget also
leaves the tree when the overlay's host does with the entry still open; a
widget that must know it was closed reads the handle's settled result
(`handle.done()`, `await handle`).

`Overlay.close(...)` closes the topmost entry, which is the overlay's whole
part in back handling; the order between overlay and navigator is in
[NAVIGATION.md](NAVIGATION.md).
