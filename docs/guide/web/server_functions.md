# Server Functions

An app runs in a browser from the source it runs on the desktop. What the
browser lacks is ignored: a second window is not shown, a notification is
not raised. Threads are the exception. `threading.Thread(...).start()`,
`asyncio.to_thread(...)` and `switch_map` with a plain function raise
`RuntimeError: can't start new thread`, and the handler dies there.

A server function is the API for that work. On the desktop it runs on a
thread the runtime owns; in the browser it runs on a server. The screen's
code is the same on both, and so is the function's.

## 1. Mark the function and await it

```python
# backend.py
import nuiitivet.material as nv

nv.server_only()  # step 6: keep this file off the browser

WORDS = [f"word{n}" for n in range(2000)]


@nv.server
def scan(query: str) -> list[str]:
    return [word for word in WORDS if query in word]
```

```python
# app.py
from backend import scan


class ScanScreen(nv.ComposableWidget):
    query = nv.Observable("word1")
    matches: nv.Observable[list[str]] = nv.Observable([])

    async def scan(self) -> None:
        self.matches.value = await scan(self.query.value)
```

The function is a plain `def` at the top level of its module, with every
parameter and the return annotated. The screen awaits it like any coroutine:
the line after the `await` runs on the UI thread, with the result.

## 2. Pass arguments and get the result

Arguments and the result are copied, and the type annotation decides how.
The function never sees the caller's objects, on the desktop either: a list
appended to inside the function stays as it was in the caller.

| Annotation | Carries |
| --- | --- |
| `None`, `bool`, `int`, `float`, `str`, `bytes` | The value; an `int` passed for a `float` arrives as a `float` |
| `datetime`, `date` | The value |
| An `Enum` subclass | The member |
| A dataclass of these | A dataclass of the same class |
| `list[T]`, `tuple[T, ...]`, `tuple[A, B]`, `dict[str, T]`, `Optional[T]` | The container, of these |

A value of another type, including a `bool` where an `int` is declared, is
refused with the argument named. An annotation outside the table, `Any`,
`object`, `set`, a plain `list`, is refused when the module imports.

A dataclass goes in a module both sides import, `models.py` in the sample:

```python
# models.py
from dataclasses import dataclass


@dataclass
class Report:
    scanned: int
    matches: list[str]
```

## 3. Report progress

A parameter annotated `nv.WriteOnlyObservable[T]` is written by the function
and read by the screen:

```python
@nv.server
def scan(query: str, progress: nv.WriteOnlyObservable[float]) -> Report:
    matches: list[str] = []
    for index, word in enumerate(WORDS):
        if query in word:
            matches.append(word)
        if index % 50 == 0:
            progress.value = index / len(WORDS)
    return Report(scanned=index + 1, matches=matches)
```

The caller passes an `nv.Observable[T]` and binds it as usual:

```python
class ScanScreen(nv.ComposableWidget):
    progress = nv.Observable(0.0)

    def build(self) -> nv.Widget:
        return nv.LinearProgressIndicator(value=self.progress)

    async def scan(self) -> None:
        report = await scan(self.query.value, self.progress)
```

Each write lands on the caller's observable on the UI thread. A tight loop
can write as often as it likes: the screen sees the latest value per frame.
The function cannot read the observable back, and a type checker says so.

## 4. Cancel

A parameter annotated `nv.CancelToken`, with `nv.CancelToken()` as its
default, is set when the caller gives up. The function checks
`cancel.cancelled` and returns:

```python
@nv.server
def scan(
    query: str,
    progress: nv.WriteOnlyObservable[float],
    cancel: nv.CancelToken = nv.CancelToken(),
) -> Report:
    for index, word in enumerate(WORDS):
        if cancel.cancelled:
            break
        ...
```

The caller gives up by cancelling the task that awaits the call:

```python
    async def scan(self) -> None:
        self._task = asyncio.ensure_future(scan(self.query.value, self.progress))
        try:
            report = await self._task
        except asyncio.CancelledError:
            self.status.value = "cancelled"

    def cancel(self) -> None:
        if self._task is not None:
            self._task.cancel()
```

The caller never passes the token; the default is the one that gets set. A
function with no `CancelToken` parameter runs to the end whatever the caller
does.

## 5. Handle an error

A built-in exception raised in the function, a `ValueError`, a `KeyError`,
reaches the caller as itself. Any other class reaches it as
`nv.ServerError`, whose text is the class name and the message:

```python
        except ValueError as error:
            self.status.value = str(error)
        except nv.ServerError as error:
            self.status.value = str(error)  # "Rejected: not for you"
```

## 6. Keep the server's code off the browser

Everything in the entry script's directory is sent to the browser, where
anyone can read it. A server function is the place for the work that must
not be: the database connection, the API key, the query that trusts no
input. `nv.server_only()` at the top of a module keeps that file out of what
the browser downloads; in a package's `__init__.py` it covers every module
of the package.

```text
myapp/
├── app.py          # the screens; python -m nuiitivet.web run app.py
├── models.py       # the dataclasses both sides use
└── backend/
    ├── __init__.py # nv.server_only(): the whole package stays on the server
    ├── scan.py     # the @nv.server functions
    └── db.py       # the connection and its password
```

The browser gets a stub in place of each server-only module: the same
functions with the same signatures, so `from backend.scan import scan`
resolves on both sides. Anything else in the module, a constant, a helper,
an import, never leaves the server.

A `@nv.server` function must sit at the top level of a server-only module.
Elsewhere, the import fails at once with the reason. The types in its
signature must come from a module the browser gets: with a dataclass defined
beside the function, the import fails with the type named. That is why
`models.py` sits outside the package.

## Full sample

`samples/web/server_functions/` — three files: `app.py` with the screen,
`backend.py` with the server function, `models.py` with the dataclass they
share. Scan for `word1`, cancel a scan, and look for `secret` to see the
`ServerError`.

## Next Steps

- [Building and Deploying](building_and_deploying.md)
- [Web overview](index.md)
