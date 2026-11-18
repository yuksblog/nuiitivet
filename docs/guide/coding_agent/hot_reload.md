# Hot Reload

Edit a widget, save, and see the UI update without a restart.

## Reload an edit

Run `samples/coding_agent/hot_reload_counter.py` under the dev runner, as in
[Set up](setup.md#5-launch-under-the-dev-runner). Change `"increment"` to
`"add one"` in the counter's `build()` and save. The button relabels in the
open window. The count keeps its value. Saves anywhere under your app's
directory reload.

### If a save fails

A syntax or build error on save leaves the **previous UI running**. The full
traceback goes to the console (VS Code debug console / terminal). A banner
appears over the app. Fix the code and save again.

### Reload while debugging in VS Code

Hot reload works under the standard **F5** debugger with no extension.
Breakpoints keep firing in the reloaded code. A save made while stopped at a
breakpoint is queued and applied when you resume.

## Keep an object alive across saves

Some objects are slow to make: a catalog read from a large file, a connection
to a device. Make such an object in `main()`. Pass a `lambda` as the root
factory, and the `lambda` hands the object to the screen. `main()` runs once,
so a save does not make the object again. The sample is
`samples/coding_agent/keep_alive/app.py`, whose catalog takes a second to
load.

```python
def main() -> None:
    catalog = Catalog()  # loaded once
    nv.App(nv.Window(content=lambda: CatalogScreen(catalog))).run()
```

Keep the object's class in a file of its own that imports nothing from
`app.py`. Then only a save to that file can ask for a restart. The sample's
`Catalog` is in `catalog.py`.

Change the screen in `app.py`, a label or a class attribute, and save. The
screen changes, and the "loaded at" time on it stays. Change the body of
`Catalog.search` in `catalog.py` and save. The next search runs the new code
on the same catalog.

An edit to `main()` outside the `lambda` applies at the next start. An edit
to the `lambda` itself applies until a save to `app.py` changes anything
outside a function body. After that, it needs a restart too. No warning is
logged.

### If a save asks for a restart

A save to `catalog.py` that changes anything outside a function body prints
this line on the console. A new method, a new class attribute, a changed
signature and a new import are such saves.

```text
[nuiitivet.dev] This save re-executed catalog, app. Objects made before it still use the old classes: catalog.Catalog x1. Restart the app to update them.
```

The line names `app` too. A file that imports the saved one is run again
with it. The catalog on screen is the one made before the save, and it lacks
what the save added. Restart the app.

When the screen calls something the old catalog lacks, the "Hot reload
failed" banner shows the same line above the error.

## If state resets or a screen closes after a save

| Pattern | After the save | What to do |
| --- | --- | --- |
| A keyless widget holding a `State`, when widgets before it are added, removed or reordered | The `State` resets to its initial value | Give the widget a `key` |
| A `State` at module top level | The value resets on a save that changes anything outside a function body, in its file or in a file it imports | Create it inside the root factory |
| A widget pushed with `Navigator.push(widget)` | It closes, with every widget pushed above it | Push an intent: `Navigator.push(intent)` |
| A widget shown on the Overlay: `Overlay.dialog(widget)`, `Overlay.side_sheet(widget)`, `Overlay.bottom_sheet(widget)` | It closes | Show an intent: `Overlay.dialog(intent)`, `Overlay.side_sheet(intent)`, `Overlay.bottom_sheet(intent)` |
| `await Overlay.dialog(intent)` still waiting at the save | The dialog stays open, but the result it returns after the save does not appear on screen | Close the dialog and open it again after the save |

## Next Steps

- [Comment mode](comment_mode.md) — tell the coding agent what to change
  from the app's own screen.
- [With a coding agent](index.md) — the section overview.
