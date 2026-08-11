# Testing a screen

`AppHarness` runs a real `App` with no window: fixed size, settled after every
action, and drivable with the same verbs the dev bridge uses.

```python
def test_counter_increments(nuiitivet_app):
    screen = CounterScreen()
    app = nuiitivet_app(screen, size=(800, 600))

    app.click(key="increment")

    assert screen.count.value == 1                   # the state behind it
    assert app.get(key="count").text == "Count: 1"   # what is on screen
```

Two assertions, two different questions. The `Observable` is the front door for
state; the tree query is how you check that the state actually reached the
screen.

Outside pytest, or for a scope narrower than the test function, it is a context
manager:

```python
with AppHarness(screen, size=(800, 600)) as app:
    ...
```

Use one or the other. The harness **must** be closed — it holds a mounted,
subscribed widget tree — and the fixture is simply the thing that holds the
`with` for you. A harness left open is closed at teardown anyway, with a warning
naming the test.

## `size` is required

There is no default. `App` would otherwise resolve `"auto"` against the root's
preferred size, which is a machine-dependent number nobody chose — and every
geometry assertion downstream would inherit it. Say what the screen is.

`resize(w, h)` re-lays-out at a new size and runs the size-change callbacks,
which is the only way to reach that code path without dragging a window edge.

## Finding things

| Query | Result |
| --- | --- |
| `app.get(key=…)` | the one node; **fails on none, fails on more than one** |
| `app.query(key=…)` | the one node or `None`; still fails on more than one |
| `app.get_all(key=…)` | every match, possibly empty |
| `app.tree()` | a dict, for `print()` when a test fails |

Target by `key` — the stable identity you set with `keyed()`. `label=` is a
shortcut for presence: it resolves to whichever node actually carries the text,
which for a composite is an inner leaf (a Material button composes its label
into a `Text`), so `.rect` and `.widget` would describe the text rather than the
button. Clicking is unaffected.

Pass one or the other, never both: they are matched as an **or**, so naming both
widens the query instead of narrowing it. The harness refuses the call rather
than answering the opposite of what you meant.

**An ambiguous query fails.** Two rows both labelled "Delete" is a question an
assistant driving a live app can resolve by looking, and an `assert` cannot — so
`get()` refuses and lists the matches. This is a deliberate divergence from the
dev bridge, which takes the first match silently. A `key` unique enough for
`get()` behaves identically in both.

`tree()` is debug output. Asserting into it by index gives you a test that
breaks when the tree is restructured and nothing about the behaviour changed;
that is what the three query verbs are for.

### What a node tells you

| Attribute | Meaning |
| --- | --- |
| `.text` | the display string, normalized |
| `.key` | the stable identity |
| `.rect` | the layout rect. Available, deliberately not the front door |
| `.is_reachable` | in the tree, laid out, inside its clip and viewport, not covered |
| `.widget` | the raw widget — the marked escape hatch |

`is_reachable` is the question `query(...) is not None` cannot answer: a node can
be in the tree and scrolled below the fold, clipped by an ancestor, or covered
by an overlay, and presence still says yes. It **says nothing about opacity** —
a `visible(False)` widget is still laid out at full size and merely faded, so it
reports `True`. Assert on the `Observable` driving `visible()` for that.

### Re-query after an action

A node describes the tree **as it was when the query ran**.

```python
node = app.get(key="count")
app.click(key="increment")
assert node.text == "Count: 1"     # wrong: ask again
```

Do this instead:

```python
app.click(key="increment")
assert app.get(key="count").text == "Count: 1"
```

If the action rebuilt the subtree, the old node points at a discarded widget
where every attribute still answers plausibly. Rather than let that be silent,
reading a stale node raises `StaleNodeError`, naming the query it came from and
the action that invalidated it.

## Driving it

| Verb | Does |
| --- | --- |
| `app.click(key=…)` | press and release at the target |
| `app.scroll(key=…, dy=…)` | wheel notches, at a scroll **region** |
| `app.scroll_into_view(key=…)` | scroll until the target is reachable |
| `app.type(text, key=…)` | click the target to focus it, then type |
| `app.key("enter")` | a key press and release, with `modifiers=` |

These are the dev bridge's verbs, one for one, targeting the same way — what you
learn writing E2E carries straight down.

`scroll_into_view` is the verb that turns a `False` from `is_reachable` into a
`True`:

```python
assert app.get(key="row-99").is_reachable is False
app.scroll_into_view(key="row-99")
assert app.get(key="row-99").is_reachable is True
```

`scroll` targets the scrolling region itself, not a row inside it. Naming a row
raises and tells you which region to use — a diagnostic worth keeping.

### A verb that did nothing raises

Text goes to whatever is *focused*. With nothing focused, the bridge reports
`handled: False` and lets the assistant judge; an `assert` does not read that, so
the harness raises `ActionNotHandledError` instead:

```python
app.type("hello")                  # nothing focused -> raises
app.type("hello", key="search")    # clicks the field first, then types
```

The same applies to `key()` when nothing consumes the keystroke. To assert the
negative on purpose, ask for the result instead:

```python
result = app.key("escape", require_handled=False)
assert result["handled"] is False
```

## Errors

Everything the harness raises is importable from `nuiitivet.testing`:

```python
from nuiitivet.testing import (
    ActionNotHandledError,   # a verb ran and nothing consumed it
    LayoutNotConvergedError, # the tree would not settle
    StaleNodeError,          # a node outlived the tree it described
    TargetNotFoundError,     # nothing matched, or too much did
    TargetNotVisibleError,   # matched, but scrolled away or covered
)
```

## Navigation and overlays

Not yet part of this surface: asserting on the current route stack or on what is
open needs public accessors the framework does not have yet — `Navigator`'s
`snapshot_stack()` is the hot-reload restore log, not the route stack. Reach
through `app.app` in the meantime, and expect a narrower API later.
