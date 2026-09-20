# Desktop integration

What the app shows outside its widget tree: more windows, the application menu
bar, the system tray, native file dialogs, file drops, OS notifications, fonts.

## Windows

```python
nv.Window(content=lambda: Palette(state), title="Palette").open()
```

- A `Window` is a model until `open()`. `close()` destroys it: construct a new
  one to reopen, and keep state that must survive in app-layer Observables.
- Hiding is different: `window.hide()` parks an open window — tree, state and
  geometry survive, no frames are drawn, and it still counts for the exit
  policy — and `window.show()` summons it back focused. `window.is_visible` is
  the matching Observable.
- Modal child: `nv.Window(content=..., parent=nv.Window.of(self), modal=True).open()`.
  Content closes its own window via `nv.Window.of(self).close()`.
- The first click into an inactive window acts, on every platform.
  `accepts_first_mouse=False` makes that click activate-only (a macOS-only
  effect).
- Exit timing: `nv.App(win, exit_policy=nv.ExitPolicy...)`.

## Application menu bar

```python
nv.Window(
    content=build_root,
    menu=nv.MenuBar([
        nv.MenuEntry("File", submenu=[
            nv.MenuEntry("Open", shortcut="Accel+O", on_select=open_file),
            nv.MenuEntry.separator(),
            nv.MenuEntry.quit(),
        ]),
    ]),
)
```

A window-level model, never built in `build()`. `label` / `enabled` / `checked`
take Observables. `shortcut` also fires window-wide, so never duplicate it with
`key_shortcut`. Replace the bar with `window.menu = ...`; `nv.MenuBarArea()`
relocates it.

## System tray

```python
tray = nv.TrayIcon(icon="tray.png", tooltip="Sync", menu=[
    nv.MenuEntry("Open", on_select=lambda: win.show()),
    nv.MenuEntry.separator(),
    nv.MenuEntry.quit(),
])
nv.App(win, tray=tray)
```

- App-owned: it lives exactly as long as the app runs.
- The menu reuses `MenuEntry`: Observable `label` / `enabled` / `checked` update
  live, and window-scoped roles are ignored. **Always include `quit()`.**
- `tray.installed` (`Observable[bool]`) says whether the icon actually shows —
  install can fail on a Linux desktop without raising.
- Resident (close-to-tray) app, three independent parts:
  `exit_policy=nv.ExitPolicy.EXPLICIT`, plus
  `nv.Window(..., close_action=tray.installed.map(lambda ok: "hide" if ok else "close"))`,
  plus the tray. `win.hide()` before `run()` starts the app in the tray.
- macOS Dock: `nv.TrayIcon(..., dock_visibility="always" | "auto" | "never")`
  (ignored elsewhere).

## File dialogs

```python
path = await nv.FileDialog.open_file(file_types=["txt", "md"])
```

Every method is a coroutine: call it from an `async` handler. Also
`open_files(...)`, `save_file(default_name=...)`, `open_directory()`. Extensions
are written without the dot. Cancel returns `None` (`open_files` returns `[]`)
and never raises. Calls are serialized, one dialog at a time.
`nv.FileDialogError` is raised when the dialog cannot be shown (Linux without
`zenity` / `kdialog`).

## File drops

```python
panel.modifier(nv.drop_target(self._on_drop))      # on_drop(e: nv.FileDropEvent)
```

`e.paths` is a `tuple[Path, ...]`, delivered to the innermost accepting widget
under the drop point.

## Desktop notifications

```python
nv.Desktop.notify("Import done", "1,000 rows written")
```

For a job that finished while the user is in another window. Fire-and-forget:
it never blocks, never raises, and is safe from any thread — the natural last
line of a worker job. Delivery is best-effort (the OS may suppress it), so keep
the result visible in the app too; in-app feedback is a snackbar, not this.

## Fonts

```python
nv.Fonts.register("assets/fonts/NotoSansJP.ttf", family_name="NotoSansJP")
```

Once at startup, before any widget renders; then `font_family="NotoSansJP"`
wherever a `font_family` is accepted (`nv.TextStyle`; icon fonts via
`nv.IconStyle(custom_font_family=...)`). The app-wide default family is
`nv.Fonts.set_default_family("Hiragino Sans")`; `None` restores locale-based
detection.
