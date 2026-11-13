# App Badge

A badge is a count or a short text on the app's Dock or taskbar icon. Where it
shows depends on the OS. [Where the badge shows](#where-the-badge-shows) lists the places.

```python
class Screen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.unread = nv.State(0)

    def _new_message(self) -> None:
        self.unread.value += 1
        nv.App.of(self).badge.value = self.unread.value  # a count

    def _alert(self) -> None:
        nv.App.of(self).badge.value = "!"  # a short text

    def _mark_all_read(self) -> None:
        self.unread.value = 0
        nv.App.of(self).badge.value = None  # no badge
```

`0` and `""` remove the badge too.

The runnable demo is at [`samples/window/app_badge.py`](https://github.com/yuksblog/nuiitivet/blob/main/samples/window/app_badge.py).

## Where the badge shows

| OS | The badge shows on | A count | A text |
| --- | --- | --- | --- |
| macOS | The Dock icon | Yes | Yes |
| Windows | The main window's taskbar button | Yes, above 99 as `99+` | The first three characters |
| Linux | The app's icon in KDE Plasma and in Dash to Dock | Yes | No |
| Browser | Nowhere | No | No |

## If no badge shows

- **On GNOME's own dock.** Install the [Dash to Dock](https://extensions.gnome.org/extension/307/dash-to-dock/) extension. It draws the
  badge.
- **On Linux, when the app starts from a terminal.** Start the app from the
  app menu. [Linux Desktop Entry](../packaging/index.md#linux-desktop-entry) shows how to put it there.
- **On Linux, when the app starts from the app menu and still shows none.**
  Name the desktop entry's file after the executable in its `Exec` line. An
  entry with `Exec=/opt/myapp/MyApp` is saved as `MyApp.desktop`.
- **For a text on Linux.** A text removes the badge there. The log says so
  once.
