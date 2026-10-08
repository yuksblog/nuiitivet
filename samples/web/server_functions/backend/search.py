"""The work: on the desktop it runs on a thread, in a browser on the server."""

import nuiitivet.material as nv

WORDS = [f"word{n}" for n in range(50_000)]


class Rejected(Exception):
    pass


def _distance(a: str, b: str) -> int:
    """Edits that turn ``a`` into ``b``: the slow part of a search."""
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        previous, row[0] = row[0], i
        for j, y in enumerate(b, 1):
            previous, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, previous + (x != y))
    return row[-1]


@nv.server
def search(
    query: str,
    progress: nv.WriteOnlyObservable[float],  # the caller passes an Observable
    cancel: nv.CancelToken = nv.CancelToken(),  # set when the caller gives up
) -> list[str]:
    if not query:
        raise ValueError("type something to look for")  # built-in: raised as-is in the caller
    if query == "secret":
        raise Rejected("not for you")  # anything else: nv.RemoteError in the caller
    matches: list[str] = []
    for index, word in enumerate(WORDS):
        if cancel.cancelled:
            break
        if _distance(query, word) <= 1:
            matches.append(word)
        if index % 500 == 0:
            progress.value = index / len(WORDS)
    return matches
