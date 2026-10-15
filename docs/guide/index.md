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

1. [The intuitive grammar](intuitive_grammar/index.md)
2. [Layout](layout/index.md)
3. [Observable](state-management/index.md)
4. [Concurrency](concurrency.md)
5. [UI Design System](design-system/index.md)
6. [Packaging](packaging/index.md)

## Topics

- [Dialogs](overlay/dialogs.md)
- [Navigation](navigation/index.md)
- [Window](window/index.md)
- [Modifiers](modifiers/index.md)
- [Web](web/index.md)

## With a coding agent

- [Overview](coding_agent/index.md)
- [Set up](coding_agent/setup.md)
- [Hot Reload](coding_agent/hot_reload.md)
- [Comment mode](coding_agent/comment_mode.md)
- [Layout edit mode](coding_agent/layout_edit_mode.md)
- [Source jump](coding_agent/source_jump.md)
- [The skills](coding_agent/skills.md)
- [The dev bridge](coding_agent/dev_bridge.md)

## Advanced

- [Interaction](advanced/interaction_region.md)
- [Geometry: scoped measured size](advanced/geometry.md)
