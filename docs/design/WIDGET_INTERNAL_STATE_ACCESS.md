# Widget Internal State Access Policy

`nuiitivet` widgets maintain internal state used by layout, paint, composition, and hit-testing.
Direct access to internal attributes (e.g. `_built`, `_layout_rect`, `_last_rect`) is prohibited across module boundaries.

See also: [WIDGET_ARCHITECTURE.md](WIDGET_ARCHITECTURE.md)

## Goals

- Prevent accidental coupling between modules and mixins.
- Make ownership and responsibility explicit.
- Reduce bugs caused by inconsistent internal state updates.

## Ownership

- Composition (`_built`)
  - Owner: `BuilderHostMixin`
  - External modules must not read/write `_built`.
  - Use `built_child` accessor.

- Layout geometry (`_layout_rect`)
  - Owner: `WidgetKernel` (layout state)
  - External modules must not read/write `_layout_rect`.
  - Use `layout_rect` and `set_layout_rect()`.

- Input bounds (`global_layout_rect`)
  - Owner: `WidgetKernel` (layout-derived global geometry)
  - External modules must not derive input bounds from paint state.
  - Use `global_layout_rect`.

- Paint geometry (`_last_rect`)
  - Owner: `WidgetKernel` (paint state)
  - External modules must not read/write `_last_rect`.
  - Use `last_rect` and `set_last_rect()`.

- Layout dirty flag (`_needs_layout`)
  - Owner: `WidgetKernel` / `Widget`
  - External modules must not read/write `_needs_layout`.
  - Use `needs_layout`, `mark_needs_layout()`, and `clear_needs_layout()`.

- Layout cache token (`_layout_cache_token`)
  - Owner: `Widget`
  - External modules must not read/write `_layout_cache_token`.
  - Use `layout_cache_token`.
  - Note: `WidgetKernel.layout_cache_token` returns `None`; `Widget` overrides it to return an `int`.

## Public Accessors

- `built_child: Widget | None`
  - Read-only access to the composed child created by `build()`.

- `layout_rect: tuple[int, int, int, int] | None`
  - Read-only layout rectangle in parent coordinates.

- `set_layout_rect(x, y, width, height) -> None`
  - Sets the layout rectangle.

- `global_layout_rect: tuple[int, int, int, int] | None`
  - Read-only global layout rectangle for input/hit-testing.

- `last_rect: tuple[int, int, int, int] | None`
  - Read-only last painted rectangle (typically absolute coordinates).

- `set_last_rect(x, y, width, height) -> None`
  - Sets the last painted rectangle.

- `needs_layout: bool`
  - Read-only flag indicating whether the widget requests layout.

- `clear_needs_layout() -> None`
  - Clears the dirty flag after a successful layout pass.

- `layout_cache_token: int | None`
  - Read-only token used by layout caches to invalidate placements.

## Rules

- Layout modules must call `set_layout_rect()` instead of assigning `_layout_rect`.
- Paint routines must call `set_last_rect()` instead of assigning `_last_rect`.
- Input and hit-testing must use `global_layout_rect` and must not depend on `last_rect`.
- Runtime traversal must use `built_child` instead of reading `_built`.
- `WidgetKernel` must not reach into `BuilderHostMixin` internals.
- Render loops must use `needs_layout` / `clear_needs_layout()` instead of mutating `_needs_layout`.
- Layout caches must use `layout_cache_token` instead of reading `_layout_cache_token`.
