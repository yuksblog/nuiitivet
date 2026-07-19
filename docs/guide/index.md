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

1. [Layout](layout/index.md)
2. [Observable](state-management/index.md)
3. [UI Design System](design-system/index.md)
4. [Packaging](packaging.md)

## Topics

- [Dialogs](overlay/dialogs.md)
- [Navigation](navigation/index.md)
- [Window](window/index.md)
- [Modifiers](modifiers/index.md)

## AI pair-programming

- [Overview](ai_pair_programming/index.md)
- [Hot Reload](ai_pair_programming/hot_reload.md)
- [Dev Bridge MCP](ai_pair_programming/dev_bridge_mcp.md)
- [The `nuiitivet-app` skill](ai_pair_programming/nuiitivet_app_skill.md)

## Advanced

- [Async & Threading](advanced/threading.md)
- [Interaction](advanced/interaction_region.md)
