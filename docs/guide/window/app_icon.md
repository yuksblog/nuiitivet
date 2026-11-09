# App Icon

An app's icon is set in two ways. PyInstaller or Nuitka sets it when the app
is packaged. `App(icon=...)` sets it from the source code. Where each one
shows depends on the OS. [Where each icon shows](#where-each-icon-shows) lists the places.

## Setting the icon when packaging

The options are in the [Packaging](../packaging/index.md) guide. PyInstaller takes `--icon`.
Nuitka takes `--macos-app-icon` on macOS and `--windows-icon-from-ico` on
Windows. Neither sets an icon on Linux. There you name it in the app's
[desktop entry](../packaging/index.md#linux-desktop-entry).

## Setting the icon in the source code

`App(icon=...)` takes the path of an image file. Build the path from
`__file__`. `__file__` is the path of the script itself, so the image is
found wherever the app starts. A relative path loses the icon when the app
starts from another directory.

```python
ICON = Path(__file__).parent / "assets" / "app_icon.png"

app = nv.App(window, icon=ICON)  # the app's icon
```

The file is a square PNG, 256 px or larger.

A packaged app reads the image from its bundle. The [Packaging](../packaging/index.md) guide puts it
there with `--add-data` for PyInstaller and `--include-data-dir` for Nuitka.

The runnable demo is at [`samples/window/app_icon.py`](https://github.com/yuksblog/nuiitivet/blob/main/samples/window/app_icon.py).

## Where each icon shows

| OS | The icon shows in | Set when packaging | Set in the source code |
| --- | --- | --- | --- |
| macOS | Finder, Launchpad | Yes | No |
| macOS | The Dock, while the app runs | Yes | Yes, replaces it |
| Windows | Explorer, the Start menu, a pinned taskbar button | Yes | No |
| Windows | The taskbar button and the title bar, while the app runs | Yes | Yes, replaces it |
| Linux | The app menu, a launcher pinned to the dock | Yes | No |
| Linux | The window's title bar, taskbar entry and switcher entry | No | Yes |
| Browser | The tab | No | Yes |

## What does nothing

- Under hot reload the icon stays as it was at launch.
- A file the app cannot read leaves the icon as it was. The log names the
  path. In a packaged app the image was usually left out of the bundle.
