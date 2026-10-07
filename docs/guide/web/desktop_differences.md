# What Differs from the Desktop

The widgets, the observables, the handlers and the navigation behave in a
browser as they do on the desktop. What follows is the rest.

## Needs a change

A browser has one thread. `threading.Thread(...).start()` raises
`RuntimeError: can't start new thread`, and so does anything built on it:
`asyncio.to_thread`, a `ThreadPoolExecutor`, `switch_map` with a plain
function. That work goes in a [server function](server_functions.md), which
runs on the desktop too.

## What is ignored

| On the desktop | In a browser |
| --- | --- |
| `nv.Window(width=..., height=...)` | The main window fills the canvas and follows its size |
| `nv.Window(title=...)` | The browser tab's title |
| A second `nv.Window(...).open()` | Not shown; the console warns once |
| `App.run(draw_fps=..., renderer=...)` | No effect: frames come with the display's refresh, drawn by CanvasKit |
| `nv.FileDialog` | Returns `None`, as if the user had cancelled |
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

## Next Steps

- [Server Functions](server_functions.md)
- [Web overview](index.md)
