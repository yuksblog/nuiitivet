# Window Management

This guide explains how to control and customize application windows in Nuiitivet. You can configure the title bar, adjust window size and position, and perform basic window operations.

Please refer to the following sections for detailed information:

- [Window Chrome](chrome.md): Learn how to configure OS-managed decoration, create a custom app-drawn header, or use a bare borderless window.
- [Size and Position](size_position.md): Understand how to control the dimensions and screen placement of your application window.
- [Operations](operations.md): Discover APIs for programmatically controlling the window state (close, maximize, minimize, etc.).
- [File Dialogs](file_dialogs.md): Show the OS-native open / save / folder dialogs and read the result.
- [Menu Bar](menu_bar.md): Register a menu bar with `Window(menu=...)` — items, shortcuts, checkable state, and placement.
- [Multiple Windows](multi_window.md): Open secondary windows with `nv.Window` — lifecycle, parent/modal windows, and the app exit policy.
- [Desktop Notifications](notifications.md): Raise an OS notification with `nv.Desktop.notify` — from an event handler or a worker thread.
