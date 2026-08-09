# Hot Reload

Edit a widget, save, and see the UI update — while the window, your debugger
session, and your app's `Observable` state all survive. Every padding tweak no
longer costs a full restart.

Hot reload runs **in-process**: it reloads your changed modules and rebuilds the
widget tree without recreating the pyglet window or the GL context. Because it is
ordinary Python, it works under the standard VSCode **F5** debugger with no
custom adapter and no extension — breakpoints keep firing in the reloaded code.

## Quick start

### 1. Write a root factory, not a root instance

Hot reload rebuilds the tree by re-invoking a **factory** — a zero-argument
callable returning the root widget. Pass that callable to `App(content=...)`
(don't call it):

```python
import nuiitivet.material as nv

class Counter(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.count = nv.Observable(0)

    def build(self) -> nv.Widget:
        return nv.Column(
            padding=16,
            children=[
                nv.Text(self.count.map(lambda n: f"Count: {n}")),
                nv.Button("increment", on_click=lambda: self._inc()),
            ],
        )

    def _inc(self) -> None:
        self.count.value += 1

def build_root() -> nv.Widget:
    return Counter()

def main() -> None:
    nv.App(content=build_root).run()

if __name__ == "__main__":
    main()
```

A `Widget` subclass works directly too — `App(content=Counter)` — and a factory
that needs arguments closes over them: `App(content=lambda: Home(config))`.

> Pass a factory, **not** `App(content=build_root())`. Calling it yields a widget
> *instance*, which the reloader cannot rebuild — hot reload becomes inert for
> that root (a warning is emitted under the dev runner).

### 2. Launch with the dev runner

```bash
python -m nuiitivet.dev path/to/app.py
```

or, for a package module:

```bash
python -m nuiitivet.dev --module yourpkg.app
```

Normal (production) launch is unchanged — `python -m yourpkg` runs `main()` and
`App.run()` blocks as usual. There is no dev/prod branching in your code; the
difference is absorbed inside `App.run()`.

### 3. VSCode F5

Add this to `.vscode/launch.json`:

```json
{
  "name": "nuiitivet: hot reload",
  "type": "debugpy",
  "request": "launch",
  "module": "nuiitivet.dev",
  "args": ["${workspaceFolder}/app.py"],
  "console": "integratedTerminal"
}
```

Press **F5**. Set breakpoints as usual; save a file to reload the UI in place. A
save made while stopped at a breakpoint is queued and applied when you resume.

## What survives a reload

- **The window, GL context, and debug session** — never recreated.
- **`Observable` state** whose position in the tree is unchanged. State is
  snapshotted by structural path and restored into the rebuilt tree. If you
  add, remove, or reorder widgets, the affected state falls back to its initial
  value — unless you give the widget a stable `key` (via the
  [`keyed()` modifier](../modifiers/others.md#keyed)), which anchors its state
  across a reorder or sibling insertion.
- **Breakpoints** — keyed by file and line, so they fire in reloaded code.

## What is *not* reloaded

`nuiitivet`, `skia`, and `pyglet` are never reloaded (they wrap C extensions).
Only your project's modules — those living under the launched app's directory —
are reloaded, in dependency order so cross-module edits are picked up
consistently.

Module-level state (an `Observable` defined at module top level, work done in an
`if __name__ == "__main__"` guard, or side effects in `main()`) is **not**
restored: `main()` runs once at startup and never again on reload. Put
per-tree initialization inside the factory, not in `main()`.

## Errors don't kill the app

A syntax or build error on save leaves the **previous UI running** and reports
the failure — the full traceback on the console (VSCode debug console /
terminal) and a banner over the app. Fix the code and save again to recover; the
debug session is never torn down.

## See also

- [AI pair-programming](index.md) — the edit → see → act loop hot reload drives.
- [Dev Bridge MCP](dev_bridge_mcp.md) — the other half: how an assistant sees and
  drives the app hot reload keeps running.
- [The `nuiitivet-debug` skill](nuiitivet_debug_skill.md) — the skill that teaches
  an assistant to launch under the dev runner and keep the factory contract.
