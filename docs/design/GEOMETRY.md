# Geometry: Container-Scoped Measured Geometry

Status: **Accepted — implemented** (tracks issue #431; related to #430)

## 1. Motivation

Some adaptive layouts must react to the size of a **specific container**, not the
whole window — reflow inside one panel regardless of window size, local
breakpoints, etc. Today a widget's measured size is set via
`WidgetKernel.set_layout_rect` (see [widget_kernel.py](../../src/nuiitivet/widgeting/widget_kernel.py))
but never delivered reactively, and there is no supported way to rebuild a
subtree based on the space available to it.

`Geometry` is a widget that measures **its own box** and publishes the result to
its subtree, read reactively via the `Geometry.of(context)` convention. The
window is simply the **root `Geometry` provider**, so the same read path serves
both the window and any nested container (see §7).

## 2. Background: why this is *not* just another environment value

nuiitivet already has an ancestor-lookup convention — `X.of(context)` backed by
`Widget.find_ancestor` — used by [Navigator](NAVIGATION.md) and
[Theme](STYLE_THEME.md). It is tempting to treat "measured size" as one more
value flowing down that mechanism. It is not. Environment values fall into three
families by **where the value comes from**:

| Source | Examples | Nature |
| :--- | :--- | :--- |
| **(A) Author-set** | theme, directionality (LTR/RTL), locale, text style | A literal the author supplies. Set once, inherited down, overridable per subtree. |
| **(B) System-provided at root** | density (DPI), color scheme, safe-area, orientation, text scale | Read-only, but produced **once at the window/root** and inherited unchanged. Behaves like (A). |
| **(C) Layout-derived per node** | **resolved size**, constraints / available space | Produced by the **layout of the specific node itself**. Re-derived at every nesting level, and only known **after** the layout phase (two-phase). |

A generic environment mechanism (SwiftUI `Environment`, Compose
`CompositionLocal`, Flutter `InheritedWidget`) cleanly carries (A) and (B): the
author or the runtime pushes a value in and descendants read it. **(C) cannot be
folded into that**, because:

1. The value differs at every node — each `Geometry` re-measures its own box;
   there is no single root value to inherit.
2. The value is produced by layout, so it exists only in the second phase
   (after build), not when the tree is constructed.

`Geometry` is the **single dedicated provider for family (C)**. Everything in
(A)/(B) belongs to a future general-purpose environment mechanism (see §8), not
here. This is why size gets a bespoke widget while theme/locale/density do not.

## 3. Frame model: why this is safe without re-entrancy

nuiitivet's frame pipeline is strictly **build → layout → paint**, and build
(scope recomposition) is flushed *before* layout within a frame:

- [app.py](../../src/nuiitivet/runtime/app.py) `_render_frame`: `flush_binding_invalidations()` / `flush_scope_recompositions()` run first,
- then `on_draw` performs `root.layout(w, h)`,
- then paint.

A container's measured size is known only during the layout phase. When
`Geometry` publishes a changed size during layout, it writes to an `Observable`.
That write marks the widgets bound to it dirty and schedules the **next** frame;
the bound widgets re-bind in the next frame's build/flush phase — never
mid-layout.

```text
frame N   : layout → Geometry measures → size changed → Observable.set()
            → bound widgets marked dirty → next frame requested
frame N+1 : flush bindings (apply new size to bound widgets) → layout → paint
```

This is the key result: **because binding flush and layout are serialized across
frames, an Observable write during layout is naturally deferred.** The one-frame
latency is imperceptible. This sidesteps the layout-time re-entrancy hazard that a
synchronous, build-during-layout `LayoutBuilder` would expose to callers.

## 4. API

A widget that wraps a single child, is transparent to layout (it passes its
incoming size straight to the child), and publishes its own resolved geometry to
descendants via the `.of(context)` convention.

```python
class Geometry(Widget):
    """Publishes this widget's own measured geometry to its subtree.

    Transparent to layout: the child receives the same size this widget
    receives. Descendants read the measured size reactively via
    ``Geometry.of(context)``.
    """

    def __init__(self, child: Widget) -> None: ...

    @property
    def size(self) -> Observable[Size]:
        """This widget's resolved (width, height), updated after layout.

        A single atomic ``Observable[Size]`` — width and height update
        together so consumers never read a torn (new width, old height) pair.
        """

    @classmethod
    def of(cls, context: Widget) -> "Geometry":
        """Return the nearest ancestor Geometry (nearest provider wins)."""
```

Consumption follows nuiitivet's reactivity rule: **bind the `size` Observable,
do not read `.value` at build time.** `Geometry.of(context).size` is an
`Observable[Size]`; map it into a widget so the widget re-binds when the size
changes. Reading `.value` inside `build()` takes a one-time snapshot that never
updates (build is not re-run on a tracked read — that is not how nuiitivet
reactivity works).

- **Value binding** (labels, colours, thresholds) — map into a value-accepting
  widget:

  ```python
  Text(Geometry.of(self).size.map(lambda s: f"{s.width}px"))
  ```

- **Structural switch** (choose between prebuilt layouts) — drive a `Deck` index
  from the mapped size. `Deck` mounts each variant and shows one by index:

  ```python
  size = Geometry.of(self).size
  Deck(
      children=[_NarrowLayout(...), _WideLayout(...)],
      index=size.map(lambda s: 1 if s.width >= 600 else 0),
  )
  ```

  (`Deck` accepts any read-observable index, including a derived `.map(...)`.)

Because **the nearest provider wins**, "local reflow independent of window size"
falls out for free: put a `Geometry` around a panel and its descendants react to
the panel, not the window. If there is no nearer provider they fall back to an
outer one — ultimately the root `Geometry` installed by the window (§7).

## 5. Value model

- **This issue ships `size` only** — a single `Observable[Size]`.
- **Do not** expose `width` and `height` as separate scalar `Observable`s. A
  coherent `Observable[Size]` updated atomically prevents torn reads. Callers who
  want to react to one axis only can derive a `computed` from `size`.
- Constraints / available space are **future** (§9). Note that nuiitivet's
  layout has **no `BoxConstraints`-style min/max model**: a parent assigns a
  concrete allocated rect, and the only bound in the pipeline is the one-way
  `max_width` / `max_height` hint passed through `preferred_size(...)` during the
  measure phase (see [container.py](../../src/nuiitivet/layout/container.py),
  [column.py](../../src/nuiitivet/layout/column.py)). Exposing "constraints"
  therefore introduces a concept the framework does not otherwise have — it is a
  layout-model extension, not a small add — so it is deliberately out of scope
  here. In practice the resolved `size` already answers "how much space do I
  have" for the common (flex/fill) case.

## 6. Oscillation

Rebuilding a subtree can change the geometry the widget measures, which can
re-fire the update — a feedback loop across frames. Handling:

1. **De-dupe guard (framework-owned).** `Geometry` only writes `size` when the
   measured value actually changed. Equal size ⇒ no write ⇒ no dependent
   recomposition. This satisfies "oscillation behavior is defined" without
   pushing the guard onto callers.
2. **Structurally safe usage (documented).** When the widget's own size is
   imposed by its parent (e.g. it fills a panel), rebuilding its child cannot
   change that size, so no feedback exists. This is the recommended pattern and
   is naturally safer than a Flutter-style `LayoutBuilder`, where the builder's
   output *is* what gets measured (a tighter loop).

## 7. Relationship to #430 (window size) — one unified read path

The window case (#430) and this container case (#431) resolve to a **single
in-tree read API**:

- **In-tree read (window and container, unified):** `Geometry.of(context).size`.
  The app installs the **root `Geometry` provider** by wrapping the content root
  in `App._wrap_with_chrome_and_scope` (see
  [runtime/app.py](../../src/nuiitivet/runtime/app.py)). It needs no bespoke
  resize plumbing: the root `Geometry` measures the window through the normal
  layout pass, which the resize path (`_update_app_size_from_window` in
  [backends/pyglet/runner.py](../../src/nuiitivet/backends/pyglet/runner.py))
  already triggers via `invalidate` → relayout. Nearest provider wins, so a
  nested `Geometry` transparently overrides the window for its subtree; with no
  nested provider, reads fall back to the window. **Implemented in #431.**
- **MD3 window size class:** a **thin wrapper widget** that reads
  `Geometry.of(context)` and derives the Compact / Medium / Expanded class. Core
  stays MD3-independent; non-MD3 apps use raw size directly. Remaining #430 work.
- **No `App.of(context).size`.** Introducing a parallel App-level read API is
  rejected — it fragments the read path. The root `Geometry` provider is the
  single mechanism.

## 8. Relationship to a future general environment mechanism

Families (A)/(B) — theme, directionality, locale, density, color scheme,
text scale, safe-area — are the natural contents of a generic, typed, composable
scope mechanism (SwiftUI `Environment` / Compose `CompositionLocal`). That is a
larger architectural decision (it affects whether `Theme` migrates onto it) and
belongs in its own design issue, **not** here.

`Geometry` is deliberately built on the existing `.of(context)` convention so
that, if such a mechanism arrives, geometry can be surfaced through the same read
path without an API break. `Geometry` remains the special (C) provider that
*feeds* geometry in; it is never a plain author-set value in that mechanism.

## 9. Scope of this issue vs. future

**In scope (#431):**

- `Geometry` widget publishing `Observable[Size]` (resolved size), read via
  `Geometry.of(context)`.
- De-dupe guard; documented structurally-safe usage.
- Root `Geometry` provider installed at the window, so a top-level read falls
  back to the window size (the unified read path in §7).
- Example: local reflow independent of window size.

**Future (later milestones / on demand):**

- `constraints` (min/max) on the same `Geometry` — a layout-model extension, not
  additive-only (§5). Revisit if requested.
- `App.window_size` context-free `Observable` for code outside the widget tree
  (e.g. view-models that cannot call `.of(context)`). Not needed for the initial
  cut; revisit on demand.
- A side-effect callback modifier (`on_resized`) for reacting to a resize without
  a subtree rebuild — considered and **deferred**; the declarative
  `Geometry.of(context)` covers the primary use case. Reconsider if a concrete
  need appears.
- General-purpose environment mechanism for families (A)/(B) — see §8.

## 10. Design decisions summary

- **Named `Geometry`, not `GeometryScope`.** The widget measures its *own* box;
  "Scope" over-claims. `Geometry.of(context)` parallels `Theme.of` /
  `Navigator.of`, and nested override works the same way `Theme` override does.
- **Widget, not modifier, for the provider.** Scope boundaries are widgets in
  nuiitivet (Navigator, Overlay); `.of(context)` requires a real ancestor node.
  A modifier that creates a scope would break that convention.
- **Raw geometry in core; MD3 size class as a thin wrapper.** Keeps MD3
  breakpoints out of core and lets non-MD3 apps use raw size.
- **Atomic `Observable[Size]`.** Prevents torn reads; per-axis reactions via
  `computed`.
- **Window = root `Geometry` provider.** Installed at the window in #431, so one
  unified read path (`Geometry.of(context).size`) serves both window and
  container; no separate `App.of().size`. The root provider needs no bespoke
  resize plumbing — it measures the window through the normal layout pass.
- **One-frame-deferred reactivity is acceptable.** Imperceptible, and it is what
  makes the layout-time write re-entrancy-free.
