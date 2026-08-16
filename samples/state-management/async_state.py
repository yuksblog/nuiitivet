"""Observable: Async State

Demonstrates:
- switch_map() to run a slow query off the UI thread and keep only the newest result
- Returning failure as a *value*, so one type carries both outcomes
- A CancelToken check that stops a superseded run from finishing its pages
- A toast raised from the outcome, in the View where Overlay is reachable

Type fast: every keystroke restarts the search, and only the last one is ever
displayed -- even when an earlier, slower query finishes after it.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

import nuiitivet.material as nv

_PAGE_COUNT = 4
_CATALOG = [
    "apple",
    "apricot",
    "avocado",
    "banana",
    "blackberry",
    "blueberry",
    "cherry",
    "cranberry",
    "grape",
    "grapefruit",
]


class SearchFailed(Exception):
    """Stand-in for whatever the HTTP client raises."""


def search_page(query: str, page: int) -> list[str]:
    """Stand-in for one page of a real search request; the delay is the I/O."""
    time.sleep(0.25)
    if query == "boom":
        raise SearchFailed("the search service is unavailable")
    matches = [item for item in _CATALOG if query in item]
    return matches[page::_PAGE_COUNT]


@dataclass(frozen=True)
class SearchOutcome:
    """One run's answer: the items, or why there are none.

    Failure lives here rather than on a channel beside the observable, so a
    single value carries both and the two can never disagree. That is what lets
    the error case decide the item list too -- a failed search shows *no* stale
    rows, which a separate error channel could not have expressed.
    """

    items: list[str] = field(default_factory=list)
    error: str | None = None
    query: str = ""


class SearchModel:
    """Search-as-you-type, with only the newest query's result on screen."""

    def __init__(self) -> None:
        self.query = nv.Observable("")

        # debounce thins the keystrokes; switch_map runs what survives off the
        # UI thread and throws away any run the next keystroke supersedes.
        self.outcome = self.query.debounce(0.3).switch_map(self._search, initial=SearchOutcome())

        self.items = self.outcome.map(lambda outcome: outcome.items)
        self.status = self.outcome.map(self._status_text)

    def _search(self, query: str, cancel: nv.CancelToken) -> SearchOutcome:
        """Runs on a worker thread. Must not touch widgets -- only values."""
        if not query:
            return SearchOutcome()
        try:
            items: list[str] = []
            for page in range(_PAGE_COUNT):
                # The result of a superseded run is discarded either way; this
                # check just stops paying for the rest of it.
                if cancel.superseded:
                    return SearchOutcome()
                items += search_page(query, page)
            return SearchOutcome(items=sorted(items), query=query)
        except SearchFailed as exc:
            # A failed search is an outcome to render, not a bug -- so it is
            # returned, and it clears the items in the same breath.
            return SearchOutcome(items=[], error=str(exc), query=query)

    @staticmethod
    def _status_text(outcome: SearchOutcome) -> str:
        if outcome.error is not None:
            return "Search failed"
        if not outcome.query:
            return "Type to search"
        return f"{len(outcome.items)} results for '{outcome.query}'"


class SearchScreen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.model = SearchModel()

    def on_mount(self) -> None:
        # super() is what runs build(); overriding without it leaves the screen
        # empty and raises nothing.
        super().on_mount()

        # Overlay.of() needs a mounted ancestor, so not in __init__.
        overlay = nv.Overlay.of(self)

        def toast(outcome: SearchOutcome) -> None:
            if outcome.error is not None:
                overlay.snackbar(f"⚠ {outcome.error}")

        self.bind(self.model.outcome.subscribe(toast))

    def build(self) -> nv.Widget:
        return nv.Box(
            padding=24,
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text("Observable: Async State"),
                    nv.Text("Type fast -- only the newest query's result is shown."),
                    # width names the box the bar is inset into, not the bar.
                    nv.SearchBar(self.model.query, placeholder="Search fruit", width=420),
                    nv.Text(self.model.status),
                    nv.Column(
                        gap=4,
                        children=[
                            nv.ForEach(self.model.items, lambda item, index: nv.Text(f"• {item}")),
                        ],
                    ),
                    nv.Text("Search for 'boom' to see a failure."),
                ],
            ),
        )


def main() -> nv.App:
    random.seed(0)
    return nv.App(content=SearchScreen(), title="Observable: Async State")


if __name__ == "__main__":
    main().run()
