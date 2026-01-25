---
layout: default
---

# Observable Guide

Observables in the nuiitivet framework are a core feature for realizing reactive programming. They allow for declarative and intuitive UI state management.

## Quick Start

### Basic Usage

```python
import nuiitivet as nv

class Counter:
    count = nv.Observable(0)

# Create instance
counter = Counter()

# Subscribe to value changes
counter.count.subscribe(lambda value: print(f"Count: {value}"))

# Update value
counter.count.value = 1  # -> "Count: 1" is printed
counter.count.value = 2  # -> "Count: 2" is printed
```

### Integration with UI

```python
import nuiitivet as nv
from nuiitivet import material

class CounterApp:
    count = nv.Observable(0)
    
    def build(self):
        return nv.Column(
            children=[
                # Automatically display the value of count (Reactive)
                material.Text(text=self.count.map(lambda c: f"Count: {c}")),
                material.FilledButton(
                    text="Increment",
                    on_click=lambda: self.increment()
                )
            ]
        )
    
    def increment(self):
        self.count.value += 1  # UI is automatically updated
```

## Basic Concepts

### What is an Observable?

An Observable represents a "value that can be observed". When the value changes, a notification is sent to all registered subscribers.

**Features:**

- ✅ Per-instance state management via Descriptor pattern
- ✅ Automatic change notifications
- ✅ Automatic cleanup to prevent memory leaks
- ✅ Efficient updates using batch()

### Descriptor Pattern

Observables are defined as class attributes, but each instance holds an independent value:

```python
class Model:
    value = Observable(0)

a = Model()
b = Model()

a.value.value = 10
b.value.value = 20

print(a.value.value)  # -> 10
print(b.value.value)  # -> 20 (Independent)
```

## API Reference

### Basic Operations

#### Creating an Observable

```python
# Create with initial value
name = Observable("Alice")
age = Observable(20)
items = Observable([])
```

#### Getting and Setting Values

```python
# Get value
current_value = observable.value.value

# Set value
observable.value.value = new_value
```

#### Subscribing

```python
# Register a callback
subscription = observable.value.subscribe(lambda value: print(value))

# Unsubscribe (Usually not needed - managed automatically)
subscription.unsubscribe()
```

### Reactive Operators

#### `.map(fn)` - Transform Value

Transforms the value of a single Observable.

```python
age = Observable(20)
is_adult = age.map(lambda x: x >= 18)

is_adult.subscribe(lambda v: print(f"Adult: {v}"))
age.value = 15  # -> "Adult: False"
age.value = 20  # -> "Adult: True"
```

**Usage Examples:**

- Formatting numbers: `price.map(lambda p: f"¥{p:,}")`
- Converting booleans: `count.map(lambda c: c > 0)`
- Extracting object properties: `user.map(lambda u: u.name)`

#### `.combine(other)` - Combine Multiple Observables

Combines two Observables. Used in combination with `.compute(fn)`.

```python
price = Observable(100)
quantity = Observable(2)

# Combine two values and calculate
total = price.combine(quantity).compute(lambda p, q: p * q)

total.subscribe(lambda v: print(f"Total: {v}"))
price.value = 200  # -> "Total: 400"
quantity.value = 3  # -> "Total: 600"
```

#### `combine(a, b, ...)` - Combine 3+ Observables (Function Style)

When combining 3 or more Observables, the function style is concise.

```python
from nuiitivet.observable import combine

price = Observable(100)
quantity = Observable(2)
discount = Observable(0.1)

# Combine 3 values
total = combine(price, quantity, discount).compute(
    lambda p, q, d: p * q * (1 - d)
)

total.subscribe(lambda v: print(f"Total: ¥{v:.0f}"))
# price=100, qty=2, discount=0.1 -> "Total: ¥180"
```

#### `Observable.compute(fn)` - Automatic Dependency Tracking

