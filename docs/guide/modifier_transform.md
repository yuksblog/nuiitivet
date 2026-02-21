# Transform Modifiers

Transform modifiers are used to apply paint-only transformations to Widgets, such as opacity, rotation, scaling, and translation. These transformations do not affect the layout or hit-testing of the Widget.

## Opacity

You can change the opacity of a Widget using the `opacity` modifier. It takes a value between 0.0 (transparent) and 1.0 (opaque).

```python
from nuiitivet.modifiers import background, opacity

# 100% opacity
box1 = Container(child=Text("100%")).modifier(background("#F44336"))

# 50% opacity
box2 = Container(child=Text("50%")).modifier(background("#F44336") | opacity(0.5))

# 20% opacity
box3 = Container(child=Text("20%")).modifier(background("#F44336") | opacity(0.2))
```

![Opacity](../assets/modifier_transform_opacity.png)

## Rotate and Scale

You can rotate a Widget using the `rotate` modifier and scale it using the `scale` modifier.

```python
from nuiitivet.modifiers import background, rotate, scale

# Rotate 45 degrees
box1 = Container(child=Text("Rotate 45°")).modifier(
    background("#4CAF50") | rotate(45)
)

# Scale 1.5x
box2 = Container(child=Text("Scale 1.5x")).modifier(
    background("#2196F3") | scale(1.5)
)
```

![Rotate and Scale](../assets/modifier_transform_rotate_scale.png)

## Translate

You can translate a Widget using the `translate` modifier. It takes an offset tuple `(dx, dy)`.

```python
from nuiitivet.modifiers import background, translate

# Normal
box1 = Container(child=Text("Normal")).modifier(background("#FF9800"))

# Translated
box2 = Container(child=Text("Translated")).modifier(
    background("#FF9800") | translate((20, 20))
)
```

![Translate](../assets/modifier_transform_translate.png)
