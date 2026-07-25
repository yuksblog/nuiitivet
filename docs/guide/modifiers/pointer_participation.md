# Pointer Participation

Pointer-participation modifiers control **which widget receives a click** when
overlapping layers compete for it. nuiitivet resolves this automatically by
default (`auto`); the four `_pointer` modifiers let a widget opt into a different
posture when the default is not what you want.

## Abstract and default (`auto`)

By default nuiitivet follows one simple rule — **you can click what you can
see**:

- A widget with a background, border, or shadow — or one that is interactive
  (`clickable`, `hoverable`, `focusable`, scrollable, raw `pointer_input`) —
  **catches** clicks on its whole rectangle.
- A transparent layout wrapper (a bare `Container`, `Stack`, or positioning
  wrapper) or non-interactive ink (`Text`, `Icon`, `Image`, `Divider`) **lets
  clicks pass through** to whatever is behind it.

This default is called `auto`, and it is usually all you need. The most common
overlay case — a full-size alignment `Container` sitting over a canvas — already
works: the empty area passes clicks to the canvas, while the toolbar inside it
still catches.

```python
import nuiitivet.material as nv

nv.Stack([
    canvas,                       # clickable across its whole area
    nv.Container(                 # transparent aligner -> passes clicks through
        toolbar, width="100%", height="100%", alignment="bottom-center",
    ),
])
```

The four modifiers below are for the rarer cases where you want a widget to
deviate from that default.

| Modifier | Own surface | Children | Behind | Use it when… |
| --- | --- | --- | --- | --- |
| `defer_pointer()` | - | reachable | reachable | a decorated aligner/overlay must hand background clicks through while its children still work |
| `absorb_pointer()` | catches | - | - | a composite must act as one solid, non-interactive slab (e.g. a disabled card) |
| `block_pointer()` | catches | reachable | - | a scrim/blocker must swallow clicks to whatever is behind, but its own children stay interactive |
| `passthrough_pointer()` | - | - | reachable | the whole subtree should be click-through (e.g. a drag ghost) |

> **Stacking.** You rarely need more than one of these on a widget. If you do,
> they nest as independent wrappers evaluated **outermost-first** (the last one
> in an `a | b` chain is outermost), and each governs only the axes it controls:
> an outer `passthrough_pointer` or `absorb_pointer` stops descent, so any
> posture nested inside never runs (the most-blocking one wins); when two
> postures only disagree about whether the *own surface* catches (e.g.
> `defer_pointer() | block_pointer()`), the outermost one decides.

## defer_pointer

Turns off the widget's *own* surface so it never catches — clicks land on its
children, or fall through to whatever is behind. This is the explicit form of
the `auto` pass-through behaviour, useful when the widget paints a surface (so
`auto` would make it catch) but you still want it to behave like a transparent
aligner.

```python
overlay.modifier(nv.defer_pointer())              # always defer
overlay.modifier(nv.defer_pointer(vm.overlay))    # driven by an Observable[bool]
```

Every `_pointer` modifier also accepts an `Observable[bool]`, as shown on the
second line: the condition is read and validated when the widget is built, and
the posture switches whenever the observable changes — you never wait until the
first click for it to take effect. The other three modifiers take a condition
the same way.

## absorb_pointer

Makes the widget catch on its whole surface **and** stops clicks from reaching
its children — the subtree presents as a single opaque piece. Use it for a
one-piece overlay such as a disabled state built from interactive parts.

```python
card.modifier(nv.absorb_pointer())               # always absorb
card.modifier(nv.absorb_pointer(vm.disabled))    # driven by an Observable[bool]
```

## block_pointer

Widens the widget's own surface so it catches **everywhere** on its rectangle,
including transparent areas — nothing behind it receives the click. Its children
keep working; only the gaps between them are caught by the widget itself.

```python
scrim.modifier(nv.block_pointer())               # always block what's behind
scrim.modifier(nv.block_pointer(vm.is_modal))    # driven by an Observable[bool]
```

## passthrough_pointer

The whole subtree becomes click-through: neither the widget nor its children
catch, and clicks fall through to what's behind. Layout, painting, focus and
keyboard handling are untouched.

```python
ghost.modifier(nv.passthrough_pointer())             # always pass through
ghost.modifier(nv.passthrough_pointer(vm.hidden))    # driven by an Observable[bool]
```
