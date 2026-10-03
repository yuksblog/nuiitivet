# Theme Consumption

A widget obtains the theme one way: it reads `Theme.of(context)` where the
value is consumed, and the read registers the dependency. There is no
per-widget choice between pull and push, because a choice fails quietly:
a widget that resolves once and keeps the value shows the light default
forever and looks correct in a light app, and a widget that resolves in
`on_mount` hands a preset to anything that measures it before mount, such as
auto window sizing measuring a card against a 0px border preset. Both are
lifecycle-ordering bugs, and the fix is removing the choice.

## The Rule

1. **Read the theme; never hold it.** A widget obtains the theme only
   through `Theme.of(context)`.
2. **Reading registers a dependency.** The framework records that the reader
   depends on the theme and invalidates it on a change. Widget authors never
   subscribe and never unsubscribe.
3. **Read in the phase that consumes the value**, which the widget's shape
   decides. A widget with a `build()` reads there and nowhere else. A leaf has
   no `build()`, so it reads in `paint()` or `preferred_size()`.
4. **Never read in `on_mount()` or `__init__()`.** What is resolved once and
   kept on a field is never corrected.

"Never hold it" means: never keep a resolved value somewhere the framework
cannot invalidate. A value read in `build()` and embedded in the returned tree
is held, and that is fine, because a theme change discards that tree. A value
read in `on_mount` and written to a field that survives rebuilds is not. This
is the trade Flutter makes: `ThemeData` holds concrete colours with no
late-binding indirection, and correctness comes from rebuilding the readers.

## Reading Registers a Dependency

`Theme.of(context)` resolves the nearest `AppScope` by walking `_parent`
upward, and records that the current reader depends on the theme. The walk
runs once per mount, not once per read: a widget changes tree only through
`mount()` and `unmount()`, so the scope it resolved is remembered until one
of those runs (`context_lookup.find_app_scope`); a read that finds no scope
remembers nothing, so a widget measured before it is attached resolves the
real scope on its next read.

The reader is whichever unit the framework can invalidate:

| Read during | Reader | Invalidated by a theme change |
| --- | --- | --- |
| `build()` | the enclosing recomposition scope | that scope is rebuilt |
| `layout()` / `preferred_size()` | the widget | the widget is re-measured |
| `paint()` | the widget | the widget is repainted |

On a change the provider calls nobody back. `ThemeManager` bumps a generation
counter and fires its one `on_change` hook, owned by the `AppScope`, which
walks its subtree and invalidates the readers marked theme-dependent. The
walk is O(tree), and a theme change is a user action, not a per-frame event.

The mark lives on the reader, never on the provider. A provider holding a
set of consumer callbacks, the shape this replaced, is a strong reference
from the provider to every consumer: a widget that forgets to unsubscribe
stays resident for the app's lifetime, and forgetting is silent. A mark on
the reader dies with the reader, so there is nothing to release, as in
Flutter (the `Element`) and Compose (the recomposition scope). A
weak-referenced registry at the provider was rejected: it invalidates more
precisely but reintroduces a registry, dead-entry sweeping and a place for
lifetime bugs, for precision that is not worth it at this event rate.

A theme change re-measures as well as repaints. Light/dark switching
changes only colour roles, so nothing moves, but a theme may carry different
typography or shape and the framework cannot tell the two apart from outside.

## Where a Widget Reads

| Widget | Reads in | Not in |
| --- | --- | --- |
| Has a `build()` | `build()` | anywhere else |
| Is a leaf | `paint()`, `preferred_size()` / `layout()` | anywhere else |
| Either | | `on_mount()`, `__init__()` |

There is no third column of judgement. Of the modules that read `Theme.of`,
only `Card` has a `build()`; `Text`, `Icon`, `Divider`, `Slider`, the
scrollbar, the indicators, `EditableText`, the selection controls, the
chips, the buttons and `TextField` are leaves. Leaves are the theme readers,
and they are the build output of something else.

The two phases trade opposite costs: a `build()` read costs nothing per frame
and a scope rebuild per change; a `paint()` / `layout()` read costs one
lookup per frame and a repaint per change. Where there is a choice, build
time wins, since frames are continuous and theme changes rare; but a
composable has no reason to defer to paint, and a leaf cannot take the
advice at all, so the phase is not a preference. The per-frame cost on the
leaf side is kept to a few attribute reads: the scope is cached per mount,
the manager hands out the current theme without a lock, and a style the
theme does not override is one shared frozen object.

Most widgets need no theme code. `Box` resolves background, border and
shadow at paint time, so anything built on it follows the theme; a widget
with a colour or typeface of its own reads `Theme.of(self)` at the point of
use, resolving on every access and holding nothing.

### When a Resolved Value Has to Rest on a Field

Some values cannot be re-derived in a getter on every frame: `Card`'s style
lands on `Box` properties, a chip's style also picks its content subtree, and
a button's colours become concrete RGBA endpoints for running animations.
`Text`, `Checkbox` and `Switch` are painted on every frame of a scroll, so
they keep their colours, and `Text` its typeface.
These keep the derived visuals on fields, but the field is a cache of the
pull, re-applied whenever a fresh read says the theme has moved, so rule 1
holds. What "moved" means differs for a reason:

