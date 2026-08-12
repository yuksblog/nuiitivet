# Testing a widget

`mount()` gives one widget the host it needs to exist: a real `invalidate`, a
theme, and the layout pass that turns its state into geometry. It replaces the
fake app class every widget test used to hand-roll.

```python
from nuiitivet.testing import mount

def test_card_collapses():
    card = Card(title="hello")
    with mount(card) as host:
        host.layout(400, 200)
        assert card.preferred_size() == (400, 48)

        card.expanded.value = True     # the Observable the test holds
        host.settle()

        assert host.get(key="body").is_reachable
```

Under pytest, prefer the fixture — it closes the host for you, on the failing
path too:

```python
def test_card_collapses(nuiitivet_mount):
    card = Card(title="hello")
    host = nuiitivet_mount(card)
    host.layout(400, 200)
```

## `layout()` is explicit

There is no default size, deliberately. A widget mounted and never laid out has
no rect, and every query against it fails — which should read as *"you forgot to
lay it out"*, not as a harness bug. A default would make that failure arrive
later and blame the wrong thing.

`settle()` before any `layout()` says so directly rather than settling nothing.
Call `layout()` again to re-lay-out at a new size.

## `settle()` after changing state

An action mutates observables; the visible effect lands on the *next* frame.
`settle()` is that frame: it flushes the pending reactive work and re-lays-out,
so the tree you query is the tree the change produced.

It is strict. A layout that raises reaches your test instead of a debug log, and
a tree that will not converge raises rather than leaving whichever half-built
frame the last pass produced.

It also pumps the zero-delay queue, so a write from a worker thread, a deferred
batch flush, or a `Computed`'s UI notify is applied. Delayed
work — `debounce`, tooltip delays, animation ticks — stays frozen: no time has
passed that your test asked for. See
[the harness clock](index.md#the-harness-clock) for making a delayed effect
actually fire.

## The theme is installed, not optional

`mount()` installs an `AppScope` serving a theme, because the alternative fails
silently. `Theme.of` falls back to the light default when it can find no scope —
it does not raise — so a themeless host does not fail your test, it quietly
answers the wrong theme and every style assertion passes against a default your
app never runs.

```python
mount(card)                       # the light default, AppScope installed
mount(card, theme=my_theme)       # a specific one
mount(card, scope=False)          # detached: no providers at all
```

`scope=False` is how a test asks for the detached path on purpose — a widget
deliberately measured outside an App, as offscreen sizing does. It is separate
from `theme=` because `None` cannot mean both "I don't mind which theme" and
"install no provider"; passing both is a contradiction and raises.

To check that a widget *follows* a theme change rather than merely picking one
up at mount:

```python
def test_card_follows_the_theme(nuiitivet_mount):
    card = Card(None)
    host = nuiitivet_mount(card, theme=light_theme)
    host.layout(400, 200)

    host.push_theme(dark_theme)

    assert card.bgcolor == ...
```

## `invalidate_count`

The host records every repaint request, which is what most hand-rolled fake apps
existed to count.

```python
assert host.invalidate_count > 0     # it asked to repaint
assert host.invalidate_count == 0    # it did not
```

**Assert `> 0` or `== 0`, not an exact number.** Coalescing two invalidations
into one is a legitimate optimisation that changes no behaviour, and `== 2`
would break on it — a test that fails when the implementation changes rather
than when the behaviour does. Where an exact count genuinely is the contract
("this must not repaint per keystroke"), `== 0` says it and a number does not.

`settle()` itself never invalidates, so the count is yours alone.

## Subscriptions are checked for you

When the harness tears the widget down it fails the test if any subscription made
during it is still open:

```text
SubscriptionLeakError: 1 subscription(s) were created during this test and never
disposed. The observable still holds a callback into a widget that has been
unmounted, so firing it now mutates a dead tree:

  MyCard  subscribed at myapp/cards.py:64

Wrap the call in self.bind(...), which disposes it on unmount, ...
```

You get this without asking for it, because it is the framework's most common
bug and it is silent where it is introduced. An observable that outlives your
widget — one the app passed in — keeps a reference to a callback into a tree that
is gone; the symptom shows up somewhere unrelated, much later.

**The fix is `bind()`.** It stores the `Disposable` and disposes it on unmount:

```python
def on_mount(self) -> None:
    super().on_mount()
    self.bind(self.source.subscribe(self._on_value))     # instead of a bare subscribe
```

`observe(obs, cb)` and `bind_to(obs, setter)` already do this for you, so a widget
built out of those cannot leak. Subscribe **in `on_mount`, not `__init__`**: the
binding is released at unmount, so a widget that subscribed in its constructor
stops working if it is ever re-mounted.

What is *not* reported: a widget that was never mounted (nothing outlived
anything), a widget still mounted in another harness, and the observable graph's
own internal edges. A subscription with no widget behind it — app code with a
lifetime the harness cannot know — is counted in the message but never fails a
test on its own.

To turn it down, narrowest wins:

```toml
# pyproject.toml — the whole suite
[tool.nuiitivet.testing]
leak_check = "warn"        # "error" (default), "warn", "off"
```

```python
@pytest.mark.nuiitivet(leak_check="off")   # this test
...
with mount(widget, leak_check="off"):      # this harness
```

Reach for `"off"` when a subscription genuinely outlives its widget — not to
silence a report you have not read, which is the one thing this check cannot
survive.

## What `mount()` will not do

**It cannot click.** The action verbs go through the App's own pointer dispatch,
which a minimal host does not have and should not reimplement — a second input
path would drift from the real one. To drive input, use
[`AppHarness`](screens.md); it is not much more setup, and it is the same query
surface.

The queries (`get` / `query` / `get_all` / `tree`) and `Node` are identical at
both levels; [Testing a screen](screens.md#finding-things) documents them once.