Automatic dependency tracking is useful for cases involving complex calculations or conditional branching.

```python
class Cart:
    show_detail = Observable(True)
    price = Observable(100)
    quantity = Observable(2)
    
    def __init__(self):
        # Calculation with conditional branching - dependencies are tracked automatically
        self.display = Observable.compute(lambda: (
            f"¥{self.price.value * self.quantity.value:,}"
            if self.show_detail.value
            else "---"
        ))
```

**Benefits:**

- No need to explicitly specify dependencies
- Handles dynamic dependencies due to conditional branching
- Code is intuitive and easy to read

### batch() - Efficient Updates

When updating multiple Observables simultaneously, using `batch()` can group notifications into a single update.

```python
from nuiitivet.observable import batch

price = Observable(100)
quantity = Observable(2)
total = price.combine(quantity).compute(lambda p, q: p * q)

# Without batch - total is recalculated twice
price.value = 200
quantity.value = 3

# With batch - total is recalculated only once
with batch():
    price.value = 200
    quantity.value = 3
# total is recalculated only once here
```

**Automatic batch:**
Since batch is automatically applied within UI event handlers, you usually don't need to write `batch()` explicitly.

```python
def on_click(self):
    # Automatically batched within event handler
    self.price.value = 200
    self.quantity.value = 3
    # -> Notified only once
```

## Selection Guide

### Which Operator to Use?

```python
# ✅ 1:1 Transformation -> .map()
is_adult = age.map(lambda x: x >= 18)
formatted_price = price.map(lambda p: f"¥{p:,}")

# ✅ 2 Observables -> .combine().compute()
subtotal = price.combine(quantity).compute(lambda p, q: p * q)
full_name = first_name.combine(last_name).compute(lambda f, l: f"{f} {l}")

# ✅ 3+ Observables -> combine(...).compute()
total = combine(price, quantity, discount).compute(
    lambda p, q, d: p * q * (1 - d)
)

# ✅ Complex Calculation / Conditional Branching -> Observable.compute()
display = Observable.compute(lambda: (
    self.tax_included.value if self.show_tax.value
    else self.tax_excluded.value
))
```

### Performance Considerations

- `.map()` and `.combine()` internally use `Observable.compute()`, so performance is equivalent.
- Since explicit dependencies (`.map()`, `.combine()`) are more readable, they are recommended for simple cases.
- `Observable.compute()` is suitable for conditional branching and complex logic.

## Thread Safety

### The Problem

Updating an Observable from a worker thread can cause UI widgets to update outside the UI thread, leading to crashes.

```python
import threading

class ViewModel:
    data = Observable([])

# ❌ Dangerous Code
def worker():
    result = fetch_data()  # Heavy process
    viewmodel.data.value = result  # <- Update from worker thread

threading.Thread(target=worker).start()

# Subscribe in UI
viewmodel.data.subscribe(lambda d: update_widget(d))  # <- Crash!
```

### Solution: `.dispatch_to_ui()`

Attach `.dispatch_to_ui()` to Observables that affect the UI to ensure update notifications run on the UI thread.

```python
class ViewModel:
    data = Observable([])

    def __init__(self):
        # Enable .dispatch_to_ui() for Observables used for UI binding
        self.data.dispatch_to_ui()
    
    def load_async(self):
        def worker():
            result = fetch_data()
            self.data.value = result  # ✅ Notification runs on UI thread
        
        threading.Thread(target=worker).start()
```

### Default Behavior

If `.dispatch_to_ui()` is not called, Observables run **fast** (no thread check).

```python
# Logic Layer - Default (Fast)
class DataProcessor:
    raw_data = Observable([])  # No dispatch
    filtered = raw_data.map(lambda x: [i for i in x if i > 0])  # Fast
```

**Usage Principles:**

- **UI Layer (ViewModel)**: Explicitly call `.dispatch_to_ui()`
- **Logic Layer**: Do not specify anything (Default fast)

