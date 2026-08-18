# Nuiitivet

![Nuiitivet showcase](docs/assets/readme_hero_showcase.gif)

An intuitive UI framework for Python.

[![PyPI version](https://img.shields.io/pypi/v/nuiitivet)](https://pypi.org/project/nuiitivet/)
[![Python versions](https://img.shields.io/pypi/pyversions/nuiitivet)](https://pypi.org/project/nuiitivet/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

## 1. Why Nuiitivet?

I have just one thing to say: I want to write UI intuitively.

### 1.1 Declarative UI

Nuiitivet offers a declarative UI that blends the best parts of frameworks like Flutter, SwiftUI, and WPF.

At its core, you build UIs by composing widgets, just like in Flutter.

```python
login_form = Column(
    [
        # Username and Password fields
        TextField(
            value="",
            label="Username",
            width=300,
        ),
        TextField(
            value="",
            label="Password",
            width=300,
        ),
        # Login Button
        Button(
            "Login",
            on_click=lambda: print("Login clicked"),
            width=300,
        )
    ],
    gap=20,
    padding=20,
)
```

![Login form](docs/assets/readme_login_form.png)

What sets Nuiitivet apart from Flutter is that size, alignment, and spacing are specified as widget parameters. Treating them as parameters of a widget — rather than as widgets in their own right — feels more natural, and it lets you avoid the deep nesting hell that Flutter tends to fall into.

```python
# Writing in Flutter style often leads to deep nesting
Padding(
    padding=EdgeInsets.all(12),
    child=SizedBox(
        width=200,
        child=Text("Hello"),
    ),
)
```

```python
# With Nuiitivet, you can specify them directly
Text(
    "Hello",
    padding=12,
    width=200,
)
```

Nuiitivet also adopts modifiers from SwiftUI and Jetpack Compose.
Instead of wrapping a widget, you attach decoration and behavior so they feel like they grow out of the widget — and they chain together naturally with `|`.

```python
Button("OK").modifier(
    tooltip("Submit") | clickable(...) | background("#2196F3")
)
```

For why modifiers exist and what kinds are available, see [docs/guide/modifiers/index.md](docs/guide/modifiers/index.md).

### 1.2 Data Binding

Dynamic UIs need state management.
With **data binding**, you declare *what the UI shows* in terms of your state — once — and that link stays live. Change the state, and every bound part of the UI follows on its own. You never write the code that pushes a value into a widget, and the UI can't drift out of sync with your state, because your state *is* the UI's single source of truth.

That mechanism is `Observable`. It binds directly to the UI, and it also carries operators like `throttle()` and `debounce()` like Rx — the best of both worlds. (It's inspired by WPF's ReactiveProperty.)

Let me walk you through three things I like about it.

#### 1. Complete separation of state and UI

When you set a value on an `Observable`, the bound UI updates automatically. Inside build(), all you ever write is the UI declaration.

```python
class CounterApp(ComposableWidget):
    def __init__(self):
        super().__init__()
        self.count = Observable(0)

    def increment(self):
        self.count.value += 1

    def build(self):
        return Column(
            [
                # Count display
                Text(self.count),
                # Increment button
                Button(
                    "Increment",
                    on_click=self.increment,
                )
            ]
        )
```

![Counter](docs/assets/readme_counter.png)

With the ViewModel pattern, you can take this even further — separating cleanly at the class level rather than the method level.

#### 2. Declarative data flow

State derived from multiple values can be declared as a formula. Below, `total` is defined as the sum of `count_a` and `count_b`; whenever either one changes, it's recalculated automatically. On the UI side, you just drop in `total` as is.

```python
self.count_a = Observable(0)
self.count_b = Observable(0)

# total is declared as a + b; it recalculates automatically when a or b changes
self.total = self.count_a.combine(self.count_b).compute(lambda a, b: a + b)
```

![Multi counter](docs/assets/readme_multi_counter.png)

#### 3. Async in the same style

This is where the ReactiveProperty heritage really shines. You can slot in an Rx-style operator like `debounce()` and then bind the result straight to the UI. Even something like a search box — "thin out the keystrokes, then process" — is a single line.

```python
self.query = Observable("")

# debounce like Rx, then bind the result straight to the UI
self.results = self.query.debounce(0.3).map(search_api)
```

The full guide to Observable is in [docs/guide/state-management/index.md](docs/guide/state-management/index.md).

### 1.3 Event Handlers

Event handlers like on_click() are written imperatively.
A handler does procedural things — popping up a dialog, branching on its result — so writing it imperatively feels natural.

```python
class CounterApp(ComposableWidget):
    count = Observable(0)

    # Write procedures in event handler
    def handle_increment(self):
        # 1. Output log
        print(f"Current count: {self.count.value}")
        # 2. Increment count
        self.count.value += 1
        # 3. Milestone check
        if self.count.value % 10 == 0:
            print("Milestone reached!")
        
    def build(self):
        return Column(
            [
                Text(f"count: {self.count.value}"),
                Button(
                    "Increment",
                    on_click=self.handle_increment,  # Execute on click
                )
            ]
        )
```

Logic → UI declaratively, UI → logic imperatively. What matters in both directions is that it stays intuitive to write — and that's the one thing Nuiitivet stands for.

## 2. First Steps

### 2.1. Requirements

- Python 3.10 or higher
- macOS / Windows / Linux

Main internal libraries used (drawing/rendering):

- pyglet
- PyOpenGL
- skia-python
- materialyoucolor

See [LICENSES/](LICENSES/) for third-party licenses.

### 2.2. Installation

You can install it easily with pip.

```bash
pip install nuiitivet
```

### 2.3. Your First App

To create an application with Nuiitivet, follow these steps:

- Import your UI design system with `import nuiitivet.material as nv`
- Inherit from `ComposableWidget` to create a UI component
- Pass the UI component to `App` and start the application

```python
import nuiitivet.material as nv

class CounterApp(nv.ComposableWidget):
    def __init__(self):
        super().__init__()
        self.count = nv.Observable(0)

    def handle_increment(self):
        # 1. Output log
        print(f"Current count: {self.count.value}")
        # 2. Increment count
        self.count.value += 1
        # 3. Milestone check
        if self.count.value % 10 == 0:
            print("Milestone reached!")
        
    def build(self):
        return nv.Column(
            [
                nv.Text(self.count),
                nv.Button(
                    "Increment",
                    on_click=self.handle_increment,
                )
            ],
            gap=20,
            padding=20,
        )

def main():
    # Start with App (pass the class as a factory so hot reload can rebuild it)
    app = nv.App(content=CounterApp)
    app.run()

if __name__ == "__main__":
    main()
```

### 2.4 AI pair-programming

Once your app runs, you develop it in a live loop built for pairing with an AI
assistant. Launch with the dev runner instead of running the module directly:

```bash
python -m nuiitivet.dev path/to/app.py
```

Now you and the assistant work on the same running window:

- **You watch the assistant work in real time.** Every edit it makes and every
  screen it drives shows up live — the window rebuilds in place on each save and
  your `Observable` state survives, and even a screen you are stepping through
  under the VSCode **F5** debugger keeps updating. No restart, no lost state.
- **Your turn is hands-on too.** You direct the assistant, but you can just as
  well edit code and manually test the screen yourself in the same session.
- **The assistant sees what *you* did.** Beyond your instructions, it can read
  which files you changed and which UI actions you took, so you stay on the same
  page and the conversation gets sharper.

Three pieces make this work:

- **Hot reload**: real-time screen updates.
- **MCP Dev Bridge**: lets the assistant read and drive the running app, and read your edit/interaction logs.
- **`nuiitivet-app` skill**: an AI skill that keeps the assistant's code idiomatic.

See [AI pair-programming](docs/guide/ai_pair_programming/index.md) for the full workflow.

## 3. Documentation

For a deep dive into Nuiitivet's design, visit the **[docs site](https://yuksblog.github.io/nuiitivet/)**.
Browse runnable examples in **[samples/](samples/)** — every snippet in this README lives there as a runnable module under [samples/readme/](samples/readme/).

### Core Concepts

| Guide | Summary |
| ----- | ------- |
| [Layout](docs/guide/layout/index.md) | Build UIs with widgets and parameters. |
| [State Management](docs/guide/state-management/index.md) | Reactive `Observable` state that auto-updates the UI. |
| [Modifiers](docs/guide/modifiers/index.md) | Attach decoration and behavior to widgets. |
| [UI Design System](docs/guide/design-system/index.md) | Theming and design tokens. |

### Building Screens

| Guide | Summary |
| ----- | ------- |
| [Overlay](docs/guide/overlay/index.md) | Dialogs, loading, and overlays. |
| [Navigation](docs/guide/navigation/index.md) | Screens, routes, and transitions. |
| [Window & Chrome](docs/guide/window/index.md) | Window sizing, position, and custom chrome. |

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
| [AI pair-programming](docs/guide/ai_pair_programming/index.md) | Live edit-save-see, the MCP dev bridge, and the `nuiitivet-app` skill. |
| [Packaging](docs/guide/packaging.md) | Ship your app to users. |

## 4. Known Limitations

- **No OS accessibility integration.** Everything is drawn with Skia, so the app
  does not participate in the OS accessibility tree — screen readers and
  VoiceOver cannot inspect the UI. This is a real constraint for domains that
  require assistive-technology support.
- **A GPU is recommended, not required.** Live rendering goes through pyglet +
  PyOpenGL + skia, and by default it uses an OpenGL/GPU context. On GPU-less,
  software-OpenGL (llvmpipe), or remote setups it falls back to CPU/raster
  rendering, which you can also select explicitly — see
  [Renderer Selection](docs/guide/window/renderer_selection.md).
- **A display is required.** `App.run()` opens an OS window, so truly headless
  environments (no display at all) are not supported in any renderer mode.

## 5. License

Nuiitivet is licensed under the Apache License 2.0. See the LICENSE file for more info.
