# Geometry: Container-Scoped Measured Geometry

Status: **Accepted — implemented** (tracks issue #431; related to #430)

## 1. Motivation

Some adaptive layouts must react to the size of a **specific container**, not the
whole window — reflow inside one panel regardless of window size, local
breakpoints, etc. Today a widget's measured size is set via
`WidgetKernel.set_layout_rect` (see [widget_kernel.py](https://github.com/yuksblog/nuiitivet/blob/main/src/nuiitivet/widgeting/widget_kernel.py))
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

- [app.py](https://github.com/yuksblog/nuiitivet/blob/main/src/nuiitivet/runtime/app.py) `_render_frame`: `flush_binding_invalidations()` / `flush_scope_recompositions()` run first,
- then `on_draw` performs `root.layout(w, h)`,
- then paint.

A container's measured size is known only during the layout phase. When
`Geometry` publishes a changed size during layout, it writes to an `Observable`.
The **recomposition** that write triggers is queued, not run: dependent scopes
are rebuilt when the next frame flushes them, so no subtree is rebuilt
mid-layout.

```text
frame N   : layout → Geometry measures → size changed → Observable.set()
            → dependent scopes queued dirty → next frame requested
frame N+1 : flush bindings/scopes (rebuild dependents) → layout → paint
```

This is the key result: **because scope recomposition and layout are serialized
across frames, a rebuild driven from layout is naturally deferred.** That is what
sidesteps the layout-time re-entrancy hazard a synchronous,
build-during-layout `LayoutBuilder` would expose to callers.

### 3.1 What is *not* deferred — a known deviation

Only recomposition defers. The write itself propagates **synchronously**: a
`bind_to` setter runs immediately, and a lazy reader such as `Text`'s label
resolution picks up the new value the moment it is asked. So within one layout
pass, a widget measured *before* the publishing `Geometry` measures against the
old value while a widget measured after it sees the new one.

That is a state change with side effects during layout, which
[RENDERING_PIPELINE.md](RENDERING_PIPELINE.md) §2 forbids for `layout()`
("except for storing layout results"). It is observable, not theoretical. A
`Text` bound to the size and laid out *ahead* of the `Geometry` in the same
`Column`:

```text
pass 1 -> label rect (0, 0, 103, 16)      # measured for "width is 0 pixels"
          label text 'width is 400 pixels'  (preferred width 119)
pass 2 -> label rect (0, 0, 119, 16)
```

Frame N paints a 119px string in a box measured at 103px. It self-heals — the
write also marks the tree dirty and requests a frame, so frame N+1 measures
correctly — but frame N is torn.

This is a deviation the initial cut (#431) shipped with, not a property to build
on. Nothing in this document should be read as endorsing a layout-phase
`Observable` write; §11's push path deliberately avoids needing one.

Tracked in **#466**, which also covers `ScrollViewport` — it publishes scroll
metrics from `layout()` the same way, so the resolution is a protocol-level
decision rather than a fix local to `Geometry`.

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
  measure phase (see [container.py](https://github.com/yuksblog/nuiitivet/blob/main/src/nuiitivet/layout/container.py),
  [column.py](https://github.com/yuksblog/nuiitivet/blob/main/src/nuiitivet/layout/column.py)). Exposing "constraints"
  therefore introduces a concept the framework does not otherwise have — it is a
  layout-model extension, not a small add — so it is deliberately out of scope
  here. In practice the resolved `size` already answers "how much space do I
  have" for the common (weight/fill) case.

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
  [runtime/app.py](https://github.com/yuksblog/nuiitivet/blob/main/src/nuiitivet/runtime/app.py)). It needs no bespoke
  resize plumbing: the root `Geometry` measures the window through the normal
  layout pass, which the resize path (`_update_app_size_from_window` in
  [backends/pyglet/runner.py](https://github.com/yuksblog/nuiitivet/blob/main/src/nuiitivet/backends/pyglet/runner.py))
  already triggers via `invalidate` → relayout. Nearest provider wins, so a
  nested `Geometry` transparently overrides the window for its subtree; with no
  nested provider, reads fall back to the window. **Implemented in #431.**
- **MD3 window size class:** proposed as a thin wrapper over this read path in
  #457 and **closed as not planned** — the read path above is the whole of the
  delivered surface. Rationale and revisit triggers are in the closing comment on
  #457; the short form is that `Geometry` is itself a container-scoped read, which
  is the concept a window size class is the coarser predecessor of.
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
- ~~A side-effect callback modifier (`on_resized`) for reacting to a resize
  without a subtree rebuild — considered and **deferred**; the declarative
  `Geometry.of(context)` covers the primary use case. Reconsider if a concrete
  need appears.~~ **Shipped as `on_size_changed` (#460)** — see §11.
- ~~MD3 window size class derived from this read path (#457).~~ **Closed as not
  planned** — see §7.
- General-purpose environment mechanism for families (A)/(B) — see §8.

## 10. Design decisions summary

- **Named `Geometry`, not `GeometryScope`.** The widget measures its *own* box;
  "Scope" over-claims. `Geometry.of(context)` parallels `Theme.of` /
  `Navigator.of`, and nested override works the same way `Theme` override does.
- **Widget, not modifier, for the provider.** Scope boundaries are widgets in
  nuiitivet (Navigator, Overlay); `.of(context)` requires a real ancestor node.
  A modifier that creates a scope would break that convention.
- **Raw geometry only; no MD3 size class.** Core stays MD3-independent and every
  app uses raw size. The size-class layer was proposed and closed as not planned
  (§7) — `Geometry` is already the container-scoped read that supersedes it.
- **Atomic `Observable[Size]`.** Prevents torn reads; per-axis reactions via
  `computed`.
- **Window = root `Geometry` provider.** Installed at the window in #431, so one
  unified read path (`Geometry.of(context).size`) serves both window and
  container; no separate `App.of().size`. The root provider needs no bespoke
  resize plumbing — it measures the window through the normal layout pass.
- **One-frame-deferred reactivity is acceptable.** Imperceptible, and it is what
  makes the layout-time write re-entrancy-free.

## 11. `on_size_changed` (#460): the push counterpart

The deferral in §9 was argued on *performance* grounds ("react without a subtree
rebuild"), and the declarative read did cover the use cases on the table. The
need that reopened it is ergonomic: when the size is consumed *imperatively* — a
ViewModel input, or a plain `Observable` the widget owns — `Geometry.of()`'s pull
semantics buy nothing while still charging the `on_mount` timing rule, the
subscription disposal, and the provider-scope concept.

`on_size_changed(callback)` reports a widget's own measured `Size` back to that
widget. Division of labour:

| | Use for |
| --- | --- |
| `on_size_changed` | **Push / self.** Measurer and consumer are the same widget. |
| `Geometry` | **Pull / scope.** Descendants at arbitrary depth read an ancestor's size without the widgets in between knowing. |

`Geometry` therefore stays the mechanism for the provider-shaped problem — many
widgets at arbitrary depth reading one scoped value, which push cannot express.
The docs invert the emphasis: `on_size_changed` is the default answer in
`docs/guide/layout/adaptive.md`, and `Geometry` moved to
`docs/guide/advanced/geometry.md`. That split matches where the demand actually
turned out to be, and is part of why the size-class layer was not needed (§7).

**It is not a provider**, so §10's "widget, not modifier, for the provider"
decision still holds: it creates no scope and is not resolvable via `.of()`. Like
`on_mount` / `on_unmount` it does not wrap the target — the callback is
registered on the widget itself and no node is added to the tree.

**Dispatch is between frames, not during layout**, and unlike `Geometry` the push
path needs no exemption from the layout protocol to get there. A size callback is
arbitrary user code that may mutate the tree, so `set_layout_rect` does two
things only: it stores `_layout_rect` — a layout result, which
[RENDERING_PIPELINE.md](RENDERING_PIPELINE.md) §2 explicitly allows — and appends
the measurement to a framework-internal queue
(`widgeting/widget_size_change.py`). Nothing in the tree is mutated and no
`Observable` is written during layout, so §3.1's tearing has no analogue here.
`App._render_frame` drains the queue at the start of the next frame, before the
build flush, and the effect lands one frame after the measurement.

The one side effect the layout pass does keep is a frame request: queuing calls
`invalidate()`, because a draw-on-demand app would otherwise never reach the
flush and the callback would never run. That schedules a frame without altering
any measurement, and `mark_needs_layout()` already does the same from inside
layout.

An in-frame dispatch (after layout, before paint) was implemented and rejected.
It removed the latency and made a one-shot `render_to_png` correct, but it
created a frame phase the framework does not otherwise have — recomposition and
mounting on an already-laid-out tree — to serve a tooling concern. Snapshots
instead settle explicitly at the entry point
(`App._settle_pending_size_changes`, capped by `_MAX_SNAPSHOT_SETTLE_PASSES`),
which simulates the frames an interactive app would have drawn. A `Geometry`
sample can look correct in a one-shot render without that help, but only because
of §3.1 — that is the deviation showing through, not a reason to copy it.

Contract details: the queue is keyed by widget and holds the *latest*
measurement, so several layout passes in one frame report once; the report
carries size only, so a widget that merely moves is silent; an equal size is
de-duped (§6.1's guard, per widget rather than per Observable); and the callback
fires once with the first measurement, so it alone can seed the state it drives.

Because that first call lands *after* the first paint, an `Observable` seeded
with a value the initial size does not imply produces one transition on startup
(the de-dupe absorbs it when the seed matches). This is documented rather than
special-cased: an eager first dispatch would mean two dispatch rules for one
feature, and the mitigation is a sensible initial value in app code.

Oscillation is bounded by the frame: a callback that resizes what it measures
advances one step per frame rather than spinning, which is the §6 guarantee
restated for the push path.