### Usage in Method Chains

`.dispatch_to_ui()` can be inserted in the middle or at the end of a method chain.

```python
# Pattern 1: Create at the end
total = (price
         .combine(quantity)
         .compute(lambda p, q: p * q)
         .dispatch_to_ui())

# Pattern 2: Create in the middle
total = (price
         .combine(quantity)
         .dispatch_to_ui()
         .compute(lambda p, q: p * q))
```

### Important Constraints

Inside the compute function, you **must not access objects limited to the UI thread**.

```python
# ❌ Wrong: Accessing Widget inside compute
class ViewModel:
    label = Label("Count: 0")  # UI Widget
    count = Observable(0)
    
    # ❌ Will crash!
    display = Observable.compute(lambda:
        f"Count: {self.label.text}"  # <- label.text is limited to UI thread
    ).dispatch_to_ui()

# ✅ Correct: Use only Observable values
class ViewModel:
    count = Observable(0)
    
    # ✅ Use only Observable value
    display = count.map(lambda c: f"Count: {c}")
    
    # Update UI via subscribe
    display.subscribe(lambda text: self.label.text = text)
```

**Rules:**

- ✅ Use only Observable values inside compute
- ❌ Do not touch UI Widgets or UI thread-specific objects
- ✅ Perform UI updates in the subscribe callback

## Timing Control

For high-frequency events (search input, mouse movement, scrolling, etc.), limiting processing frequency can improve performance.

### debounce() - Wait for Input to Stabilize

Executes **once after a specified time has passed since the last change** in a series of changes.

**Use Cases:**

- Search box input (Search after user stops typing)
- Form validation (Check after input completion)
- Auto-save (Save after editing stops)

```python
from nuiitivet.observable import Observable

class SearchModel:
    query = Observable("")
    
    def __init__(self):
        # Execute search if no input for 0.5 seconds
        self.debounced_query = self.query.debounce(0.5)
        self.debounced_query.subscribe(self._perform_search)
    
    def _perform_search(self, query: str):
        if query.strip():
            print(f"🔍 Searching for: '{query}'")
            # API call, etc.

# Example
model = SearchModel()
model.query.value = "h"      # Not searched
model.query.value = "he"     # Not searched
model.query.value = "hello"  # Not searched
# ... Wait 0.5 seconds ...
# -> "🔍 Searching for: 'hello'" is executed
```

**Benefits:**

- Significantly reduces number of API requests
- Reduces server load
- Avoids unnecessary calculations

### throttle() - Sample Regularly

**Executes the first change immediately, then executes only at specified intervals**.

**Use Cases:**

- Mouse movement tracking
- Scroll position monitoring
- Window resize events
- Real-time data updates

```python
from nuiitivet.observable import Observable

class MouseTracker:
    mouse_x = Observable(0)
    mouse_y = Observable(0)
    
    def __init__(self):
        # Sample at 0.1s intervals (Max 10 times/sec)
        self.throttled_x = self.mouse_x.throttle(0.1)
        self.throttled_y = self.mouse_y.throttle(0.1)
        
        self.throttled_x.subscribe(self._update_display)
    
    def _update_display(self, x: int):
        print(f"📍 Position updated: {x}")

# Example
tracker = MouseTracker()
tracker.mouse_x.value = 10   # -> Immediately "📍 Position updated: 10"
tracker.mouse_x.value = 20   # Ignored (less than 0.1s)
tracker.mouse_x.value = 30   # Ignored (less than 0.1s)
# ... 0.1s passed ...
# -> "📍 Position updated: 30" is executed
```

**Benefits:**

- Maintains UI responsiveness (First change reflected immediately)
- Ensures performance even with high-frequency events
- Smooth UX with periodic updates

### debounce vs throttle

