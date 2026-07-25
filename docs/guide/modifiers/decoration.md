# Decoration Modifiers

Decoration modifiers are used to add visual styling to Widgets, such as background colors, borders, corner radii, clipping, and shadows.

## Background and Border

You can add a background color using the `background` modifier and a border using the `border` modifier.

```python
import nuiitivet.material as nv

# Background only
box1 = nv.Container(child=nv.Text("Background")).modifier(nv.background("#E0E0E0"))

# Border only
box2 = nv.Container(child=nv.Text("Border")).modifier(nv.border(color="#F44336", width=4))

# Both background and border
box3 = nv.Container(child=nv.Text("Both")).modifier(
    nv.background("#E0E0E0") | nv.border(color="#4CAF50", width=2)
)
```

![Background and Border](../../assets/modifier_decoration_bg_border.png)

## Corner Radius and Clip

You can round the corners of a Widget using the `corner_radius` modifier. If you want to clip the content of the Widget to its bounds, use the `clip` modifier.

```python
import nuiitivet.material as nv

# Corner radius
box1 = nv.Container(child=nv.Text("Radius")).modifier(
    nv.background("#2196F3") | nv.corner_radius(16)
)

# Clip content
box2 = nv.Container(child=nv.Text("Clip")).modifier(
    nv.background("#FF9800") | nv.clip()
)
```

![Corner Radius and Clip](../../assets/modifier_decoration_radius_clip.png)

## Shadow

You can add a drop shadow to a Widget using the `shadow` modifier. It takes parameters like `color`, `blur`, and `offset`.

```python
import nuiitivet.material as nv

# Simple shadow
box1 = nv.Container(child=nv.Text("Shadow")).modifier(
    nv.background("#FFFFFF") | nv.shadow(color="#000000", blur=8, offset=(0, 4))
)

# Shadow with corner radius
box2 = nv.Container(child=nv.Text("With Radius")).modifier(
    nv.background("#FFFFFF") | nv.corner_radius(16) | nv.shadow(color="#000000", blur=12, offset=(0, 6))
)
```

![Shadow](../../assets/modifier_decoration_shadow.png)
