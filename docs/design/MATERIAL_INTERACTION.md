# Material Design Interaction and State Layers

Every interactive Material widget (`Button`, `Checkbox`, `RadioButton`,
`Switch`, ...) inherits from `InteractiveWidget`, which brings
`InteractionHostMixin`, the state layer, the focus ring and the Space/Enter
key binding in one place. The nodes underneath are in
[INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md).

## Logical Focus and the Visual Ring

`state.focused` says the widget is the input target, whether it got there by
click or by Tab, and it alone routes input (the Space key). The ring is a
separate question, `should_show_focus_ring`: true for keyboard and
programmatic focus, false for pointer focus, so a clicked button does not keep
a ring. The ring tracks the latest `FocusSource`, not only the last focus
change, because the source can change without focus moving (dragging a
Tab-focused slider, then Tab-ing between its handles).

## State Layer Priority

`_get_active_state_layer_opacity` resolves the overlay in one order: drag,
then press, then hover. Keyboard focus draws no layer by default; MD3 prefers
the ring alone.

A widget that roves focus with the arrow keys inside a `FocusScope`, a
`MenuItem`, does layer focus, overriding the resolution to fall back to the
focus opacity while `should_show_focus_ring`. The roved item must read as
focused, and that is focus, not selection: `selected` stays reserved for a
genuinely selected entry. This is not automatic for every roving widget.
`NavigationRail` items rove too and stay ring-only, because their focus shape
is the active-indicator pill; a layer there fills the whole pill and reads as
selection or hover. A menu item's full-width row has no such ambiguity.

## Focus Ring Placement

The default ring (`draw_focus_indicator`) is drawn outside the widget bounds,
a 3dp stroke at a 2dp offset. Where an outer ring cannot fit, a widget
overrides `draw_focus_indicator` to draw the same ring inset, just inside the
shape that indicates the focus, mirroring the 2dp gap inward.

`NavigationRail` items settled this. MD3's component imagery shows no ring on
rail items, which could be read as "rail items are not focusable", but the
token set says otherwise: the rail defines a full `focused` state family
(state layer, icon and label colours, for active and inactive items alike), so
the items are focusable, and dropping them from the Tab sequence would fail
WCAG 2.1.1. What the imagery reflects is geometry: the items are packed so
closely that a ring offset outside one active indicator would overlap the
neighbouring indicators. Jetpack Compose's Material 3 ripple resolves the same
conflict with an inset ring, and the rail follows it: the inset ring alone,
painted on the active-indicator shape, identical in colour and stroke to the
standard ring and differing only in sitting inside.