| Feature | debounce | throttle |
| ------ | ---------- | ---------- |
| **First change** | Wait | Execute immediately |
| **During continuous changes** | Keep waiting | Execute periodically |
| **Last change** | Always execute | Depends on timing |
| **Execution count** | Minimized | Constant interval |

```python
# Search Box -> debounce (Wait for input completion)
search_query = Observable("")
debounced = search_query.debounce(0.5)  # ✅ Search after user stops typing

# Mouse Tracking -> throttle (Immediate reaction + Periodic update)
mouse_pos = Observable((0, 0))
throttled = mouse_pos.throttle(0.1)  # ✅ First movement immediate, then every 0.1s
```

### Chainable

debounce/throttle can also be chained with other operators.

```python
# debounce -> map -> dispatch_to_ui
formatted_query = (
    query
    .debounce(0.5)
    .map(lambda q: q.strip().lower())
    .dispatch_to_ui()
)

# throttle -> compute
position_display = (
    mouse_x
    .throttle(0.1)
    .combine(mouse_y.throttle(0.1))
    .compute(lambda x, y: f"({x}, {y})")
)
```

**Notes:**

- The `.value` property returns the original value immediately (no delay).
- Avoid heavy processing as it runs on the UI thread.

## Best Practices

### 1. ViewModel Pattern

Consolidate UI logic into a ViewModel class.

```python
class TodoViewModel:
    items = Observable([])
    selected_item = Observable(None)
    
    # Derived states defined as None initially
    item_count = None
    has_items = None
    
    def __init__(self):
        # Enable .dispatch_to_ui() for UI Observables
        self.items.dispatch_to_ui()
        self.selected_item.dispatch_to_ui()
        self.item_count = self.items.map(lambda items: len(items))
        self.has_items = self.item_count.map(lambda count: count > 0)
    
    def add_item(self, text: str):
        with batch():
            current = self.items.value
            self.items.value = current + [{"text": text, "done": False}]
```

### 2. Defining Derived State

Define values calculated from other Observables as computed.

```python
class ShoppingCart:
    items = Observable([])
    tax_rate = Observable(0.1)
    
    def __init__(self):
        # Subtotal
        self.subtotal = self.items.map(
            lambda items: sum(item["price"] * item["qty"] for item in items)
        )
        
        # Total (Subtotal + Tax)
        self.total = combine(self.subtotal, self.tax_rate).compute(
            lambda sub, rate: sub * (1 + rate)
        )
```

### 3. Memory Management

Usually, unsubscribing is not necessary (managed automatically).

```python
# ✅ Recommended: Leave to automatic management
def create_counter():
    count = Observable(0)
    doubled = count.map(lambda x: x * 2)
    return doubled
# Automatically cleaned up when out of scope
```

Use `Disposable` if you want to explicitly manage long-lived objects.

```python
from nuiitivet.observable import Disposable

class ViewModel(Disposable):
    def __init__(self):
        super().__init__()
        
        self.count = Observable(0)
        self.doubled = self.count.map(lambda x: x * 2)
        
        # Register to Disposable
        self.add_disposable(self.doubled)
    
    def dispose(self):
        super().dispose()  # Release all at once
```

### 4. Utilizing batch

Group related updates with `batch()`.

```python
def reset_form(self):
    with batch():
        self.name.value = ""
        self.email.value = ""
        self.age.value = 0
        self.errors.value = []
    # Notified only once here
```

### 5. Custom Comparison Function

You can customize the identity check for values.

```python
# Default: Compare with ==
count = Observable(0)

# Custom Compare: Always notify
always_notify = Observable(0, compare=lambda a, b: False)

# Custom Compare: Notify on specific condition
def compare_users(a, b):
    if a is None or b is None:
        return a is b
    return a.id == b.id

user = Observable(None, compare=compare_users)
```

## Sample Code

### Counter App

