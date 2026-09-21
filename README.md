# Nuiitivet

![Nuiitivet overview](docs/assets/readme_overview.png)

**AI friendly Desktop UI framework for Python.**

[![PyPI version](https://img.shields.io/pypi/v/nuiitivet)](https://pypi.org/project/nuiitivet/)
[![Python versions](https://img.shields.io/pypi/pyversions/nuiitivet)](https://pypi.org/project/nuiitivet/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

---

## What Nuiitivet is

Nuiitivet has two themes.

### Exploring what a UI framework should be in the age of AI agents

Ask a coding agent, and the first version of an app is on screen in no time.
It is rarely the version you wanted, so a back-and-forth follows.

- **Refine** — the back-and-forth that brings what works closer to what you
  want.
- **Debug** — the back-and-forth that fixes what behaves wrong.

Both can be done through chat, and you have probably felt how hard some of it
is to put into prose.

With Nuiitivet, you drag, mark and comment on the running app itself. The
agent looks at the same screen, edits, drives it, and checks. The centre of
your communication with the agent moves from the chat to the app. The
back-and-forth stops being a matter of explaining in prose and becomes a
matter of showing each other on the screen. That is far more intuitive.

### A UI framework specialised in desktop apps for Python

It sits between Tkinter and PyQt / PySide. It is more modern to write than
Tkinter: a declarative widget tree, reactive state, Material Design 3. It does
not aim at the large applications PyQt serves. The target is small to
mid-sized apps, and what there is to learn is in proportion.

The code looks like Flet's. Flet targets many platforms, mobile and web
included; Nuiitivet looks at the desktop alone.

The biggest difference is state management. `Observable` is modelled on
ReactiveProperty, a library widely used with WPF's MVVM: Rx operators work
directly on a reactive value. And the switch from a worker thread back to the
UI thread — where things tend to go wrong — is done by `Observable` for you.

OS integration and shipping an executable are there too. What is still
missing is listed plainly in [5. Current limitations](#5-current-limitations).

---

## 1. Building with a coding agent

Everything in this chapter turns on when you launch through the dev runner.

```bash
python -m nuiitivet.dev run app.py
```

A saved change shows up on the screen, on the spot.

### 1.1 Refine

The back-and-forth that brings what works closer to what you want. There are
three things you can do on the app's own screen.

#### Write the prompt on the app

Some instructions are hard to put into words in chat. In an app with many
widgets, **where** is the hard part.

`Ctrl+Shift+C` (`Cmd+Shift+C` on macOS) enters comment mode. Click a widget as
it is, or drag over an area where there is nothing to click, and write your
comment right there, on what you marked. There is no need to work out how to
say where: you point with the mouse.

When you are done, run `/nuiitivet-see-comments` in chat. The agent reads the
comments, changes the app as they say, and drives the app itself to check.

![Write the prompt on the app](docs/assets/readme_1.3.gif)

#### Change the layout directly

A size, an alignment, the order inside a `Row`: some changes are not worth an
instruction. They are all layout.

`Ctrl+Shift+E` (`Cmd+Shift+E` on macOS) enters layout edit mode. Drag the
app's own screen to change the layout. The change is written into the source
code. It costs no turn and no tokens.

#### Jump to the source, to check it or edit it

Even when an agent writes the code, human code review does not go to zero.
And a senior engineer is sometimes faster writing the code than instructing an
agent.

`Ctrl+Shift+Click` (`Cmd+Shift+Click` on macOS) opens the source code that
built the widget you clicked, in your editor. The code you want to check, or
to edit, is one click away.

![Jump to the source](docs/assets/readme_1.5.gif)

### 1.2 Debug

The back-and-forth that fixes what behaves wrong. Here there are two things
the agent can do.

#### The agent sees the app, and drives it

- **See** — the widget tree, the live `Observable` values behind it, a
  screenshot
- **Act** — click, type, scroll, send keys. Targets are named by `key` /
  `label` rather than coordinates, so they survive a layout change
- **Wait** — for async work to settle

So you can ask it to "use this app like a user would". Below, the agent drives
the app, checks the result, and finds a bug on the way.

![The agent drives the app](docs/assets/readme_1.2.gif)

#### The agent sees what you did, too

Writing down the steps that reproduce a bug is a chore. The
[dev bridge](#the-dev-bridge) records the actions you took in the app. For
privacy, the text you type is never recorded.

So you walk into the bug once, by hand, and that is enough. Write "this
happened" on the spot in comment mode, or say it in chat. The agent reads the
record, replays the same actions, sees the symptom for itself, and then fixes
it.

The example below is a "works sometimes, fails sometimes" case. Every attempt
is in the record, so the agent compares them and finds the one step that
differed.

![The agent compares the attempts](docs/assets/readme_1.2.png)

### 1.3 What makes this possible

#### The UI is all Python

Python is all you read and all you write. There is no new language to learn,
and it is a language the agent writes well.

A widget is a Python object, and each one corresponds to one expression in
your code. That is why an edit made on a displayed widget can be written
straight back into the code, and why the source jump works.

#### Hot reload

Every save **hot reloads** the app: the window is rebuilt **in place**, no
restart. And the state your `Observable`s hold **survives** — the screen you
reached with twelve clicks is not thrown away because you saved a file.
Reloads also go through with a VS Code **F5** debug session attached, and your
breakpoints stay.

#### The dev bridge

The dev bridge is an MCP server. MCP is the standard that connects agents to
tools, so no per-agent plugin is needed: Claude Code or GitHub Copilot, it
works the same way.

It opens only under the dev runner and listens only on localhost. It is not
part of the app you ship.

#### The intuitive grammar

A jump to the code is no use if the code it lands on cannot be read: no
review, no touch-up. Nuiitivet takes the good parts of several frameworks,
aiming at a grammar that is intuitive to read and to write.

- **Flutter** — the widget tree
- **SwiftUI / Compose** — modifiers that chain
- **CSS** — spacing with `padding` and `gap` alone, no `margin`; `Grid` cells
  placed by area name
- **WPF** — `Grid` layout, `*`-style weight sizing (`"wt"` here), and
  ReactiveProperty for state (that one is a desktop matter, so it waits for
  [2.1 ReactiveProperty-style state](#21-reactiveproperty-style-state))

Where it departs from them, it is to keep the code readable:

- Decoration is a **parameter**, not a wrapper, so the nesting does not grow
- Decoration and behavior are attached as **modifiers**, chained with `|`
- Event handlers are written as **procedures**, not declarations

[The intuitive grammar](docs/guide/intuitive_grammar.md) walks through it with
code.

#### Skills

Plainly: the agent does not know Nuiitivet. There is not enough of it in the
training data. The bundled skills fill that gap.

- **`nuiitivet-app`** — keeps the code idiomatic. Ships with a linter
- **`nuiitivet-debug`** — teaches the agent hot reload and the dev bridge:
  launch, see, act, check, down to reading the tree before spending a
  screenshot

Installing them is in [3.2 Installation](#32-installation).

---

## 2. Built for the desktop

**Nuiitivet is aiming at being desktop-specialised**, and most of what that
takes has landed. File dialogs, the menu bar, the tray icon — the OS
integration a desktop app leans on shipped piece by piece, and
[2.4](#24-the-os-is-part-of-the-app) keeps the checklist. What remains open is
listed in [5. Current limitations](#5-current-limitations).

What makes the specialisation real:

- **ReactiveProperty-style state management** — MVVM from WPF, as-is
- **Worker threads, dispatched onto the UI thread** — the answer to running
  heavy work locally, which is a desktop-only problem
- **Shipping an executable**
- **OS integration** — file dialogs, OS file drop, menu bar, notifications,
  tray icon, multiple windows

### 2.1 ReactiveProperty-style state

If you built desktop apps on WPF with ReactiveProperty, this is the part that
makes the move easy.

Set a value on an `Observable` and the UI bound to it **follows on its own**.
You never write the code that pushes a value into a widget.

```python
class CounterApp(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.count = nv.Observable(0)

    def increment(self):
        self.count.value += 1

    def build(self):
        return nv.Column(
            [
                nv.Text(self.count),          # bound directly
                nv.Button("Increment", on_click=self.increment),
            ]
        )
```

![Counter](docs/assets/readme_counter.png)

All that goes inside `build()` is the UI declaration. State and UI cannot drift
apart, because **the state is the UI's single source of truth.** With the
ViewModel pattern you separate at the class level rather than the method level.
**MVVM carries over.**

State derived from several values is declared as a formula — the equivalent of
WPF's `ReadOnlyReactiveProperty`.

```python
# total is declared as a + b; it recalculates whenever either one changes
self.total = self.count_a.combine(self.count_b).compute(lambda a, b: a + b)
```

And Rx-style operators slot in, with the result bound straight to the UI.

```python
# search 0.3 s after typing stops; if they type again, the earlier answer is dropped
self.results = self.query.debounce(0.3).switch_map(self._search, initial=[])
```

The function handed to `switch_map` runs **off the UI thread**, so the window
keeps painting while it searches. The `build()` side never learns it was async;
it binds an ordinary `Observable`.

`map` / `combine` / `compute` / `debounce` / `throttle` / `filter` /
`switch_map`, along with the async and threading details, are covered in the
[State Management guide](docs/guide/state-management/index.md).

### 2.2 Heavy work runs on your machine

This is a desktop-only problem. In a web app the heavy work sits inside the
server, so it never comes up. Importing a 100,000-row CSV freezes the screen if
you run it on the UI thread — and if you run it on a worker, you now have to get
the result back onto the UI thread.

In Nuiitivet, **a write to an `Observable` from a worker thread is marshalled
onto the UI thread for you.** You never hand-write that code.

Reporting progress, staying indeterminate until the total is known, cancelling
with a `CancelToken`, leaving the screen mid-run, and a worker that raises — all
of them have an answer ([Background Work](docs/guide/state-management/background_work.md)).

### 2.3 Ship an executable

There are recipes for PyInstaller and Nuitka ([Packaging](docs/guide/packaging.md)).
One executable, onto a machine with no Python on it.

### 2.4 The OS is part of the app

A desktop app is more than its window. It opens the OS file dialog, puts a
menu in the menu bar and an icon in the tray, raises notifications, accepts a
file dragged in from Finder or Explorer. That layer is kept here as a
checklist, so the distance to a complete desktop specialisation stays visible:

- [x] File dialogs (`nv.FileDialog`) — [File Dialogs](docs/guide/window/file_dialogs.md)
- [x] File drop from the OS (`drop_target` modifier) — [Interaction modifiers](docs/guide/modifiers/interaction.md)
- [x] Menu bar (`nv.MenuBar`) — [Menu Bar](docs/guide/window/menu_bar.md)
- [x] Desktop notifications (`nv.Desktop.notify`) — [Notifications](docs/guide/window/notifications.md)
- [x] Tray icon (`nv.TrayIcon`) — [Tray Icon](docs/guide/window/tray_icon.md)
- [x] Multiple windows (`nv.App` / `nv.Window`) — [Multi-Window](docs/guide/window/multi_window.md)
- [x] Window chrome customisation — [Chrome](docs/guide/window/chrome.md)
- [ ] Mouse cursor shapes
- [ ] OS accessibility — screen readers and VoiceOver cannot inspect the UI

The unchecked items are tracked in
[issues](https://github.com/yuksblog/nuiitivet/issues).

---

## 3. Getting started

### 3.1 Requirements

- Python 3.11 or higher
- macOS / Windows / Linux

Main libraries used for drawing and rendering: pyglet, PyOpenGL, skia-python,
materialyoucolor. See [LICENSES/](LICENSES/) for third-party licenses.

### 3.2 Installation

```bash
pip install 'nuiitivet[dev]'
```

With uv, `[dev]` is only needed while developing, so keep it in the dev group:

```bash
uv add nuiitivet
uv add --dev 'nuiitivet[dev]'
```

`[dev]` is the extra the [dev bridge](docs/guide/ai_pair_programming/dev_bridge_mcp.md)'s
MCP server needs. Plain `nuiitivet` is enough to *run* an app, but building with
an AI effectively requires the extra — install it up front.

Then install the bundled [skills](#skills) into your agent. The package bundles
them, so what you install matches the nuiitivet version you have:

```bash
python -m nuiitivet.skills install
```

Where skills belong differs by agent: by default this writes to Claude's
project skills directory, `.claude/skills/`; point `--dest` at another
agent's. Re-run it after upgrading nuiitivet. The other channels — the
Claude Code plugin (which also wires up the dev bridge MCP server) and copying
by hand — are covered in the
[install page](docs/guide/ai_pair_programming/install_skills.md).

Finally, register the dev bridge's MCP server with your agent, so it can see
and drive the app. Add this to your MCP host's configuration:

```json
{
  "mcpServers": {
    "nuiitivet-dev": {
      "command": ".venv/bin/python",
      "args": ["-m", "nuiitivet.dev", "mcp"]
    }
  }
}
```

The Claude Code plugin does this for you.
[Dev Bridge MCP](docs/guide/ai_pair_programming/dev_bridge_mcp.md) has the
details, Windows paths included.

### 3.3 Your first app

- Pull in the design system with `import nuiitivet.material as nv`
- Subclass `ComposableWidget` to build a UI component
- Hand it to `App` and run

The counter from [2.1](#21-reactiveproperty-style-state), complete and runnable:

```python
import nuiitivet.material as nv


class CounterApp(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.count = nv.Observable(0)

    def increment(self):
        self.count.value += 1

    def build(self):
        return nv.Column(
            [
                nv.Text(self.count),
                nv.Button("Increment", on_click=self.increment),
            ],
            gap=20,
            padding=20,
        )


def main():
    # pass the class itself — it is a factory, so hot reload can rebuild it
    app = nv.App(nv.Window(content=CounterApp))
    app.run()


if __name__ == "__main__":
    main()
```

### 3.4 Run it under the dev runner

`python app.py` works, but during development, use the dev runner. Everything
described above — hot reload, the dev bridge, comment mode, layout edit mode,
the source jump — turns on here.

```bash
python -m nuiitivet.dev run app.py
```

See [AI pair-programming](docs/guide/ai_pair_programming/index.md) for the full
workflow.

---

## 4. Documentation

For a deep dive into Nuiitivet's design, visit the **[docs site](https://yuksblog.github.io/nuiitivet/)**.
Browse runnable examples in **[samples/](samples/)** — the apps shown in this
README live there as runnable modules under [samples/readme/](samples/readme/).

### Core Concepts

| Guide | Summary |
| ----- | ------- |
| [The intuitive grammar](docs/guide/intuitive_grammar.md) | What is borrowed from Flutter, SwiftUI / Compose, CSS and WPF, in one small card. |
| [Layout](docs/guide/layout/index.md) | Build UIs with widgets and parameters. |
| [State Management](docs/guide/state-management/index.md) | Reactive `Observable` state that auto-updates the UI. |
| [Modifiers](docs/guide/modifiers/index.md) | Attach decoration and behavior to widgets. |
| [UI Design System](docs/guide/design-system/index.md) | Theming and design tokens. |

### Building Screens

| Guide | Summary |
| ----- | ------- |
| [Overlay](docs/guide/overlay/index.md) | Dialogs, loading, and overlays. |
| [Navigation](docs/guide/navigation/index.md) | Screens, routes, and transitions. |
| [Window & Chrome](docs/guide/window/index.md) | Window sizing, custom chrome, and OS integration — dialogs, menu bar, tray, notifications. |

### Material Design

| Guide | Summary |
| ----- | ------- |
| [Material App](docs/guide/design-system/material_app.md) | App entry point and structure. |
| [Material Theme](docs/guide/design-system/material_theme.md) | Color schemes generated from a seed. |
| [Material Widgets](docs/guide/design-system/material_widgets.md) | Catalog of built-in widgets. |

### Going Further

| Guide | Summary |
| ----- | ------- |
| [Concurrency](docs/guide/concurrency.md) | Choosing a concurrency tool, and safe UI updates from background work. |
| [AI pair-programming](docs/guide/ai_pair_programming/index.md) | Refine and Debug with a coding agent: the on-screen modes, hot reload, the dev bridge, and the skills. |
| [Packaging](docs/guide/packaging.md) | Ship your app to users. |

---

## 5. Current limitations

There are two kinds. **Constraints rooted in the design**, which will not change
easily, and **things simply not built yet**. They mean different things when you
are deciding whether to adopt this, so they are kept separate.

### Rooted in the design

- **A display is required.** `App.run()` opens an OS window, so a truly headless
  environment — no display at all — is not supported.
- **A GPU is recommended, not required.** By default rendering goes through an
  OpenGL/GPU context; on GPU-less or remote setups it falls back to CPU raster
  rendering, which you can also select explicitly
  ([Renderer Selection](docs/guide/window/renderer_selection.md)).

### Not built yet

The OS-integration checklist — what has shipped and what has not — lives in
[2.4 The OS is part of the app](#24-the-os-is-part-of-the-app). None of the
open items is technically out of reach — they just have not been built yet,
and all of them are tracked in
[issues](https://github.com/yuksblog/nuiitivet/issues).

---

## 6. License

Nuiitivet is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for
more info.
