# What Differs from the Desktop

The widgets, the observables, the handlers and the navigation behave in a
browser as they do on the desktop. What follows is the rest.

## Needs a change

A browser has one thread. `threading.Thread(...).start()` raises
`RuntimeError: can't start new thread`, and so does anything built on it:
`asyncio.to_thread`, a `ThreadPoolExecutor`, `switch_map` with a plain
function. That work goes in a
[worker or server function](worker_and_server_functions.md), which runs on
the desktop too.

## What is ignored

| On the desktop | In a browser |
| --- | --- |
| `nv.Window(width=..., height=...)` | The main window fills the canvas and follows its size |
| `nv.Window(title=...)` | The browser tab's title |
| A second `nv.Window(...).open()` | Not shown; the console warns once |
| `App.run(draw_fps=..., renderer=...)` | No effect: frames come with the display's refresh, drawn by CanvasKit |
| `nv.FileDialog.open_file(title=..., initial_dir=...)` | The browser's picker has its own title and opens where it last did |
| `nv.Desktop.notify(...)` | Nothing |
| `nv.MenuBar` | Drawn in the page, as on the desktop |

## What you will notice

### The first load

The first load downloads Pyodide and CanvasKit, about 19 MB uncompressed,
and starts the interpreter: a few seconds before the first frame. Under `run`
they come from a CDN, in a built site from the site itself. The browser
caches both; a reload is faster.

### Fonts

The page has the fonts the framework ships and the font files in the app's
directory. A family name the page does not have falls back to the shipped
text font; there is no system font to find.

### File dialogs

`open_file()` shows the browser's file picker. The picker opens only from the
handler of a click or a key press; called from anywhere else, such as a
timer, `open_file()` raises `nv.FileDialogError`. The path it returns is a
copy of the file in the page's memory, read as on the desktop.
`open_directory()` copies every file under the directory, so a large one
takes a moment.

`save_file()` asks the user nothing. It returns a path in the page's memory
at once; write the file there, and the browser downloads it when your handler
returns, under the `default_name`. A later write to the same path downloads
nothing: each download is one `save_file()` call.

`python -m nuiitivet.web run samples/window/file_dialogs.py` shows all four
dialogs.

## Next Steps

- [Worker and Server Functions](worker_and_server_functions.md)
- [Web overview](index.md)
