# Theme Consumption

**Status: proposal. Not implemented.**

This document specifies how a widget should obtain the theme. It describes a
target design, not current behaviour — `docs/design/STYLE_THEME.md` §4.1
documents what the framework does today. Motivated by #464, #473 and #476.

## The problem

Today the framework asks each widget author to choose between two ways of
consuming the theme:

- **Pull** — read `Theme.of(self)` at the point of use (`Text`, `Box`'s colours).
- **Push** — resolve once in `on_mount`, subscribe to a `ThemeManager`, and keep
  the value on a field (`Card`, the chips, the buttons).

Neither is wrong in isolation, but making it a per-widget decision means every
new widget re-litigates it, and a wrong choice fails quietly:

- **Resolve and keep, without subscribing.** The widget shows the light default
  forever. It looks correct in a light-themed app. This is what #473 found
  across `Card`, the chips, `TextField` and the floating toolbars.
- **Push, when something reads the value before `on_mount` runs.** The reader
  gets the preset. #476: auto window sizing measured a card against a 0px border
  preset and sized the window 38px wide for a card that needed 62px.

Both failures are lifecycle-ordering bugs. The fix is not better documentation
of the choice — it is removing the choice.

## The rule

1. **Read the theme; never hold it.** A widget obtains the theme only through
   `Theme.of(context)`.
2. **Reading registers a dependency.** The framework records that the reader
   depends on the theme and invalidates it when the theme changes. Widget
   authors never subscribe and never unsubscribe.
3. **Read in the phase that consumes the value — which your widget's shape
   already decides for you.** A widget with a `build()` reads there and nowhere
   else. A leaf widget has no `build()`, so it reads in `paint()` or
   `preferred_size()`. This is not a preference to weigh; it follows from what
   kind of widget you wrote.
4. **Never read in `on_mount()` or `__init__()`.** `__init__` is an error, not
   a warning. `on_mount` is not an error — there is a context by then — but
   nothing legitimate happens there that rule 3 does not place better.

### What "never hold it" means precisely

It does not mean "never let a resolved value rest in a variable". It means:

> Never keep a resolved theme value somewhere the framework cannot invalidate.

A value read in `build()` and embedded in the returned widget tree is held — and
that is fine, because a theme change discards that tree and rebuilds it. A value
read in `on_mount` and written to a field that survives rebuilds is not fine:
nothing will ever correct it.

This is the same trade Flutter makes. `ThemeData` holds concrete `Color` and
`TextStyle` values, with no late-binding indirection; correctness comes from
rebuilding the readers, not from deferring resolution.

## Mechanism: reading registers a dependency

`Theme.of(context)` does two things:

1. resolves the nearest `AppScope` by walking `_parent` upward, and
2. records that the **current reader** depends on the theme.

The "current reader" is whichever unit the framework can invalidate:

| Read during | Reader | Invalidated by a theme change |
| --- | --- | --- |
| `build()` | the enclosing recomposition scope | that scope is rebuilt |
| `layout()` / `preferred_size()` | the widget | the widget is re-measured |
| `paint()` | the widget | the widget is repainted |

On a theme change the provider does not call anybody back. It bumps a
generation counter and invalidates the readers it can reach.

### Why release is automatic

The dependency record must live on the **reader**, never on the provider.

Today `ThemeManager` keeps `Set[Callable]` of bound methods — a strong reference
from the provider to every consumer. A widget that forgets to unsubscribe stays
resident for the App's lifetime. Manual pairing is therefore mandatory, and
forgetting it is silent.

Inverting the reference direction removes the operation entirely: the dependency
is a mark on the reader, so it dies when the reader dies. There is no registry
to clean up and nothing to unsubscribe. This mirrors Flutter (dependencies live
on the `Element`) and Compose (on the recomposition scope), where the framework
owns the object's lifetime and the subscription is a consequence of it.

Concretely, the provider should hold **no** consumer references at all. On a
theme change, `AppScope` walks its subtree and invalidates the widgets and
scopes marked as theme-dependent. That walk is O(tree), but a theme change is a
user action, not a per-frame event.

The alternative — a weak-referenced registry at the provider — invalidates more
precisely but reintroduces a registry, dead-entry sweeping, and a place for
lifetime bugs to live. The precision is not worth it at this event rate.

## Where a widget may read

| Your widget | Read in | Not in |
| --- | --- | --- |
| Has a `build()` | `build()` | anywhere else |
| Is a leaf (no `build()`) | `paint()`, `preferred_size()` / `layout()` | anywhere else |
| Either | — | `on_mount()`, `__init__()` |

There is no third column of judgement calls. A widget that composes reads while
composing; a widget that draws reads while drawing. Nobody weighs a trade-off,
because the widget's shape has already made the decision.

This is not a minority case to be tolerated. Of the twenty modules that read
`Theme.of` today, thirteen have no `build()` at all — `Text`, `Icon`, `Divider`,
`Slider`, `Scrollbar`, the progress and loading indicators, `EditableText`, the
selection controls and the `Box`-derived interactive base. Leaf widgets *are*
the majority of theme readers, and they are the build output of something else.

### Why the phase follows from the widget, not from a preference

The two phases do trade opposite costs:

| Read in | Cost per frame | Cost per theme change |
| --- | --- | --- |
| `build()` | none — `build()` does not run per frame | rebuild the reading scope |
| `paint()` / `layout()` | one lookup per read, every frame | repaint only |

Frames are continuous and theme changes are a rare user action, so where there
*is* a choice, build time is the better side of that trade. But a composable has
no reason to defer to paint, and a leaf cannot take the advice at all. Framing
this as a default to be preferred implies a decision that does not exist, and
leaves the majority of readers with guidance they cannot follow.

The per-frame cost on the leaf side is therefore unavoidable. What that costs
today, and what to do about it, is a property of the implementation rather than
of this rule, and is tracked in #478.

### Enforcement

Only `__init__` is rejected at runtime. A read from anywhere else — including
imperative code that is in no phase at all — is well defined: it registers the
context widget, and that widget repaints on a theme change it would have
repainted for anyway.

The failure this design exists to prevent is not *where* the read happens but
*what is done with the result*, and rule 1 covers that. Classifying call sites
at runtime would mean new phase-tracking machinery whose only job is to catch a
mistake another rule already forbids.

### Why `__init__` is an error, not a warning

Under this design a read *is* a dependency registration. In `__init__` there is
no reader to attribute the dependency to and no parent chain to resolve against,
so the call has no meaning — it is not merely early, it is undefined. Raising
is consistent with every other `of()` API in the framework
(`nuiitivet/widgeting/context_lookup.py`), and it removes the class of bug that
required the #473 audit.

Flutter takes the same position: `of(context)` in `initState` is an error, with
`didChangeDependencies` as the sanctioned alternative. SwiftUI and Compose make
it structurally impossible.

## What this replaces

| Today | Under this design |
| --- | --- |
| `Box` subscribes to invalidate its paint cache | The framework invalidates the reader; `Box` just reads |
| `Card` adopts in `on_mount` and subscribes | It has a `build()`; resolve there and let the rebuild carry the new style |
| The chips adopt in `on_mount` and subscribe | They are leaves; resolve where the style is consumed |
| Buttons subscribe to re-resolve their colour animation targets | They have a `build()`; resolve there |
| `NavigationRail` hand-drives a badge's subscription because the badge is never mounted | No subscription exists to drive |
| `Theme.of` warns when called before mount | `Theme.of` raises in `__init__`; a detached read resolves normally |

## Decided: reads outside build, layout and paint

A read made from an event handler, a timer, or other imperative code registers
the context widget like any other read. It is neither an error nor a special
case, and no separate non-tracking API is provided.

This was reached by looking for the use case rather than reasoning from analogy.
Colour animations looked like the obvious candidate — an interaction handler
capturing endpoints to interpolate between — but that is not how the buttons
work. Hover and press animate a float opacity; the colour stays an unresolved
`ColorSpec` on the widget and is resolved at paint. The buttons resolve colours
only in their theme-change callback and at construction, both of which this
proposal removes.

No widget in the framework reads the theme outside build, layout or paint.

Given that, classifying call sites into phases would mean building runtime phase
tracking whose only payoff is rejecting a pattern nothing uses — and the harm it
would guard against, a stale value kept on a field, is already forbidden by the
first rule. A spurious dependency costs at most one repaint on a rare user
action.

Should a genuine need for an untracked, one-shot read appear later, it should be
designed then, against that use case. Sanctioning a mechanism for it now would
bless a pattern this document exists to remove.

## Prior art

| Framework | Model |
| --- | --- |
| Flutter | `Theme.of(context)` registers the Element as a dependent; change rebuilds dependents. `initState` is an error |
| Jetpack Compose | Reading a `CompositionLocal` subscribes the enclosing recomposition scope; no constructor exists |
| SwiftUI | `@Environment` reads declare a dependency; views are value types, so holding a stale value is not possible |
| React | `useContext` — same shape |
| UIKit | Late-bound colours resolved against the trait collection at draw; everything else re-read in `traitCollectionDidChange` |
| Qt / GTK | Palette/style read at paint; framework calls `changeEvent` / emits `style_updated` |
| Android Views | Attributes read eagerly in the constructor; a theme change recreates the Activity |

The declarative four converge on the same answer: the author writes a pull, the
framework wires the invalidation, and nobody subscribes. The retained-mode
frameworks all provide a **framework-called hook** rather than a subscription —
none of them ask the author to pair subscribe with unsubscribe. nuiitivet is the
outlier in doing so, and #473 is the predictable result.

No framework surveyed extends late-binding tokens beyond colour. The answer for
typography and shape is recomputation, not indirection — which is why extending
`ColorRole`-style tokens to `border_radius` and `font_family` is not proposed
here.

## Generalisation

`Theme`, `Geometry`, `Navigator` and (eventually) locale share one shape: a
value supplied by an ancestor, consumed by descendants, changing over time. The
mechanism above is not theme-specific.

This proposal deliberately scopes itself to the theme, because that is where the
failures have been observed. It should be written so the dependency-registration
machinery can be lifted to a general ambient-context facility later, rather than
baking theme-specific assumptions into it.

## Migration sketch

1. Add dependency registration to `Theme.of`, reusing the existing
   `RecomposeScope` / `_dependency_scope_index` machinery.
2. Move `AppScope` to generation-bump + subtree invalidation; drop
   `ThemeManager`'s subscriber set.
3. Convert `Card`, `TextField` and the buttons — all of which have a `build()` —
   from adopt-at-mount to resolving in `build()`. For the buttons that means the
   colour animation targets.
4. Convert the chips, which have no `build()`, to resolving where the style is
   consumed.
5. Remove `Box`'s invalidation-only subscription.
6. Make `Theme.of` raise in `__init__`; delete the `theme_of_before_mount`
   warning.
7. Delete `NavigationRail`'s hand-driven badge subscription.

Steps 3–7 are each independently shippable once step 1 and 2 land.
