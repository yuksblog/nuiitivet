# Desktop Notifications

`nv.Desktop.notify(title, body)` raises an operating-system notification — the kind
that appears in the corner of the screen and lands in the notification center.
It exists for one job: telling the user that something finished while they
were in another window.

```python
nv.Desktop.notify("Import done")                        # title only
nv.Desktop.notify("Import done", "1,000 rows written")  # title + body
```

The runnable demo is at
[`samples/window/desktop_notifications.py`](https://github.com/yuksblog/nuiitivet/blob/main/samples/window/desktop_notifications.py).

## `Desktop.notify` is fire-and-forget

- **It never blocks.** It returns in milliseconds; the notification appears on
  its own a moment later. There is nothing to `await`.
- **It never raises.** A platform that cannot show the notification logs the
  failure once and moves on — a notification is a courtesy, and it must not
  take the app down. There is no return value to check.
- **It is safe from any thread.** Call it from an event handler or straight
  from the worker thread that just finished its job — no marshalling to the
  UI thread is needed. This is the natural last line of a long job wired up
  as in [Background Work](../state-management/background_work.md).

Delivery is best-effort even when everything works: the OS may still suppress
the notification (Do Not Disturb / Focus modes, per-app notification
settings), silently. Never make a notification the only way the user learns
something — keep the result visible in the app too.

## What the notification looks like

Run **from source (`python app.py`)**, the notification carries a borrowed
identity — the OS attributes it to the helper that raised it, not to your app:

- **macOS** — delivered via `osascript`, attributed to **Script Editor**. The
  helper process adds a fraction of a second before the banner appears.
- **Windows** — shown as a regular toast through a transient notification-area
  icon; the icon appears while the toast is up and disappears when it closes.
  The attribution line shows the notification's own title.
- **Linux** — delivered via `notify-send`, which most desktops show without
  any attribution line.

A **packaged app** does better on macOS. Inside a signed `.app` bundle with a
bundle identifier, notifications go through the native notification center
in-process: your app's own name and icon, instant delivery, and the app gets
its own row in System Settings → Notifications. The first notification asks
the user for permission; if they decline, later calls are silently ignored
(see above — never rely on delivery). None of this needs code changes — the
same `nv.Desktop.notify` call upgrades itself when a bundle identifier is
present. [macOS App Identity](../packaging.md#macos-app-identity) shows the
build flags that produce such a bundle.

## If nothing appears on Linux

Notifications are delivered by `notify-send`. Most desktop distributions ship
it; on a minimal install, add the `libnotify` package (`libnotify-bin` on
Debian/Ubuntu). Without it every `nv.Desktop.notify` call is a logged no-op —
the app keeps running.
