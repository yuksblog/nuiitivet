# Public Root Surface

How callables on the `nv` root are organized, and where a new one goes.
Classes (widgets, styles, protocols) always sit flat on the root; this policy
is about functions.

## The rule

A function earns a flat spot on the root only when it is **DSL vocabulary** —
something written inline, per widget, inside a builder expression, where a
namespace prefix would be pure noise. Everything else — configuration and OS
services, typically called a few times per app at startup or from an event
handler — lives on a **namespace class**: a class used as a namespace, holding
`@staticmethod`s, never instantiated (`Desktop`, `FileDialog`, `Fonts`,
`Clocks`).

Test for a new function: *does it appear inside widget-tree code, many times,
next to other flat vocabulary?* If not, find or create a namespace.

A bare verb at the root also collides with the framework's own concepts
(`notify` reads as an Observable notification); a namespace disambiguates for
free (`Desktop.notify`).

## Namespace conventions

- The class name is a plural or collective noun for the subsystem
  (`Fonts`, `Clocks`), or the service it wraps (`Desktop`, `FileDialog`).
- Methods drop the words the class name already carries:
  `Fonts.register(...)`, not `Fonts.register_font(...)`;
  `Fonts.set_default_family(...)`, not `Fonts.set_default_font_family(...)`.
- The class is a thin facade; the implementation stays in its subsystem
  module, and the facade delegates.
- No aliases for pre-namespace spellings; renames are clean breaks.

## Audit of root-level functions

### Flat — DSL vocabulary

| Group | Functions | Why flat |
| --- | --- | --- |
| Modifiers | `background`, `border`, `clickable`, `clip`, `context_menu`, `corner_radius`, `opacity`, `rotate`, `scale`, `shadow`, `stick`, `tooltip`, `translate`, `visible`, `keyed`, `popup`, `focusable`, `hoverable`, `key_shortcut`, `on_mount`, `on_unmount`, `on_size_changed`, `will_pop`, `absorb_pointer`, `block_pointer`, `defer_pointer`, `passthrough_pointer`, `pointer_input`, `drop_target`, `block_focus_traversal` | Read as a DSL inside `.modifier(...)`, several per widget. |
| Observable operators | `batch`, `combine` | Inline state-graph vocabulary, used mid-expression. |
| Input filters | `allow`, `deny`, `digits_only`, `matching`, `max_length` | Combinator vocabulary for `input_filter=`, composed inline. |
| Date helpers | `parse_date`, `format_date`, `is_date` | Value vocabulary paired with `DatePicker` / `DateFormat`, used inline in handlers and bindings. |

### Namespaced — configuration / OS services

| Namespace | Methods | Replaces |
| --- | --- | --- |
| `Fonts` | `set_default_family`, `register` | `set_default_font_family`, `register_font` |
| `Clocks` | `get`, `set` | `get_clock`, `set_clock` |
| `Desktop` | `notify` | `notify` |
| `FileDialog` | `open_file`, `open_files`, `save_file`, `open_directory` | — |

`Clocks` stays on the public root (rather than becoming test-only internals)
because swapping the clock is the documented seam for app-level tests, and
apps import through the single root only.
