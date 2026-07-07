---
layout: default
---

# Nuiitivet Guides

This section is the practical user guide for building apps with Nuiitivet.
Use it as a step-by-step path from fundamentals to common app patterns.

## Imports

Nuiitivet has a single import root: your chosen UI design system. Import it once
as `nv`, and every symbol — layout, state, widgets, styles, modifiers — is
reachable from there.

```python
import nuiitivet.material as nv

nv.Column([nv.Text("Hello"), nv.Button("Click")])
```

An app always uses exactly one design system, so selecting it should hand you
the whole toolkit in one import. Only `nuiitivet.material` is available today.

## Recommended Path

1. [Layout](layout.md)
2. [Observable](observable.md)
3. [UI Design System](ui_design_system.md)
4. [Packaging](packaging.md)

## Topics

- [Dialogs](dialogs.md)
- [Navigation](navigation.md)
- [Window](window.md)
- [Modifiers](modifier.md)

## Advanced

- [Async & Threading](threading.md)
- [Interaction](interaction_region.md)
