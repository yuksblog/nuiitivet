# Nuiitivet

Nuiitivet is an intuitive UI framework for Python.

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
        OutlinedTextField(
            value="",
            label="Username",
            width=300,
        ),
        OutlinedTextField(
            value="",
            label="Password",
            width=300,
        ),
        # Login Button
        FilledButton(
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

We explain Widgets and parameters in [3.1 Layout](#31-layout), so check it out if you're interested.
Modifiers are explained in [3.2 Modifier](#32-modifier).

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
                FilledButton(
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
                        FilledButton("+", on_click=self.increment_a),
                    ],
                ),
                # Counter B
                Row(
                    [
                        Text(self.count_b.value),
                        FilledButton("+", on_click=self.increment_b),
                    ],
                ),
                # Just specify total!
                Text(self.total),
            ],
        )
```

![Multi counter](docs/assets/readme_multi_counter.png)

In the UI code, you just specify `total` without worrying about the logic. I think it's cleanly separated. Moreover, the definition of `total` can also be written Reactively, making the intent easy to read from the code.

Detailed usage of Observable is summarized in [3.3 Observable](#33-observable), so check it out if you're interested.

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
                FilledButton(
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
- macOS(tested) / Windows(not tested) / Linux(not tested)

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
from nuiitivet.material import Text, FilledButton
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
                FilledButton(
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

## 3. Nuiitivet Concepts

### 3.1. Layout

In Nuiitivet, you can build UIs using only Widgets and parameters.
You don't need unnecessary wrapper widgets.

```python
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import Text, FilledButton, TextButton

# Layout vertically with Column
Column(
    children=[
        Text("Title", padding=10),
        Text("Subtitle", padding=10),
        Text("Body", padding=10),
    ],
    gap=16,                    # Space between children
    padding=20,                # Outer padding
    cross_alignment="start",   # Cross axis alignment (start/center/end)
)

# Layout horizontally with Row
Row(
    children=[
        FilledButton("OK"),
        TextButton("Cancel"),
    ],
    gap=12,                     # Space between children
    main_alignment="end",       # Main axis alignment (start/center/end/space-between)
    cross_alignment="center",   # Cross axis alignment
)
```

![Layout](docs/assets/readme_layout.png)

By providing appropriate parameters according to the Widget's role, you can keep Widget nesting shallow.

- **All Widgets**
  - `padding`: Inner padding of the Widget
  - `width` / `height`: Widget size specification (fixed value or automatic)
    - Square widgets like Icons are specified only with `size`
- **Single Child Layout Widgets**
  - `alignment`: Alignment of the single child (Container)
- **Multi-Child Layout Widgets**
  - `gap`: Space between child elements (Column / Row)
  - `main_alignment` / `cross_alignment`: Alignment of multiple children (Column / Row)

The following Layout Widgets are available:

- **Column**: Layout children vertically
- **Row**: Layout children horizontally
- **Stack**: Layout children overlapping each other
- **Flow**: Layout children with wrapping
- **Grid**: Layout children in a grid
- **Container**: Basic layout Widget containing a single child
- **Spacer**: Insert blank space

### 3.2. Modifier

Modifiers are a mechanism for adding functionality to Widgets.
Use them when you want to add decorations like background color or corner radius to a Widget.

You can add functionality to a Widget by passing a Modifier to the `modifier()` method that all Widgets have. If you want to attach multiple Modifiers, you can chain them with the `|` operator.

```python
from nuiitivet.material import Text
from nuiitivet.modifiers import background, corner_radius, border

# Add background color with Background
text1 = Text("Hello").modifier(background("#FF5722"))

# Add corner radius with CornerRadius
text2 = Text("Rounded Box").modifier(background("#2196F3") | corner_radius(8))

```

![Modifier](docs/assets/readme_modifier.png)

Currently, the Modifiers available in Nuiitivet are:

**Decoration:**

- **background**: Add background color
- **border**: Add border
- **corner_radius**: Add corner radius
- **clip**: Add clipping
- **shadow**: Add shadow

**Interaction:**

- **clickable**: Make clickable
- **hoverable**: Make hoverable
- **focusable**: Make focusable

**Others:**

- **scrollable**: Make scrollable
- **will_pop**: Handle back navigation

It's similar to Modifiers in SwiftUI / Jetpack Compose, but Nuiitivet does not provide layout-related functions in Modifiers. Layout should be handled by Widgets and parameters alone; allowing Modifiers to handle layout would make the code complex.

### 3.3. Observable

Observable is a mechanism that uses Reactive programming concepts to simplify UI updates. When a value changes, the UI is automatically updated.

Observables can be transformed and combined using methods like `.map()`, `.combine()`, and `Observable.compute()`.

```python
from nuiitivet.observable import Observable, combine

# 1-to-1 transformation with .map()
price = Observable(1000)
formatted_price = price.map(lambda p: f"${p:,}")

# Combine multiple Observables (two) with .combine()
price = Observable(1000)
quantity = Observable(2)
subtotal = price.combine(quantity).compute(lambda p, q: p * q)

# Combine 3 or more with combine() function
tax_rate = Observable(0.1)
total = combine(price, quantity, tax_rate).compute(
    lambda p, q, t: int(p * q * (1 + t))
)

# Complex calculation and automatic dependency tracking with Observable.compute()
class CartViewModel:
    def __init__(self):
        self.price = Observable(1000)
        self.quantity = Observable(2)
        self.discount = Observable(0.1)
        self.tax_rate = Observable(0.1)

        # Automatically track dependent Observables
        self.total = Observable.compute(
            lambda: int(
                self.price.value
                * self.quantity.value
                * (1 - self.discount.value)
                * (1 + self.tax_rate.value)
            )
        )
```

Here are the APIs available in Observable and points on how to use them.

**Basic Operations:**

- **`.value`**: Get/set the current value of the Observable
- **`.subscribe(callback)`**: Observe value changes and execute a callback when changed

**Transformation / Combination:**

- **`.map(fn)`**: Transform a single Observable (e.g., number -> string)
- **`.combine(other)`**: Combine two Observables
- **`combine(a, b, ...)`**: Combine 3 or more Observables
- **`Observable.compute(fn)`**: When there is complex logic such as conditional branching, or when automatic dependency tracking is convenient

**Timing Control:**

- **`.debounce(seconds)`**: Notify only if the value has not changed for the specified number of seconds (search input, form validation, etc.)
- **`.throttle(seconds)`**: Notify the first value immediately, then notify at most once every specified number of seconds (mouse tracking, scroll position, etc.)

**Thread Control:**

- **`.dispatch_to_ui()`**: Dispatch value change notifications to the UI thread in a multi-threaded environment

## 4. License

Nuiitivet is licensed under the Apache License 2.0. See the LICENSE file for more info.

## Appendix: README Samples

All README examples are available as runnable modules under `src/samples/`.
