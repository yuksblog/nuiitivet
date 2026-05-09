# Nuiitivet

![Nuiitivet showcase](docs/assets/readme_hero_showcase.gif)

Nuiitivet is an intuitive UI framework for Python.

[![PyPI version](https://img.shields.io/pypi/v/nuiitivet)](https://pypi.org/project/nuiitivet/)
[![Python versions](https://img.shields.io/pypi/pyversions/nuiitivet)](https://pypi.org/project/nuiitivet/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

## 1. Welcome to Nuiitivet

Hi there, thanks for stopping by.
I'd like to take a little of your time to introduce you to Nuiitivet. It should only take about 10 minutes to read, so I'd appreciate it if you could stick with me for a bit.

### 1.1 Declarative UI

Do you ever create small applications for work or as a hobby? With Python, you can start writing code immediately and build things easily, which is very convenient. But even for small tools, you often find yourself wanting a UI, don't you? That's where Nuiitivet comes in. You can build a UI quickly using a declarative UI style like Flutter or SwiftUI.
For example, a login form can be written like this:

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

If you know Flutter or SwiftUI, you know how convenient declarative UIs are.
Even if you don't, I hope you can see how intuitive it is to write.

But if you do know Flutter or SwiftUI, you might be worried about "Widget nesting hell" or "Modifier chain hell".
Don't worry. We've balanced the roles of Widgets, parameters, and Modifiers perfectly to keep things simple.

For example, if you specify padding or size with Padding or SizedBox like in Flutter, the Widget nesting tends to get deep. But with Nuiitivet, you can specify them directly as parameters, so you can write it simply.

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

Modifiers are positioned for intermediate users and above. For small applications, you probably won't need to use Modifiers.

#### Why Modifiers?

Wrapping a widget is usually intuitive — but not always. Take **Tooltip** as an example. A tooltip shows a small description when you hover over a widget. The mental model is: *the tooltip grows out of the widget*.

In Flutter / Jetpack Compose, the code looks like this:

```python
# Flutter / Jetpack style: Tooltip wraps the widget
Tooltip(message="Submit", child=Button("OK"))
```

`Tooltip` wraps `Button` — the opposite of what you'd imagine.

In Nuiitivet, a modifier attaches to the widget instead:

```python
# Nuiitivet: the tooltip grows out of the button
Button("OK").modifier(tooltip("Submit"))
```

The tooltip grows out of the button — just as you'd imagine.

Tooltip is just one example. Modifiers cover a wide range of features — and they chain together naturally with `|`:

```python
Button("OK").modifier(
    tooltip("Submit") | clickable(...) | background("#2196F3")
)
```

We explain Widgets and parameters in [docs/guide/layout.md](docs/guide/layout.md), so check it out if you're interested.
Modifiers are explained in [docs/guide/modifier.md](docs/guide/modifier.md).

### 1.2 Data Binding

It's fine when the application is small, but as it grows, UI code and logic code tend to get mixed up, making maintenance difficult. This is a problem that has plagued me in many languages, not just Python.

So, leveraging my experience, Nuiitivet provides a mechanism to cleanly separate UI and logic. First, let me explain logic -> UI updates.

For logic -> UI updates, we adopted the Reactive concept.
In Nuiitivet, when you set a value to an Observable, the UI is automatically updated.

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

This might not fully convey the benefits of Reactive programming.
Let's look at an example where we increase counters and display the total.

```python
class MultiCounterApp(ComposableWidget):
    def __init__(self):
        super().__init__()
        self.count_a = Observable(0)
        self.count_b = Observable(0)

        self.total = self.count_a.combine(self.count_b).compute(lambda a, b: a + b)

    def increment_a(self):
        self.count_a.value += 1

    def increment_b(self):
        self.count_b.value += 1

```

Take a look at the `self.total` line.
You can read from the code that `total` is defined as the sum of `count_a` and `count_b`. Of course, `total` is automatically recalculated when `count_a` or `count_b` is updated, and in the UI code, you just need to specify `total` as is.

```python
    def build(self):
        return Column(
            [
                # Counter A
                Row(
                    [
                        Text(self.count_a.value),
                        Button("+", on_click=self.increment_a),
                    ],
                ),
                # Counter B
                Row(
                    [
                        Text(self.count_b.value),
                        Button("+", on_click=self.increment_b),
                    ],
                ),
                # Just specify total!
                Text(self.total),
            ],
        )
```

![Multi counter](docs/assets/readme_multi_counter.png)

In the UI code, you just specify `total` without worrying about the logic. I think it's cleanly separated. Moreover, the definition of `total` can also be written Reactively, making the intent easy to read from the code.

Detailed usage of Observable is summarized in [docs/guide/observable.md](docs/guide/observable.md), so check it out if you're interested.

### 1.3. Event Handlers

For UI -> logic, you just write the processing sequentially in event handlers.
Since logic -> UI is written declaratively with Reactive, shouldn't this be declarative too?
No, no, no. Ask yourself honestly. When a UI event occurs, don't you really want to write "what to do" sequentially?

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

Don't try to force it to be declarative; just write the procedures sequentially.
Another common case is displaying a dialog. You click a button, show a dialog, and branch processing based on OK/Cancel. You want to write this procedurally too, right?

### 1.4. Declarative vs Imperative

I've introduced Nuiitivet, but what do you think?

You might feel uneasy mixing declarative and imperative styles. But if you think about it, SQL retrieves data declaratively, but application code is written imperatively, right? So it's not strange at all for UI code to mix declarative and imperative styles. The important thing is that it can be written "intuitively".

"Intuitive" differs from person to person, so I don't know if Nuiitivet is intuitive for everyone. But I think it has become a framework that I can write intuitively. So please give it a try.

## 2. First Steps

### 2.1. Requirements

- Python 3.10 or higher
- macOS / Windows / Linux(not tested)

Main internal libraries used (drawing/rendering):

- pyglet
- PyOpenGL
- skia-python
- material-color-utilities

See [LICENSES/](LICENSES/) for third-party licenses.

### 2.2. Installation

You can install it easily with pip.

```bash
pip install nuiitivet
```

### 2.3. Your First App

To create an application with Nuiitivet, follow these two steps:

- Inherit from `ComposableWidget` to create a UI component
- Pass the UI component to `MaterialApp` and start the application

```python
from nuiitivet.material.app import MaterialApp
from nuiitivet.material import Text, Button
from nuiitivet.layout.column import Column
from nuiitivet.observable import Observable
from nuiitivet.widgeting.widget import ComposableWidget

class CounterApp(ComposableWidget):
    def __init__(self):
        super().__init__()
        self.count = Observable(0)

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
                Text(self.count),
                Button(
                    "Increment",
                    on_click=self.handle_increment,
                )
            ],
            gap=20,
            padding=20,
        )

def main():
    # Create counter app
    counter_app = CounterApp()
    
    # Start with MaterialApp
    app = MaterialApp(content=counter_app)
    app.run()

if __name__ == "__main__":
    main()
```

## 3. Documentation

For a deep dive into Nuiitivet's design, visit the **[docs site](https://yuksblog.github.io/nuiitivet/)**.

| Concept | Summary | Guide |
|---------|---------|-------|
| Layout | Build UIs with widgets and parameters. | [docs/guide/layout.md](docs/guide/layout.md) |
| Modifier | Attach decoration and behavior to widgets. | [docs/guide/modifier.md](docs/guide/modifier.md) |
| Observable | Reactive state that auto-updates the UI. | [docs/guide/observable.md](docs/guide/observable.md) |

## 4. License

Nuiitivet is licensed under the Apache License 2.0. See the LICENSE file for more info.

## Appendix: README Samples

All README examples are available as runnable modules under `src/samples/`.
