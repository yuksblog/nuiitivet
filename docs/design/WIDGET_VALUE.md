# Widget Value Surface

A widget that holds something the user set publishes it as a public `value`
property. This is the name the whole framework uses (`EditableText`,
`TextFieldBase`, `Toggleable`, `RadioGroup`, `SearchBar`, `ProgressIndicator`,
`Slider`, `RangeSlider`) and the name the dev tools read. The `_private` side
of the same widgets is in [WIDGET_ARCHITECTURE.md](WIDGET_ARCHITECTURE.md).

## Why One Name

`describe_tree` reports a node's interactive state in a vocabulary a coding
agent can rely on across every widget: `disabled`, `focused`, `selected`,
`value`. It gets that vocabulary by probing public properties, so a widget
that keeps its value under a private attribute is invisible there.

The reactive dump (`describe_state`) is not a substitute. It reports the
`Observable` attributes a widget happens to hold, under the names the widget
bound them to (`_state_internal`, `checked_external_tri`), so the same fact is
named differently for every widget. A widget whose value was bound as a plain
`bool` or `float` holds no observable at all and reports nothing.

## What `value` Means

**The value the user thinks the widget has, not all of its state.**
`EditableText.value` is the `str` being edited, while the full editing state,
text, selection and composing range, lives in a `TextEditingValue` beside it.
A widget with rich internal state still publishes the one thing its user set.
A widget with no such thing has no `value`: `Navigator` does not publish its
route stack as one.

## Composite Values

A value made of several parts is still one `value`. `RangeSlider.value` is
`(start, end)`; a time picker's would carry hour, minute and period.

The shape of a composite value is a per-widget decision, reviewed before it
is fixed, because once published callers destructure it and changing it
breaks them. Two questions decide it, and neither has a general answer:

- **Is the shape self-describing?** A positional tuple works when the parts
  are the same quantity in the same order every time, a range's two ends. It
  stops working when the parts are different kinds of thing: `(3, 30)` does
  not say which is the hour. Parts that need names are not given positions.
- **Does the widget already declare the shape somewhere?** `RangeSlider`
  types `on_change` as `Callable[[Tuple[float, float]], None]`, so its value
  was an ordered pair before `value` existed and the property only surfaced
  it. Where such a declaration exists, it wins over a second shape for the
  same value.

Reaching for a tuple because a sibling widget used one is the failure this
rule exists to prevent.

## Writing

`value` is writable wherever the widget's value is writable, so a caller can
read and assign through the name it saw in the tree.

A composite `value` whose parts have their own setters does not leave the
ordering to the caller. `RangeSlider.value_start` clamps against the current
`value_end` and vice versa, so assigning the two ends in the wrong order
collapses the new range onto the old one; the `value` setter picks the order,
and that trap is solved once, in the widget.
