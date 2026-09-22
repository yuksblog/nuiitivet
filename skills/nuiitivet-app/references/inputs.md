# Text & date input

An input widget takes an `Observable` as its value and writes the user's edit
back into it. What the text *means* — a number, a date, a query — is derived
from that `Observable`, never stored beside it.

## Bind the value

```python
self.query = nv.Observable("")
nv.TextField(value=self.query, label="Name")
nv.TextField.multiline(value=self.notes, label="Notes")  # the text area, same arguments
```

`nv.TextField(value=self.query)`, `nv.Switch(checked=self.on)` and
`nv.HorizontalSlider(value=self.level)` all write the edit straight back. There is
no separate opt-in, and no `on_change` is needed to keep the Observable in sync.
Use `on_change` only for a *side effect* of the change; anything you can derive
(`query.debounce(0.3).switch_map(...)`) belongs on the Observable.

A read-only source — anything from `.map(...)`, `.compute(...)`, `combine(...)` —
has no setter, so an input widget can only display it. That is the correct way
to show a derived value; add `disabled=True` so the field does not look editable.

## Act on Enter, and on blur

`on_submit` means **Enter only** — every press, including a repeat on an unchanged
value, and never on blur. Blur-time work (validating, saving an inline edit,
finishing a half-typed value) goes to `on_focus_change(focused, source)`, the
same signature as `nv.focusable()`. `Enter` submits in `nv.TextField.multiline(...)`
too; `Shift+Enter` breaks the line.

## Restrict what can be typed

```python
nv.TextField(value=self.pin, input_filter=nv.digits_only() | nv.max_length(4))
```

## Get a typed value from the text

```python
self.amount = self.text.map(to_int)                                 # invalid text -> None
self.amount = self.text.filter(is_int, initial="0").map(to_int)     # holds the last valid one
```

Never bind a widget to the typed value and mirror the text back — the widget
writes into the text, and the field ends up reformatting itself under the
user's cursor.

## Show a search bar

```python
nv.SearchBar(self.query, placeholder="Search", width=440)
```

`width` names the **box**; the bar is inset 24dp inside it (12dp while focused).

```python
nv.DockedSearchBar(self.query, placeholder="Search", content=panel_widget,
                   on_submit=self.search, width=440)
```

- One slot, `content`: a live widget bound to your observables (suggestions,
  results, a spinner), not a rebuild callback.
- It opens on focus, on a tap on the bar, and on typing. It closes on Enter
  (`close_on_enter=False` keeps it up), on Escape, and on blur — never on a tap
  on the bar itself. Pass `is_open` to drive it yourself.
- `on_submit` is Enter only: clicking away never searches.

## Take a date

```python
nv.DockedDatePicker(value=self.arrival_text, label="Arrival")
self.arrival = self.arrival_text.map(nv.parse_date)
```

`value` is the field's **text**; the date is derived from it. The widget flags
nothing: pass `is_error` / `supporting_text` derived from the same text.
`min_date` / `max_date` scope the calendar only.

For a pattern other than the default, use one `nv.DateFormat` for the widget and
for the app, so parse, render and hint text cannot disagree:

```python
fmt = nv.DateFormat("dd.mm.yyyy")
nv.DockedDatePicker(value=self.arrival_text, date_format=fmt)
self.arrival = self.arrival_text.map(fmt.parse)
```

Tokens are `yyyy`, `yy`, `mm`, `dd`, lowercase; everything else is a literal
(`"yyyy年mm月dd日"` works).