```python
from nuiitivet.observable import Observable
from nuiitivet.widgets import Column, Row, Button, Text
from nuiitivet.runtime.app import App

class CounterApp:
    count = Observable(0)

    def __init__(self):
        self.count.dispatch_to_ui()
    
    def build(self):
        return Column(
            children=[
                Text(
                    text=self.count.map(lambda c: f"Count: {c}"),
                    size=32
                ),
                Row(
                    gap=10,
                    children=[
                        Button(
                            text="-",
                            on_click=lambda: self.decrement()
                        ),
                        Button(
                            text="+",
                            on_click=lambda: self.increment()
                        ),
                    ]
                )
            ],
            gap=20,
            padding=20
        )
    
    def increment(self):
        self.count.value += 1
    
    def decrement(self):
        self.count.value -= 1

if __name__ == "__main__":
    app = App(CounterApp().build)
    app.run()
```

### Shopping Cart

```python
from nuiitivet.observable import Observable, combine

class ShoppingCart:
    price = Observable(100)
    quantity = Observable(1)
    discount = Observable(0.1)
    
    def __init__(self):
        self.price.dispatch_to_ui()
        self.quantity.dispatch_to_ui()
        self.discount.dispatch_to_ui()
        # Subtotal
        self.subtotal = self.price.combine(self.quantity).compute(
            lambda p, q: p * q
        )
        
        # Total (After discount)
        self.total = combine(
            self.subtotal, 
            self.discount
        ).compute(lambda sub, disc: sub * (1 - disc))
        
        # Display string
        self.display = self.total.map(lambda t: f"Total: ¥{t:,.0f}")
```

### Asynchronous Data Fetching

```python
import threading
from nuiitivet.observable import Observable

class DataViewModel:
    data = Observable([])
    loading = Observable(False)
    error = Observable(None)

    def __init__(self):
        # Enable .dispatch_to_ui() for UI Observables
        self.data.dispatch_to_ui()
        self.loading.dispatch_to_ui()
        self.error.dispatch_to_ui()
    
    def load_data_async(self):
        def worker():
            try:
                self.loading.value = True
                self.error.value = None
                
                # Heavy process (API request etc.)
                result = fetch_data_from_api()
                
                # Set result (Notified on UI thread)
                self.data.value = result
            except Exception as e:
                self.error.value = str(e)
            finally:
                self.loading.value = False
        
        threading.Thread(target=worker).start()

def fetch_data_from_api():
    import time
    time.sleep(2)  # Simulate network delay
    return [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
```

### TODO List

```python
from nuiitivet.observable import Observable, batch

class TodoViewModel:
    items = Observable([])
    filter_mode = Observable("all")  # "all" | "active" | "completed"
    
    def __init__(self):
        self.items.dispatch_to_ui()
        self.filter_mode.dispatch_to_ui()
        # Filtered Items
        self.filtered_items = combine(
            self.items,
            self.filter_mode
        ).compute(lambda items, mode: self._filter_items(items, mode))
        
        # Statistics
        self.total_count = self.items.map(lambda items: len(items))
        self.active_count = self.items.map(
            lambda items: len([i for i in items if not i["done"]])
        )
        self.completed_count = self.items.map(
            lambda items: len([i for i in items if i["done"]])
        )
    
    def _filter_items(self, items, mode):
        if mode == "active":
            return [i for i in items if not i["done"]]
        elif mode == "completed":
            return [i for i in items if i["done"]]
        else:
            return items
    
    def add_item(self, text: str):
        current = self.items.value
        new_item = {"id": len(current), "text": text, "done": False}

        self.items.value = current + [new_item]
    
    def toggle_item(self, item_id: int):
        items = self.items.value
        new_items = [
            {**item, "done": not item["done"]} if item["id"] == item_id else item
            for item in items
        ]
        self.items.value = new_items
    
    def clear_completed(self):
        self.items.value = [i for i in self.items.value if not i["done"]]
```

---

## Next Steps

- [Layout Guide](layout.md) - Widget arrangement and layout system
