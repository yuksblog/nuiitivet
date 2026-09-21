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

1. [The intuitive grammar](intuitive_grammar.md)
2. [Layout](layout/index.md)
3. [Observable](state-management/index.md)
4. [Concurrency](concurrency.md)
5. [UI Design System](design-system/index.md)
6. [Packaging](packaging.md)

## Topics

- [Dialogs](overlay/dialogs.md)
- [Navigation](navigation/index.md)
- [Window](window/index.md)
- [Modifiers](modifiers/index.md)

## AI pair-programming

- [Overview](ai_pair_programming/index.md)
- [Install the skills](ai_pair_programming/install_skills.md)
- [Hot Reload](ai_pair_programming/hot_reload.md)
- [The on-screen modes](ai_pair_programming/on_screen_modes.md)
- [Dev Bridge MCP](ai_pair_programming/dev_bridge_mcp.md)

## Advanced

- [Interaction](advanced/interaction_region.md)
- [Geometry: scoped measured size](advanced/geometry.md)
