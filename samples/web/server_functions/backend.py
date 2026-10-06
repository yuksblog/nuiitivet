"""The server's side: this module never reaches the browser."""

import time

import nuiitivet.material as nv
from models import Report

nv.server_only()  # keep this file off the browser; the page gets a stub

API_KEY = "stays-on-the-server"
WORDS = [f"word{n}" for n in range(2000)]


class Rejected(Exception):
    pass


@nv.server
def scan(
    query: str,
    progress: nv.WriteOnlyObservable[float],  # the caller passes an Observable
    cancel: nv.CancelToken = nv.CancelToken(),  # set when the caller gives up
) -> Report:
    if not query:
        raise ValueError("type something to look for")  # built-in: raised as-is in the caller
    if query == "secret":
        raise Rejected("not for you")  # anything else: nv.ServerError in the caller
    matches: list[str] = []
    for index, word in enumerate(WORDS):
        if cancel.cancelled:
            break
        if query in word:
            matches.append(word)
        if index % 50 == 0:
            time.sleep(0.1)  # a real job would hit a database here
            progress.value = index / len(WORDS)
    return Report(scanned=index + 1, matches=matches)
