# Observable: Async State

A search box that searches as you type. The user types, results appear — and if
they keep typing, only the newest search reaches the screen, even when an earlier
one comes back later.

```python
import nuiitivet.material as nv


class SearchScreen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.query = nv.Observable("")

        # Search 0.3 s after typing stops. If the user types again before the
        # search answers, that answer is thrown away.
        self.results = self.query.debounce(0.3).switch_map(self._search, initial=[])

    def _search(self, query: str, cancel: nv.CancelToken) -> list[str]:
        return search_api(query)          # runs on a worker thread, not the UI thread

    def build(self) -> nv.Widget:
        return nv.Column(
            gap=16,
            children=[
                nv.TextField(value=self.query, label="Search", width=320),
                nv.ForEach(self.results, lambda item, index: nv.Text(item)),
            ],
        )
```

That is the whole feature. `self.results` is an ordinary Observable, so the list
binds to it the same way anything else does; nothing in `build()` knows a thread
was involved.

`switch_map` is `map` for a function that takes time to answer. `_search` runs off
the UI thread so the window keeps painting, and each new query discards the
previous search rather than racing it. Type `p`, `py`, `pyt` quickly and three
searches may be in flight; only the last one can reach the screen.

`_search` is handed a `CancelToken` as its second argument. You can ignore it —
see [`CancelToken`](#canceltoken) below.

## `initial`

Required, and keyword-only. There is no result until a search lands, so you say
what the UI shows meanwhile — `[]` above, giving an empty list.

**No search starts when the screen is built.** The first one waits for `query` to
change, so `initial` is also what the screen shows before the user types anything.

## Handling failure

`_search` runs on a worker thread, so a raised exception has nowhere to go.
**Return failures instead of raising them.** That means widening the result from a
bare list to a type that can carry both outcomes:

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchOutcome:
    items: list[str] = field(default_factory=list)
    error: str | None = None
```

```python
        self.outcome = self.query.debounce(0.3).switch_map(self._search, initial=SearchOutcome())
        self.items = self.outcome.map(lambda outcome: outcome.items)

    def _search(self, query: str, cancel: nv.CancelToken) -> SearchOutcome:
        try:
            return SearchOutcome(items=search_api(query))
        except RequestError as exc:
            return SearchOutcome(items=[], error=str(exc))
```

`build()` now binds `self.items` instead of `self.results`.

The `except` branch decides the items **and** the error together, which is why it
clears the list: a failed search leaves no stale rows on screen underneath an
error message.

An exception that escapes `_search` is treated as a bug, not an outcome — it is
logged, nothing is published, and the previous result stays.

## Showing the error

An error message is ordinary binding:

```python
nv.Text(self.outcome.map(lambda outcome: outcome.error or "")),
```

A toast is a side effect, so it belongs in the View where `Overlay` is reachable:

```python
    def on_mount(self) -> None:
        super().on_mount()                 # this is what runs build() — never skip it
        overlay = nv.Overlay.of(self)      # not in __init__ — needs a mounted ancestor

        def toast(outcome: SearchOutcome) -> None:
            if outcome.error is not None:
                overlay.snackbar(f"⚠ {outcome.error}")

        self.bind(self.outcome.subscribe(toast))
```

Overriding `on_mount` without calling `super()` leaves the screen blank and raises
nothing, because the base implementation is what calls `build()`.

Discarded searches never emit, so this fires once per outcome that actually
lands. You do not need a stale-result guard.

## `CancelToken`

A discarded search keeps running: Python cannot stop a thread from outside. Its
result is thrown away either way, so this costs you only time and network calls.
If `_search` has a natural place to check, it can give up early:

```python
    def _search(self, query: str, cancel: nv.CancelToken) -> SearchOutcome:
        items: list[str] = []
        for page in range(PAGE_COUNT):
            if cancel.superseded:
                return SearchOutcome()
            items += search_page(query, page)
        return SearchOutcome(items=items)
```

Checking is optional and never affects which result wins. A `_search` that blocks
in a single call has nowhere to check, and loses nothing by ignoring `cancel`.

## When this is the wrong tool

`switch_map` runs when a value changes, and produces one result. Anything else
stays hand-written — see [Background Work](background_work.md):

| You want | What happens instead |
| --- | --- |
| A Retry button | Nothing. The query has not changed, so no search starts |
| A progress bar while it runs | Only the final value arrives; there is nothing to report progress with |
| A Cancel button | `cancel` is not yours to set; only a new query discards a search |
| Infinite scroll | Each result **replaces** the last, so pages do not accumulate |

Two things that do *not* matter here: how much data comes back (items, a total and
facets are still one answer — that is what `SearchOutcome` is for), and how heavy
the work is (`switch_map` uses a worker thread either way).

## Full sample

`samples/state-management/async_state.py` — a runnable screen with the failure
path wired up (search for `boom`).
