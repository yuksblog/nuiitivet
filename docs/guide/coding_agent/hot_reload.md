# Hot Reload

Edit a widget, save, and see the UI update without a restart.

## Reload an edit

Change `"increment"` to `"add one"` in the counter's `build()` and save. The
counter is the one from
[Set up](setup.md#4-pass-a-root-factory-to-the-window), running under the
dev runner. The button relabels in the open window. The count keeps its
value. Saves anywhere under your app's directory reload.

### If a save fails

A syntax or build error on save leaves the **previous UI running**. The full
traceback goes to the console (VS Code debug console / terminal). A banner
appears over the app. Fix the code and save again.

### Reload while debugging in VS Code

Hot reload works under the standard **F5** debugger with no extension.
Breakpoints keep firing in the reloaded code. A save made while stopped at a
breakpoint is queued and applied when you resume.

## If state resets or a screen closes after a save

| Pattern | After the save | What to do |
| --- | --- | --- |
| A keyless widget holding an `Observable`, when widgets before it are added, removed or reordered | The `Observable` resets to its initial value | Give the widget a `key` |
| An `Observable` at module top level, or work done in `main()` | The value resets. What `main()` set up is not redone | Create it inside the root factory |
| A widget pushed with `Navigator.push(widget)` | It closes, with every widget pushed above it | Push an intent: `Navigator.push(intent)` |
| A widget shown on the Overlay: `Overlay.dialog(widget)`, `Overlay.side_sheet(widget)`, `Overlay.bottom_sheet(widget)` | It closes | Show an intent: `Overlay.dialog(intent)`, `Overlay.side_sheet(intent)`, `Overlay.bottom_sheet(intent)` |
| `await Overlay.dialog(intent)` still waiting at the save | The dialog stays open, but the result it returns after the save does not appear on screen | Close the dialog and open it again after the save |

## Next Steps

- [Comment mode](comment_mode.md) — tell the coding agent what to change
  from the app's own screen.
- [With a coding agent](index.md) — the section overview.
