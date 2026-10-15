# Source jump

`Ctrl+Shift+Click` (`Cmd+Shift+Click` on macOS) on a widget **opens the code
that built it**, in your editor.

## Open a widget's code

Hold `Ctrl+Shift`. The widget under the cursor gets **rose** brackets and a
caption naming its file and line. Click, and the editor opens at that line. A
caption then says what happened: `opening app.py:42`, or why nothing did. It
clears on the next pointer move.

### Use another editor

VS Code works as installed. For another editor, pass its URL scheme to
`--editor`. `{file}` and `{line}` are replaced with the path and the line:

```bash
# Cursor
python -m nuiitivet.dev run app.py --editor "cursor://file{file}:{line}:1"
# PyCharm
python -m nuiitivet.dev run app.py \
  --editor "jetbrains://pycharm/navigate/reference?project=NAME&path={file}:{line}"
```

### Jump from inside a mode

`Ctrl+Shift+Click` works inside [comment mode](comment_mode.md) and
[layout edit mode](layout_edit_mode.md) too. There it opens the code instead
of marking or selecting. Inside comment mode, rose brackets mean a jump;
amber means a mark.

## Next Steps

- [The skills](skills.md) — what each skill does for you.
- [With a coding agent](index.md) — the section overview.
