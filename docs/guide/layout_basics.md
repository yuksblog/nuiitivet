---
layout: default
---

# Layout Basics

The basics of screen layout are combinations of "vertical arrangement" and "horizontal arrangement".
This page explains how to use `Column` and `Row`, which are the most fundamental and powerful tools.
Before learning complex mechanisms, let's confirm that most screens can be created with just these two.

## Column

Forms, lists, settings screens, etc., are centered around Column.

```python
import nuiitivet as nv
import nuiitivet.material as md

content = nv.Column(
    children=[
        md.FilledTextField(label="Email"),
        md.FilledTextField(label="Password"),
        md.FilledButton("Login"),
    ],
    gap=16,
    padding=16,
)
```

- `gap`: Space between child elements
- `padding`: Padding inside the column

![Basic Column](../assets/layout_basics_column.png)

## Row

Toolbars, button rows, left-right splits, etc. often use Row.

```python
import nuiitivet as nv
import nuiitivet.material as md

actions = nv.Row(
    children=[
        md.OutlinedButton("Back"),
        md.FilledButton("Next"),
    ],
    gap=12,
    padding=16,
)
```

![Basic Row](../assets/layout_basics_row.png)

## Combining Row and Column

You can express complex layouts by combining Row and Column.
For example, a "Registration Form" layout can be created as follows:

```python
import nuiitivet as nv
import nuiitivet.material as md

# User Registration Form
form = nv.Column(
    children=[
        # Row 1: Name (Horizontal)
        nv.Row(
            children=[
                md.FilledTextField(label="First Name"),
                md.FilledTextField(label="Last Name"),
            ],
            gap=8,
        ),

        # Row 2: Address
        md.FilledTextField(label="Address", width=nv.Sizing.flex(1)),

        # Row 3: Buttons (Horizontal)
        nv.Row(
            children=[
                md.TextButton("Cancel"),
                md.FilledButton("Register"),
            ],
            gap=12,
        ),
    ],
    gap=16,
    padding=16,
    cross_alignment="center",
)
```

![Form example](../assets/layout_basics_form.png)

In this way, you construct screens by putting Column inside Row or Row inside Column.

## Next Steps

- Adjusting Spacing: [layout_spacing.md](layout_spacing.md)
- Determining Size: [layout_sizing.md](layout_sizing.md)
- Determining Alignment: [layout_alignment.md](layout_alignment.md)
