---
layout: default
---

# Welcome to Nuiitivet

## Key Areas in the Docs

- **[Guide](guide/index.md)**
 A practical user guide to learn Nuiitivet step by step, from first app setup to common development workflows.
- **[API Reference](api/nuiitivet.md)**
 Provides reference docs.
- **[Changelog](https://github.com/yuksblog/nuiitivet/releases)**
 Tracks released versions and updates.

## Quick Example

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
    self.count.value += 1

  def build(self):
    return Column(
      [
        Text(f"count: {self.count.value}"),
        FilledButton("Increment", on_click=self.handle_increment),
      ],
      gap=12,
      padding=16,
    )


MaterialApp(home=CounterApp()).run()
```
