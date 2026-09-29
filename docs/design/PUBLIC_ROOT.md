# Public Root Surface

How callables on the `nv` root are organised, and where a new one goes.
Classes, widgets, styles and protocols, sit flat on the root; this policy is
about functions.

## The Rule

A function earns a flat spot on the root only when it is **DSL vocabulary**:
something written inline, per widget, inside a builder expression, where a
namespace prefix would be noise. Everything else, configuration and OS
services called a few times per app at startup or from an event handler,
lives on a **namespace class**, a class used as a namespace, holding
`@staticmethod`s and never instantiated. The test for a new function: does
it appear inside widget-tree code, many times, next to other flat
vocabulary? If not, find or create a namespace.

A bare verb at the root also collides with the framework's own concepts:
`notify` reads as an observable notification, where `Desktop.notify` does
not.

Flat, as DSL vocabulary: the modifiers (`background`, `clickable`,
`key_shortcut`, ...), which read as a DSL inside `.modifier(...)` several
per widget; the observable operators `batch` and `combine`, used
mid-expression; the input filters (`digits_only`, `max_length`, ...),
combinators composed inline for `input_filter=`; and the date helpers
(`parse_date`, `format_date`, `is_date`), value vocabulary used inline in
handlers and bindings beside `DatePicker`.

Namespaced, as configuration and OS services: `Fonts` (`set_default_family`,
`register`), `Clocks` (`get`, `set`), `Desktop` (`notify`) and `FileDialog`
(`open_file`, `open_files`, `save_file`, `open_directory`). `Clocks` stays on
the public root rather than becoming a test-only internal because swapping
the clock is the documented seam for app-level tests, and apps import
through the single root only.

## Namespace Conventions

The class name is a plural or collective noun for the subsystem (`Fonts`,
`Clocks`) or the service it wraps (`Desktop`, `FileDialog`). Methods drop
the words the class name carries: `Fonts.register(...)`, not
`Fonts.register_font(...)`. The class is a thin facade, and the
implementation stays in its subsystem module. A rename is a clean break; no
alias keeps a pre-namespace spelling alive.
