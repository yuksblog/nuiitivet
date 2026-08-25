# File Dialogs

`nv.FileDialog` shows the operating system's native open / save / folder
dialogs. Every method is a coroutine — call it with `await` from an `async`
event handler; your handler resumes with the result when the user dismisses
the dialog:

```python
import nuiitivet.material as nv


class Editor(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.status = nv.Observable("no file")

    def build(self) -> nv.Widget:
        return nv.Column(
            padding=24,
            gap=12,
            children=[
                nv.Text(self.status),
                nv.Button("Open…", on_click=self._open),
            ],
        )

    async def _open(self) -> None:
        path = await nv.FileDialog.open_file(file_types=["txt", "md"])
        if path is None:
            return  # the user cancelled
        self.status.value = f"opened {path.name}"
```

A selection comes back as a `pathlib.Path`; cancelling the dialog returns
`None`. There is no other sentinel — check `is None`, not truthiness.

A runnable demo with all three dialogs is at
[`samples/window/file_dialogs.py`](https://github.com/yuksblog/nuiitivet/blob/main/samples/window/file_dialogs.py).

## Opening a file

```python
path = await nv.FileDialog.open_file(
    title="Pick an image",
    initial_dir="~/Pictures",          # str or Path
    file_types=["png", "jpg", "gif"],  # extensions, no leading dot
)
```

All parameters are optional. `file_types` restricts the picker to the given
extensions; omit it to allow any file.

## Opening several files at once

```python
paths = await nv.FileDialog.open_files(file_types=["png", "jpg"])
for path in paths:  # empty when cancelled
    load(path)
```

`open_files` takes the same parameters as `open_file` and returns a list.
Cancelling returns an empty list, so a plain `for` loop handles both cases —
there is no `None` to check.

## Saving to a file

```python
path = await nv.FileDialog.save_file(default_name="untitled.txt", file_types=["txt"])
if path is not None:
    path.write_text(content)
```

The dialog picks a *destination*: the returned path usually does not exist yet,
and nothing has been written when the call returns — writing the file is your
job. Where the platform asks for overwrite confirmation, that happens inside
the dialog. `file_types` filters the file browser on Windows and Linux; the
macOS save dialog has no type filter and ignores it.

## Opening a directory

```python
path = await nv.FileDialog.open_directory(title="Export to…")
```

## While a dialog is open

Only one dialog can be up at a time: `FileDialog` serializes calls, so a
double-click never stacks two dialogs — the second call simply waits its turn.
You don't need to disable buttons yourself.

What the rest of the app does meanwhile differs by platform:

- **macOS**: the dialog is a native panel inside your process and is
  app-modal — the app window pauses (no input, no repaints) until the dialog
  is dismissed. The first dialog of a session can take a moment to appear
  (the OS panel service warms up once); later ones open instantly.
- **Windows / Linux**: the dialog runs in a helper process and your window
  keeps painting; the `await` simply doesn't resume until the dialog closes.

## If no dialog appears on Linux

The dialogs are provided by `zenity` (GNOME) or `kdialog` (KDE). Most desktop
distributions ship one of them; on a system with neither installed, every
`FileDialog` call raises `nv.FileDialogError`. Install one, or catch the error
and fall back to a text field:

```python
try:
    path = await nv.FileDialog.open_file()
except nv.FileDialogError:
    ...  # no zenity/kdialog — ask for a path another way
```

macOS and Windows need nothing extra (`osascript` and PowerShell are part of
the OS). `FileDialogError` is never raised for cancellation — that is always
`None`.
