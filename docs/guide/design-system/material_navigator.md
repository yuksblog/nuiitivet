# Material Navigator

`MaterialNavigator` is a Material Design 3-flavored subclass of `Navigator`. It is automatically configured by `App`.

The only difference from the base `Navigator` is the default transition: when you push a plain `Widget`, `MaterialNavigator` wraps it in a `Route` pre-configured with the MD3 page transition. Pushing an explicit `Route` bypasses this default and uses whatever `transition_spec` you provide.

!!! note "Import convention"
    `App` and `Navigator` are the public names exported from `nuiitivet.material` for these classes.
    Import and use them by these names throughout your code.

    ```python
    import nuiitivet.material as nv
    ```

    The rest of this guide follows this convention.

## Automatic Setup

Passing a plain `Widget` to `App` is all that is needed. `App` wraps it in a `MaterialNavigator` automatically.

```python
import nuiitivet.material as nv

nv.App(nv.Window(content=HomeScreen())).run()
```

## Accessing

`App` registers the `MaterialNavigator` as the root navigator.

```python
import nuiitivet.material as nv

nv.Navigator.of(self)    # root navigator
nv.Navigator.of(self)  # nearest ancestor Navigator — use only with nested navigators
```

Neither can be resolved from a widget's `__init__`. Resolve one in the event handler, every time.

## Further Reading

| Topic | Guide |
| ----- | ----- |
| push / pop basics | [Navigation Overview](../navigation/index.md) |
| Custom transitions | [Route and Animations](../navigation/route.md) |
| Intent-based routing | [Intent-Based Navigation](../navigation/intent.md) |
| Nested navigation | [Nested Navigation](../navigation/nested.md) |

---

[API Reference](../../api/material.md#nuiitivet.material.MaterialNavigator)
