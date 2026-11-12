# Screen Reader

A screen reader reads each widget by its words, its role and its state: "Save,
button", "Agree, checkbox, unchecked". The window is readable with no setup.
[What is read with no code](#what-is-read-with-no-code) says what each widget gives; [Words for what has none](#words-for-what-has-none) says what to add where that is only a role.

The runnable demo is at [`samples/window/screen_reader.py`](https://github.com/yuksblog/nuiitivet/blob/main/samples/window/screen_reader.py).
[Where it works](#where-it-works) lists the platforms.

## What is read with no code

| Widget | What is read |
| --- | --- |
| A button, a chip, a navigation rail item, a menu item | Its text, then its role: "Save, button" |
| A text field | Its label and its text, as a text field |
| A checkbox, a switch, a radio button | Its role and its state, no words: "checkbox, unchecked" |
| A slider | Its value, no words: "slider, 30" |
| A range slider | Two sliders, "Range start" and "Range end", each with its value |
| A menu | "menu", then its items |
| A text | Its words |
| An icon, an image | Nothing |
| A layout | Nothing of its own; its children are read one by one |

## Words for what has none

A widget whose row above says "no words" or "nothing" is read as a role
alone. `nv.semantics` gives it the words.

```python
nv.IconButton("close", on_click=close).modifier(nv.semantics(label="Close"))
```

### An icon button

Read as "button" alone. Put `nv.semantics(label=...)` on it: "Close, button".

### A checkbox, a switch, a radio button, a slider

Read as "checkbox, unchecked": the user hears the state and not what it is
for. Put `nv.semantics(label=...)` on the control: "Agree, checkbox,
unchecked". The text beside it is still read on its own, as text, after the
control; there is no way to hide it.

```python
nv.Row(
    children=[
        nv.Checkbox(checked=agree).modifier(nv.semantics(label="Agree")),
        nv.Text("I agree"),
    ],
    gap=8,
)
```

### An icon or an image on its own

Not read at all. Put `nv.semantics(label=..., role=nv.SemanticsRole.IMAGE)`
on it: "Warning, image".

```python
nv.Icon("warning").modifier(nv.semantics(label="Warning", role=nv.SemanticsRole.IMAGE))
```

### A row of texts that belong together

Read as two texts, "3 items" after the icon that is not read. Put
`nv.semantics(label=...)` on the layout: "Cart, 3 items", once, as a text.
The texts inside are no longer read. A control inside the layout is still read,
after the label.

```python
nv.Row(
    children=[nv.Icon("shopping_cart"), nv.Text("3 items")],
    gap=8,
).modifier(nv.semantics(label="Cart, 3 items"))
```

### A range slider's handles

Read as "Range start, slider, 20" and "Range end, slider, 80". Put
`nv.semantics(label=[...])` on the slider, one name per handle: "Lowest
price, slider, 20".

```python
nv.HorizontalRangeSlider(value_start=20, value_end=80, min_value=0, max_value=100).modifier(
    nv.semantics(label=["Lowest price", "Highest price"])
)
```

## Where it works

| OS | Read by |
| --- | --- |
| macOS | VoiceOver |
| Windows | Narrator, NVDA |
| Linux | Orca |
| Browser | Nothing yet |
