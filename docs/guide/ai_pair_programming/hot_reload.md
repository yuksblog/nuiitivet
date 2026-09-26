# Hot Reload

Edit a widget, save, and see the UI update without a restart.

Hot reload watches the modules under your app's directory. On a save it reloads
them and rebuilds the widget tree in the window that is already open. It works
under the standard VSCode **F5** debugger with no extension, and breakpoints keep
firing in the reloaded code.

## Quick start

### 1. Write a root factory, not a root instance

Hot reload rebuilds the tree by re-invoking a **factory** — a zero-argument
callable returning the root widget. Pass that callable to `Window(content=...)`
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
    nv.App(nv.Window(content=build_root)).run()

if __name__ == "__main__":
    main()
```

A `Widget` subclass works directly too — `Window(content=Counter)` — and a factory
that needs arguments closes over them: `Window(content=lambda: Home(config))`.

> Pass a factory, **not** `Window(content=build_root())`. Calling it yields a widget
> *instance*, which the reloader cannot rebuild — hot reload becomes inert for
> that root (a warning is emitted under the dev runner).

### 2. Launch with the dev runner

```bash
python -m nuiitivet.dev run path/to/app.py
```

or, for a package module:

```bash
python -m nuiitivet.dev run --module yourpkg.app
```

Arguments for your app go after a `--` separator — everything past it becomes
the app's `sys.argv`:

```bash
python -m nuiitivet.dev run app.py -- --png out.png
```

Without one, the app's argv is just its own path, so an `argparse` entry gets
its defaults.

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

## What a reload does not restore

| Pattern | After the save | What to do |
| --- | --- | --- |
| A keyless widget holding an `Observable`, when widgets before it are added, removed or reordered | The `Observable` resets to its initial value | Give the widget a `key` |
| An `Observable` at module top level, or work done in `main()` | The reload re-initialises the module; `main()` does not run again | Create it inside the root factory |
| A widget pushed with `Navigator.push(widget)` | It closes, with every widget pushed above it | Push an intent: `Navigator.push(intent)` |
| A widget shown on the Overlay: `Overlay.dialog(widget)`, `Overlay.side_sheet(widget)`, `Overlay.bottom_sheet(widget)` | It closes | For a dialog, show an intent: `Overlay.dialog(intent)` |
| `await Overlay.dialog(intent)` still waiting at the save | The dialog stays open, but the result it returns after the save does not appear on screen | Close the dialog and open it again after the save |

## Errors don't kill the app

A syntax or build error on save leaves the **previous UI running** and reports
the failure — the full traceback on the console (VSCode debug console /
terminal) and a banner over the app. Fix the code and save again to recover; the
debug session is never torn down.

## Next Steps

- [The on-screen modes](on_screen_modes.md) — tell the coding agent what to change
  from the app's own screen, or change the layout yourself.
- [AI pair-programming](index.md) — the section overview.