| Widget | Re-applies when |
| --- | --- |
| `Card` | always; `build()` re-resolves, and rebuilding is the theme-change path |
| The chips | the resolved `ChipStyle` differs from the applied one |
| The buttons | `ThemeManager.generation` has advanced (`theme_generation(self)`) |
| `Text`, `Checkbox`, `Switch` | the generation has advanced, or the key the value was resolved under differs (`ThemeKept`) |

A button cannot compare the derived value the way a chip does, because
re-targeting a colour animation on every measure would disturb one in
flight. The painted leaves cannot either: resolving the value is the cost
their field avoids. They hold it in a `ThemeKept`, whose key carries what
decides the value besides the theme: the style object, which a parent
replaces to recolour a label and which moves no generation, and for the
selection controls the disabled flag and the value. A widget outside an
`AppScope` keeps nothing, since no theme change reaches it.

A `ThemeKept` holds colours, never a Skia paint. A paint held per widget has
to be dropped on every path that changes a colour, and a frame of a colour
animation changes it on every paint. `shared_paint` hands out one paint per
distinct colour and stroke, so a paint is found by what it draws and no path
can leave a stale one behind.

And no widget compares the `Theme` object: `Theme` is frozen, but its
`extensions` list and a `MaterialThemeData`'s `roles` dict are not, so a theme
mutated in place and re-installed is a real change arriving on the same
object; the generation counter moves regardless. A chip's pushed visuals
materialise when it is first measured, not mounted, which in an app is
invisible since layout runs before paint. A button's held RGBA is the one
value a stale read cannot self-correct, which is why its check is the strict
one. Adopting at mount without that re-check is as broken as reading in
`__init__`, only harder to notice.

### The Framework's Side

Widgets can honour the rule only if the chain they walk is intact. A
composable parents its build result when it builds, not when it mounts
(`BuilderHostMixin._adopt_built`), so a pre-mount measurement resolves
ancestors instead of dead-ending; a host that returns `self` from `build()`
is skipped, or it would become its own parent. A `ChildrenStore` clears a
child's `_parent` only while it still points at that store's owner, so
re-parenting before the old owner drops the child does not orphan it. And the
app installs the `AppScope` and mounts the tree before it measures anything;
measuring first would resolve every lookup against the default light theme
and size the window for a theme the app never installed.

### Enforcement and Its Limit

`Theme.of` raises when `context` has no `_parent` attribute at all, which can
only mean the call ran before `super().__init__()`: there is no chain to
resolve and no identity to hang a dependency on. Flutter takes the same
position for `of(context)` in `initState`.

A read in `__init__` after `super().__init__()` is not rejected, by choice.
At that point the widget has `_parent is None` and is not mounted, a state
indistinguishable from a constructed widget being measured offscreen, which
tests and preview tooling do; raising would forbid `Switch().style`. Telling
the two apart needs machinery that knows a constructor is on the stack, and
under a pull the early read is harmless on its own: the fallback (a bare
light `Theme`) is self-correcting on the next attached read, and what makes
it a bug is keeping the result, which rule 1 forbids. So the rule is enforced
where it is cheap and unambiguous and carried by review where it is not.

A read from an event handler, a timer or other imperative code registers the
context widget like any other read; it is neither an error nor a special
case, and no untracked read API exists. No widget in the framework reads the
theme outside build, layout or paint (hover and press animate a float
opacity while the colour stays an unresolved `ColorSpec` resolved at paint),
so phase tracking would reject a pattern nothing uses, and the harm it would
guard against is already forbidden by rule 1. A spurious dependency costs at
most one repaint on a rare user action.

## Prior Art

| Framework | Model |
| --- | --- |
| Flutter | `Theme.of(context)` registers the Element as a dependent; a change rebuilds dependents; `initState` is an error |
| Jetpack Compose | Reading a `CompositionLocal` subscribes the enclosing recomposition scope |
| SwiftUI | `@Environment` reads declare a dependency; views are value types, so holding a stale value is impossible |
| React | `useContext`, the same shape |
| UIKit | Late-bound colours resolved at draw; everything else re-read in `traitCollectionDidChange` |
| Qt / GTK | Palette read at paint; the framework calls `changeEvent` / emits `style_updated` |

The declarative frameworks converge: the author writes a pull, the framework
wires the invalidation, nobody subscribes. The retained-mode frameworks
provide a framework-called hook rather than a subscription; none asks the
author to pair subscribe with unsubscribe. No framework surveyed extends
late-binding tokens beyond colour, so typography and shape are handled by
recomputation, not by `ColorRole`-style tokens for `border_radius` or
`font_family`.

`Theme`, `Geometry` and `Navigator` share one shape, a value supplied by an
ancestor and consumed by descendants, and `theme/dependency.py` (marking
readers, walking a provider's subtree) knows nothing theme-specific. It is
scoped to the theme because that is where the failures were observed.

## Where This Lives

| Piece | Module |
| --- | --- |
| Reader marking, subtree invalidation, `theme_generation`, `ThemeKept` | `theme/dependency.py` |
| The read and the `__init__` guard | `Theme.of` in `theme/theme.py` |
| Attributing a read to the building host | `evaluate_build` in `widgeting/widget_builder.py` |
| Turning a theme change into invalidation | `AppScope._on_theme_changed` in `runtime/app.py` |
| The single owner hook and the generation counter | `theme/manager.py` |
