# MD3 Specs and Framework Padding

MD3 has no `padding` or `margin` in the CSS sense. A component's sizes are
defined as layers, all internal to the component and independent of the
layout around it:

```text
Component
├─ Touch target   (48×48dp minimum, the interaction area)
├─ Container      (the visual boundary)
├─ State layer    (hover and press feedback)
└─ Content
   └─ internal spacing: label insets, icon-to-text gap
```

Where an MD3 spec says "padding", it means content placement inside the
container: a button's 24dp horizontal padding is the distance from its label
to its container edge, a list item's 16dp content padding is where its
leading icon sits. A checkbox spec uses no such word at all; it gives the
icon, the state layer and the touch target as three independent sizes.

The framework's `Widget.padding` is a different thing: the inset from the
allocated rect to the content rect, defined in [BOX_MODEL.md](BOX_MODEL.md),
included in `preferred_size()`, and the same on every widget from `Column` to
`Checkbox`. The two never share a field:

| MD3 term | Framework home |
| --- | --- |
| Container size, touch target | a `*Style` token, or the constructor parameter [SIZE_POLICY.md](SIZE_POLICY.md) allows for that axis |
| Content padding (internal) | a `*Style` token (`content_insets`), never `Widget.padding` |
| State layer | computed from the container by the MD3 ratio |
| Spacing between items | the container's `gap` |
| (no MD3 equivalent) | `Widget.padding` |

So an MD3 component is a closed unit: its touch target, container, state
layer and insets are its own, driven by its style, and `padding` wraps the
whole of it. `Checkbox(padding=10)` is a 48dp component in a 68dp box; the
component draws its 40dp state layer and 18dp icon inside the 48dp region
exactly as before, and the 10dp band is blank. The band reads as outer space
on a leaf because nothing paints there; it is still the allocated-to-content
inset, and BOX_MODEL.md says who hit-tests it.

The alternative, letting `Widget.padding` stand in for an MD3 inset, was
rejected: a button whose label inset were its `padding` would move its
container when a layout added space around it, and a layout that wanted
space around the button would have to know the spec's inset to add to it.
Two insets in one field cannot be told apart.
